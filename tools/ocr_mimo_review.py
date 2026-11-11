#!/usr/bin/env python3
"""Bounded real OCR review of the two bundled synthetic samples only."""
from __future__ import annotations

import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import threading

import ocr_mimo_connection as connection

FIXTURES = Path(__file__).resolve().parents[1] / "tests/fixtures/synthetic_samples"
SAMPLES = {"clean": "app/service/data_processor.py",
           "defect": "app/service/file_handler.py"}
MAX_CALLS = 8  # Shared across BOTH samples, including planner and failed calls.
MAX_BYTES = 65536
MAX_OUTPUT = 2048
TIMEOUT = 150


class ReviewRelay(connection.Relay):
    """Parent-only credential; shared attempt cap, fail-closed, no HTTP retries."""

    def exchange(self, raw, authorization, path):
        if not secrets.compare_digest(authorization, f"Bearer {self.token}"):
            raise connection.ProbeError("relay authentication rejected")
        try:
            if self.halted or self.attempts >= MAX_CALLS:
                raise ValueError()
            if path != "/v1/chat/completions" or len(raw) > MAX_BYTES:
                raise ValueError()
            payload = json.loads(raw)
            if (payload.get("model") != connection.MODEL
                    or payload.get("stream") not in (None, False)
                    or not isinstance(payload.get("messages"), list)):
                raise ValueError()
            payload.pop("max_completion_tokens", None)
            payload["max_tokens"] = MAX_OUTPUT
            body = json.dumps(payload, ensure_ascii=False).encode()
            if len(body) > MAX_BYTES:
                raise ValueError()
            self.attempts += 1
            response = self._forward(body) if self.live else self.mock_review(payload)
            if len(response) > connection.MAX_RESPONSE_BYTES:
                raise ValueError()
            data = json.loads(response)
            if data.get("model") != connection.MODEL or len(data["choices"]) != 1:
                raise ValueError()
            choice = data["choices"][0]
            if choice["finish_reason"] not in ("stop", "tool_calls"):
                raise ValueError()
            message = choice["message"]
            if not (message.get("tool_calls") or
                    isinstance(message.get("content"), str) and message["content"].strip()):
                raise ValueError()
            usage = data.get("usage", {})
            self.usage.append({k: usage[k] if type(usage.get(k)) is int
                               and usage[k] >= 0 else "unknown" for k in
                               ("prompt_tokens", "completion_tokens", "total_tokens")})
            self.completed += 1
            return response
        except Exception:
            self.halted = True
            raise connection.ProbeError("review stopped; outcome may be unknown") from None

    def mock_review(self, payload):
        names = {t["function"]["name"] for t in payload.get("tools", [])}
        if "task_done" not in names:  # Planner's free-text guidance.
            message = {"role": "assistant", "content": "Review the supplied changes."}
        else:
            calls = []
            text = json.dumps(payload["messages"])
            if "file_handler.py" in text and not any(
                    m.get("role") == "tool" for m in payload["messages"]):
                calls.append({"id": "mock_comment", "type": "function", "function": {
                    "name": "code_comment", "arguments": json.dumps({"comments": [{
                        "path": SAMPLES["defect"], "content": "Synthetic fixture finding.",
                        "existing_code": '        f = open(target_path, "r", encoding="utf-8")',
                        "category": "bug", "severity": "medium",
                    }]})}})
            else:
                calls.append({"id": "mock_done", "type": "function", "function": {
                    "name": "task_done", "arguments": '{"state":"DONE"}'}})
            message = {"role": "assistant", "content": None, "tool_calls": calls}
        return json.dumps({"model": connection.MODEL, "choices": [{
            "index": 0, "message": message,
            "finish_reason": "tool_calls" if message.get("tool_calls") else "stop",
        }]}).encode()


def ingest(data, target, line_count):
    """Accept only completed current-run output; never infer fine subcategories."""
    if (not isinstance(data, dict) or data.get("status") not in ("success", "complete")
            or data.get("warnings") or data.get("llm", {}).get("model") != connection.MODEL
            or data.get("summary", {}).get("files_reviewed") != 1
            or not isinstance(data.get("comments"), list)):
        raise connection.ProbeError("incomplete review output")
    findings = []
    for comment in data["comments"]:
        start, end = comment.get("start_line"), comment.get("end_line")
        if (comment.get("path") != target or not isinstance(comment.get("content"), str)
                or not comment["content"].strip()
                or type(start) is not int or type(end) is not int
                or not 1 <= start <= end <= line_count):
            raise connection.ProbeError("invalid finding location")
        findings.append({k: comment.get(k) for k in
                         ("path", "start_line", "end_line", "category", "severity",
                          "content", "existing_code", "suggestion_code")})
    return {"findings": findings, "findings_count": len(findings),
            "fine_category_matches": "NOT_SCORED",
            "false_positives": "PENDING_HUMAN_REVIEW",
            "missed_defects": "PENDING_HUMAN_REVIEW",
            "human_verification_required": True}


def run_review(binary, *, live=False):
    binary, digest = connection.checked_binary(binary)
    if (Path.home() / ".opencodereview/config.json").exists():
        raise connection.ProbeError("existing OCR config requires reconciliation")
    # A global custom rule can add unrelated input. Do not edit/bypass it.
    if (Path.home() / ".opencodereview/rule.json").exists():
        raise connection.ProbeError("existing OCR rule requires reconciliation")
    key = os.environ.get("MIMO_API_KEY", "") if live else ""
    if live and (not key or "\n" in key or "\r" in key):
        raise connection.ProbeError("MIMO_API_KEY is not available")
    relay = ReviewRelay(live=live, api_key=key)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            self.connection.settimeout(connection.REQUEST_TIMEOUT)
            try:
                size = int(self.headers.get("Content-Length", "-1"))
                if not 0 < size <= MAX_BYTES or self.headers.get("Transfer-Encoding"):
                    raise ValueError()
                raw = self.rfile.read(size)
                if len(raw) != size:
                    raise ValueError()
                body = relay.exchange(raw, self.headers.get("Authorization", ""), self.path)
                status = 200
            except Exception:
                relay.halted = True
                body, status = b'{"error":{"message":"review stopped; no upstream retry"}}', 400
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    results = []
    try:
        for sample, target in SAMPLES.items():
            if relay.halted:
                break
            before_calls = relay.completed
            with tempfile.TemporaryDirectory(prefix="ocr-synthetic-") as directory:
                root = Path(directory)
                repo = root / "repo"
                repo.mkdir()
                env = connection.child_environment(relay.token, server.server_port)
                # No caller Git configuration, hooks, signing, or credentials.
                env["GIT_CONFIG_NOSYSTEM"] = "1"
                env["GIT_CONFIG_GLOBAL"] = os.devnull
                env["GIT_TERMINAL_PROMPT"] = "0"
                def git(*args):
                    return subprocess.run(["git", *args], cwd=repo, env=env,
                                          check=True, capture_output=True, timeout=10)
                git("init", "-q")
                destination = repo / target
                destination.parent.mkdir(parents=True)
                shutil.copyfile(FIXTURES / "sources" / sample / "before" / target, destination)
                git("add", "--", target)
                git("-c", "user.name=Synthetic", "-c", "user.email=synthetic@example.invalid",
                    "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
                    "commit", "-qm", "synthetic baseline")
                shutil.copyfile(FIXTURES / "sources" / sample / "after" / target, destination)
                diff = git("diff", "--no-ext-diff", "--no-textconv", "--", target).stdout
                output = root / "review.json"
                rc = None
                try:
                    process = subprocess.run([
                        str(binary), "review", "--repo", str(repo), "--format", "json",
                        "--audience", "agent", "--output", str(output), "--no-filter",
                        "--effort", "low", "--concurrency", "1", "--timeout", "1",
                    ], cwd=repo, env=env, stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        timeout=TIMEOUT, check=False)
                    rc = process.returncode
                    if rc != 0 or relay.halted or relay.completed == before_calls:
                        raise connection.ProbeError("review incomplete")
                    if not output.is_file() or output.stat().st_size > 262144:
                        raise connection.ProbeError("review output outside limits")
                    accepted = ingest(json.loads(output.read_text()), target,
                                      len(destination.read_text().splitlines()))
                    results.append({"sample": sample, "status": "REVIEW_COMPLETED",
                                    "diff_sha256": hashlib.sha256(diff).hexdigest(),
                                    "cli_exit_code": rc, **accepted})
                except (ValueError, OSError, subprocess.TimeoutExpired):
                    relay.halted = True
                    results.append({"sample": sample, "status": "FAILED_OR_UNKNOWN",
                                    "cli_exit_code": rc})
                    break
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=31)
    passed = len(results) == 2 and not relay.halted
    return {"schema_version": "1.0", "mode": "live" if live else "mock",
            "status": ("LIVE_REVIEW_COMPLETED" if live else "MOCK_REVIEW_PASSED")
                      if passed else "FAILED_OR_UNKNOWN",
            "binary_sha256": digest, "ocr_version": connection.VERSION,
            "ocr_source_commit": connection.SOURCE_COMMIT,
            "requested_model": connection.MODEL,
            "http_attempts": relay.attempts, "completed_responses": relay.completed,
            "usage": relay.usage, "results": results,
            "cost_usd": "unknown" if live else "not_applicable_mock",
            "dollar_cap_enforced": False, "review_quality_accepted": False,
            "limits": {"http_attempts_total": MAX_CALLS, "request_bytes": MAX_BYTES,
                       "output_tokens_per_request": MAX_OUTPUT,
                       "request_timeout_seconds": connection.REQUEST_TIMEOUT}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--live", action="store_true", help="paid synthetic review, not a connection probe")
    parser.add_argument("--receipt", required=True, type=Path, help="new private file, never reused")
    args = parser.parse_args()
    try:
        connection.checked_binary(args.binary)
        with os.fdopen(os.open(args.receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600),
                       "w", encoding="utf-8") as receipt:
            receipt.write('{"status":"OUTCOME_UNKNOWN_UNTIL_RECONCILED"}\n')
            receipt.flush()
            os.fsync(receipt.fileno())
            report = run_review(args.binary, live=args.live)
            receipt.seek(0)
            json.dump(report, receipt, ensure_ascii=False)
            receipt.write("\n")
            receipt.truncate()
            receipt.flush()
            os.fsync(receipt.fileno())
        # Findings remain in private receipt; do not echo arbitrary model content.
        print(json.dumps({k: v for k, v in report.items() if k not in ("results",)}))
        return int(report["status"] == "FAILED_OR_UNKNOWN")
    except (connection.ProbeError, OSError, subprocess.SubprocessError):
        print('{"status":"BLOCKED_OR_UNKNOWN","reason":"reconcile receipt; do not retry"}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
