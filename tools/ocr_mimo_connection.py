#!/usr/bin/env python3
"""Pinned OpenCodeReview/MiMo connectivity probe, not a code reviewer.

Default: no-network preflight. --mock: real CLI with synthetic loopback replies.
--live: separately authorized paid requests using an existing MIMO_API_KEY.
No global configuration or credential file is created.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import secrets
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

VERSION = "v1.13.7"
SOURCE_COMMIT = "b1dcffb0729f3f2e3e47170968a5014a2e035580"
MODEL = "mimo-v2.6-pro"
ENDPOINT_HOST = "api.xiaomimimo.com"
# Official GitHub release asset digests, not supplied by the executable.
BINARY_HASHES = {
    "fa7b63f25e7002aec38e6980b071d1b53e6681aeb9e144b7bfe84833de5e3de6",
    "ce2eab495483f9b119992b48253a4e2f6969c27c3b02514350d9e7aa0083b4e8",
    "8c1ff786161b6dc0e8dcb06107f18bda8b6181b39ce573400add4a39f90cf19d",
    "f18be0e467aa23a5d9966b38fc0f89144b932970a2082800eacd4062b9257ffa",
    "b637d002471056c57f50c947583188dbeafa043aeb5875ee16ab4355b1eb2d36",
    "7c65e39825a169a4c6a4ddf1e163a0888843d5b338b72ed77e892095e6c8042d",
}
MAX_CALLS = 2
MAX_REQUEST_BYTES = 8192
MAX_RESPONSE_BYTES = 65536
MAX_OUTPUT_TOKENS = 1024
REQUEST_TIMEOUT = 30
PROCESS_TIMEOUT = 70


class ProbeError(ValueError):
    """Only fixed, credential-free diagnostics may cross this boundary."""


def checked_binary(path: Path) -> tuple[Path, str]:
    path = path.resolve(strict=True)
    if not path.is_file() or path.stat().st_size > 70_000_000:
        raise ProbeError("invalid CLI file")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest not in BINARY_HASHES:
        raise ProbeError("CLI does not match pinned release")
    return path, digest


def child_environment(token: str, port: int) -> dict[str, str]:
    # HOME stays unchanged. No provider key, proxy or telemetry env inheritance.
    env = {k: os.environ[k] for k in (
        "PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "TMPDIR", "TEMP", "TMP"
    ) if k in os.environ}
    env.update({
        "OCR_LLM_URL": f"http://127.0.0.1:{port}/v1",
        "OCR_LLM_TOKEN": token, "OCR_LLM_MODEL": MODEL,
        "OCR_LLM_PROTOCOL": "openai", "OCR_LLM_TIMEOUT": str(REQUEST_TIMEOUT),
        "OCR_ENABLE_TELEMETRY": "0", "OCR_CONTENT_LOGGING": "0", "NO_COLOR": "1",
    })
    return env


class Relay:
    """Serialized, two-attempt relay. Failure permanently stops upstream calls.

    Limits are HTTP attempts, request BYTES and output-token parameters, NOT
    exact input tokens or a provider-side dollar cap. Failed/unknown attempts
    count. The production transport has no retries or redirect following.
    """

    def __init__(self, *, live: bool, api_key: str = ""):
        self.live, self.api_key = live, api_key
        self.token = secrets.token_urlsafe(32)
        self.attempts = self.completed = 0
        self.halted = self.tool_round_trip = False
        self.tool_call_id = None
        self.usage = []

    def exchange(self, raw: bytes, authorization: str, path: str) -> bytes:
        if not secrets.compare_digest(authorization, f"Bearer {self.token}"):
            raise ProbeError("relay authentication rejected")
        if self.halted or self.attempts >= MAX_CALLS:
            self.halted = True
            raise ProbeError("relay stopped; do not retry")
        try:
            if path != "/v1/chat/completions" or len(raw) > MAX_REQUEST_BYTES:
                raise ProbeError("request outside limits")
            payload = json.loads(raw)
            if not isinstance(payload, dict) or payload.get("model") != MODEL:
                raise ProbeError("unexpected model")
            if payload.get("stream") not in (None, False):
                raise ProbeError("streaming disabled")
            messages = payload.get("messages")
            if not isinstance(messages, list) or not messages:
                raise ProbeError("missing conversation")
            if self.attempts == 0:
                if any(m.get("role") not in ("system", "user") for m in messages):
                    raise ProbeError("unexpected initial conversation")
            else:
                if not self.tool_call_id or not any(
                    m.get("role") == "tool" and m.get("tool_call_id") == self.tool_call_id
                    and m.get("content") == "ocr_selftest ok" for m in messages
                ):
                    raise ProbeError("self-test result missing")
                self.tool_round_trip = True
            # Pinned SDK sends max_completion_tokens; MiMo uses max_tokens.
            payload.pop("max_completion_tokens", None)
            payload["max_tokens"] = MAX_OUTPUT_TOKENS
            body = json.dumps(payload, ensure_ascii=False).encode()
            if len(body) > MAX_REQUEST_BYTES:
                raise ProbeError("request exceeds byte ceiling")
            self.attempts += 1  # Reserve BEFORE external HTTP, including failures.
            response = self._forward(body) if self.live else self._mock()
            if len(response) > MAX_RESPONSE_BYTES:
                raise ProbeError("response exceeds byte ceiling")
            data = json.loads(response)
            if data.get("model") != MODEL:
                raise ProbeError("response model differs")
            choices = data.get("choices")
            if not isinstance(choices, list) or len(choices) != 1:
                raise ProbeError("missing completion")
            choice, message = choices[0], choices[0]["message"]
            if self.attempts == 1:
                calls = message.get("tool_calls", [])
                if (choice.get("finish_reason") != "tool_calls" or len(calls) != 1
                        or calls[0].get("function", {}).get("name") != "ocr_selftest"
                        or not isinstance(calls[0].get("id"), str) or not calls[0]["id"]):
                    raise ProbeError("self-test call missing")
                self.tool_call_id = calls[0]["id"]
            elif (choice.get("finish_reason") != "stop" or message.get("tool_calls")
                  or not isinstance(message.get("content"), str) or not message["content"].strip()):
                raise ProbeError("final response incomplete")
            usage = data.get("usage", {})
            self.usage.append({
                k: usage[k] if type(usage.get(k)) is int and usage[k] >= 0 else "unknown"
                for k in ("prompt_tokens", "completion_tokens", "total_tokens")
            })
            self.completed += 1
            return response
        except Exception:
            self.halted = True
            raise ProbeError("probe stopped; outcome may be unknown") from None

    def _forward(self, body: bytes) -> bytes:
        # No proxy env, redirect following, SDK retries, or endpoint fallback.
        conn = http.client.HTTPSConnection(ENDPOINT_HOST, timeout=REQUEST_TIMEOUT)
        try:
            conn.request("POST", "/v1/chat/completions", body, {
                "Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json",
            })
            response = conn.getresponse()
            if response.status != 200:
                raise ProbeError("MiMo HTTP response rejected")
            return response.read(MAX_RESPONSE_BYTES + 1)
        finally:
            conn.close()

    def _mock(self) -> bytes:
        if self.attempts == 1:
            message = {"role": "assistant", "content": None, "tool_calls": [{
                "id": "fixture_call_1", "type": "function", "function": {
                    "name": "ocr_selftest", "arguments": '{"note":"synthetic"}',
                },
            }]}
        else:
            message = {"role": "assistant", "content": "Synthetic local connection fixture."}
        return json.dumps({
            "id": "fixture", "object": "chat.completion", "created": 0, "model": MODEL,
            "choices": [{"index": 0, "message": message,
                         "finish_reason": "tool_calls" if self.attempts == 1 else "stop"}],
        }).encode()


def run_probe(binary: Path, *, live: bool = False) -> dict:
    binary, digest = checked_binary(binary)
    # OCR config outranks env and can execute key commands or enable telemetry.
    # Reconcile explicitly rather than editing or silently bypassing it.
    if (Path.home() / ".opencodereview/config.json").exists():
        raise ProbeError("existing OCR config requires reconciliation")
    key = os.environ.get("MIMO_API_KEY", "") if live else ""
    if live and (not key or "\n" in key or "\r" in key):
        raise ProbeError("MIMO_API_KEY is not available")
    relay = Relay(live=live, api_key=key)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass  # Never log request headers, bodies, provider errors or content.

        def do_POST(self):
            self.connection.settimeout(REQUEST_TIMEOUT)
            try:
                size = int(self.headers.get("Content-Length", "-1"))
                if not 0 < size <= MAX_REQUEST_BYTES or self.headers.get("Transfer-Encoding"):
                    relay.halted = True
                    raise ProbeError("invalid HTTP framing")
                raw = self.rfile.read(size)
                if len(raw) != size:
                    relay.halted = True
                    raise ProbeError("incomplete body")
                body = relay.exchange(raw, self.headers.get("Authorization", ""), self.path)
                status = 200
            except Exception:
                body = b'{"error":{"message":"probe stopped; no upstream retry"}}'
                status = 400  # Non-retryable to the pinned upstream SDK.
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    rc = None
    try:
        result = subprocess.run(
            [str(binary), "llm", "test"], stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env=child_environment(relay.token, server.server_port),
            timeout=PROCESS_TIMEOUT, check=False,
        )
        rc = result.returncode
    except (subprocess.TimeoutExpired, OSError):
        relay.halted = True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=REQUEST_TIMEOUT + 1)
    passed = (rc == 0 and relay.attempts == relay.completed == MAX_CALLS
              and relay.tool_round_trip and not relay.halted)
    return {
        "schema_version": "1.0", "mode": "live" if live else "mock",
        "status": "CONNECTED" if live and passed else "MOCK_PASSED" if passed else "FAILED_OR_UNKNOWN",
        "ocr_version": VERSION, "ocr_source_commit": SOURCE_COMMIT,
        "binary_sha256": digest, "requested_model": MODEL,
        "http_attempts": relay.attempts, "completed_responses": relay.completed,
        "tool_round_trip": relay.tool_round_trip, "cli_exit_code": rc,
        "usage": relay.usage, "cost_usd": "unknown" if live else "not_applicable_mock",
        "dollar_cap_enforced": False, "review_quality_accepted": False,
        "limits": {"http_attempts": MAX_CALLS, "request_bytes": MAX_REQUEST_BYTES,
                   "output_tokens_per_request": MAX_OUTPUT_TOKENS,
                   "request_timeout_seconds": REQUEST_TIMEOUT},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--mock", action="store_true")
    mode.add_argument("--live", action="store_true",
                      help="paid external requests; requires separately authorized execution")
    parser.add_argument("--receipt", type=Path,
                        help="new private receipt; required for live, never reused")
    args = parser.parse_args()
    receipt = None
    try:
        if args.live:
            if args.receipt is None:
                raise ProbeError("live requires a new receipt path")
            # Validate before reserving a receipt or reading the credential.
            checked_binary(args.binary)
            if not os.environ.get("MIMO_API_KEY"):
                raise ProbeError("MIMO_API_KEY is not available")
            fd = os.open(args.receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            receipt = os.fdopen(fd, "w", encoding="utf-8")
            receipt.write('{"status":"OUTCOME_UNKNOWN_UNTIL_RECONCILED"}\n')
            receipt.flush()
            os.fsync(receipt.fileno())
        if args.mock or args.live:
            report = run_probe(args.binary, live=args.live)
        else:
            _, digest = checked_binary(args.binary)
            report = {"status": "PREFLIGHT_ONLY", "binary_sha256": digest,
                      "credential_present": bool(os.environ.get("MIMO_API_KEY")),
                      "ocr_config_present": (Path.home()/".opencodereview/config.json").exists(),
                      "external_requests": 0}
        if receipt:
            receipt.seek(0)
            receipt.write(json.dumps(report, sort_keys=True) + "\n")
            receipt.truncate()
            receipt.flush()
            os.fsync(receipt.fileno())
        print(json.dumps(report, sort_keys=True))
        return 1 if report["status"] == "FAILED_OR_UNKNOWN" else 0
    except (ProbeError, OSError) as exc:
        reason = str(exc) if isinstance(exc, ProbeError) else "local preflight or receipt failed"
        print(json.dumps({"status": "BLOCKED", "reason": reason}))
        return 1
    finally:
        if receipt:
            receipt.close()


if __name__ == "__main__":
    raise SystemExit(main())
