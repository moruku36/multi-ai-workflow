#!/usr/bin/env python3
"""Bounded, check-only Ruff/Semgrep adapter for explicitly selected Python files.

No installation, fix mode, remote rules, login, or API transport is provided.
This is an offline-configured tool adapter, not an OS network sandbox.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import tempfile
import time
from pathlib import Path

TOOLS = ("ruff", "semgrep")
MAX_FILES = 50
MAX_FILE_BYTES = 1024 * 1024
MAX_TOTAL_BYTES = 5 * 1024 * 1024
MAX_OUTPUT_BYTES = 2 * 1024 * 1024
MAX_FINDINGS = 1000
TIMEOUT_SECONDS = 30
RULES_PATH = Path(__file__).resolve().parent / "quality" / "semgrep-python.json"
RULES_SHA256 = "701a50fda74ed554cf182742b636486af231b1b70087ed082dc55aacb1b4ffc4"
RULE_MESSAGES = {
    "local-python-dynamic-eval": "Review dynamic evaluation; do not evaluate untrusted input.",
    "local-python-shell-true": "Review shell execution; prefer an argument list with shell=False.",
    "local-python-bare-except-pass": "Review silently swallowed exceptions; preserve an observable failure path.",
}


def sanitized_path(repo_root: Path) -> str:
    """Use the same trusted search scope for entrypoints and their helpers."""
    root = repo_root.resolve()
    entries = []
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        path = Path(entry)
        if not entry or not path.is_absolute():
            continue
        resolved = path.resolve()
        if not resolved.is_relative_to(root):
            entries.append(str(resolved))
    return os.pathsep.join(dict.fromkeys(entries))


def find_executable(tool: str, repo_root: Path) -> str | None:
    """Ignore relative PATH entries and executable shims inside the target repo."""
    found = shutil.which(tool, path=sanitized_path(repo_root))
    if found is None:
        return None
    resolved = Path(found).resolve()
    if resolved.is_relative_to(repo_root.resolve()):
        return None
    return str(resolved)


def select_files(repo_root: Path, targets: list[str]) -> list[tuple[str, bytes]]:
    """Copy only named ordinary .py files, never expand directories or symlinks."""
    root = repo_root.resolve(strict=True)
    if not root.is_dir() or not targets or len(targets) > MAX_FILES:
        raise ValueError("Select between 1 and 50 Python files in an existing repository")
    selected = []
    seen = set()
    total = 0
    for target in targets:
        rel = Path(target)
        if rel.is_absolute() or ".." in rel.parts or not rel.parts:
            raise ValueError("Targets must be relative paths without parent traversal")
        if rel.suffix != ".py" or rel.as_posix() in seen:
            raise ValueError("Targets must be unique .py files")
        path = root
        for part in rel.parts:
            path = path / part
            if path.is_symlink():
                raise ValueError("Symlinks are not permitted in target paths")
        if not path.is_file() or not path.resolve().is_relative_to(root):
            raise ValueError("Target must be an ordinary file inside the repository")
        data = read_regular_file(root, rel)
        if len(data) > MAX_FILE_BYTES:
            raise ValueError("A target exceeds the 1 MiB file limit")
        data.decode("utf-8")
        if b"\x00" in data:
            raise ValueError("NUL bytes are not permitted in Python sources")
        total += len(data)
        if total > MAX_TOTAL_BYTES:
            raise ValueError("Targets exceed the 5 MiB total limit")
        name = rel.as_posix()
        seen.add(name)
        selected.append((name, data))
    return selected


def read_regular_file(root: Path, rel: Path) -> bytes:
    """Descriptor-relative, nonblocking reads prevent symlink/FIFO replacement."""
    if os.name != "posix":
        raise ValueError("This adapter requires POSIX descriptor-relative access")
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in rel.parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        fd = os.open(rel.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(fd, "rb") as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE_BYTES:
                raise ValueError("Target is not a bounded ordinary file")
            return source.read(MAX_FILE_BYTES + 1)
    finally:
        os.close(directory)


def isolated_env(home: Path, repo_root: Path) -> dict[str, str]:
    # Do not pass API tokens, cloud credentials, proxy settings, or Python hooks.
    env = {k: os.environ[k] for k in ("SystemRoot", "WINDIR") if k in os.environ}
    env.update({
        "PATH": sanitized_path(repo_root),
        "HOME": str(home), "USERPROFILE": str(home),
        "XDG_CONFIG_HOME": str(home / "config"),
        "XDG_CACHE_HOME": str(home / "cache"),
        "TMPDIR": str(home), "TMP": str(home), "TEMP": str(home),
        "SEMGREP_SETTINGS_FILE": str(home / "semgrep-settings.yml"),
        "SEMGREP_SEND_METRICS": "off", "SEMGREP_ENABLE_VERSION_CHECK": "0",
        "DO_NOT_TRACK": "1", "PYTHONNOUSERSITE": "1", "LC_ALL": "C.UTF-8",
    })
    return env


def execute(command: list[str], cwd: Path, env: dict[str, str]) -> dict:
    """One process group at a time; terminate descendants on timeout/oversize."""
    if os.name != "posix":
        return {"status": "UNSUPPORTED_PLATFORM", "returncode": None}
    started = time.monotonic()
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        try:
            process = subprocess.Popen(
                command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                stdout=stdout, stderr=stderr, shell=False, start_new_session=True,
            )
        except OSError:
            return {"status": "LAUNCH_ERROR", "returncode": None}
        stop_reason = None
        while process.poll() is None:
            if time.monotonic() - started >= TIMEOUT_SECONDS:
                stop_reason = "TIMEOUT"
            elif os.fstat(stdout.fileno()).st_size + os.fstat(stderr.fileno()).st_size > MAX_OUTPUT_BYTES:
                stop_reason = "OUTPUT_LIMIT"
            if stop_reason:
                break
            time.sleep(0.02)
        # A tool's leader can exit while descendants still hold output files.
        # Clean the entire owned session even on normal exit before the next tool.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            stop_reason = "CLEANUP_ERROR"
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            stop_reason = "CLEANUP_ERROR"
        if os.fstat(stdout.fileno()).st_size + os.fstat(stderr.fileno()).st_size > MAX_OUTPUT_BYTES:
            stop_reason = stop_reason or "OUTPUT_LIMIT"
        stdout.seek(0)
        stderr.seek(0)
        raw = stdout.read(MAX_OUTPUT_BYTES + 1)
        err = stderr.read(MAX_OUTPUT_BYTES + 1)
        return {
            "status": stop_reason or "FINISHED", "returncode": process.returncode,
            "stdout": raw.decode("utf-8", errors="replace"),
            "stderr_sha256": hashlib.sha256(err).hexdigest(),
            "duration_sec": round(time.monotonic() - started, 3),
        }


def relative_result_path(value: object, stage: Path, selected: set[str]) -> str:
    if not isinstance(value, str):
        raise ValueError("Missing finding path")
    path = Path(value)
    full = path if path.is_absolute() else stage / path
    resolved = full.resolve()
    if not resolved.is_relative_to(stage.resolve()):
        raise ValueError("Finding outside selected scope")
    rel = resolved.relative_to(stage.resolve()).as_posix()
    if rel not in selected:
        raise ValueError("Finding outside selected scope")
    return rel


def normalize(tool: str, text: str, stage: Path, selected: set[str]) -> tuple[list[dict], str]:
    parsed = json.loads(text)
    version = "unknown"
    if tool == "ruff":
        if not isinstance(parsed, list):
            raise ValueError("Expected Ruff finding list")
        rows = parsed
    else:
        if not isinstance(parsed, dict) or parsed.get("errors") != []:
            raise ValueError("Semgrep errors or incomplete result envelope")
        rows = parsed.get("results")
        paths = parsed.get("paths")
        if not isinstance(paths, dict):
            raise ValueError("Missing Semgrep path envelope")
        scanned = paths.get("scanned")
        if not isinstance(rows, list) or not isinstance(scanned, list):
            raise ValueError("Missing Semgrep results or scanned paths")
        observed = {relative_result_path(p, stage, selected) for p in scanned}
        if observed != selected or len(scanned) != len(observed):
            raise ValueError("Semgrep did not scan every selected file")
        if isinstance(parsed.get("version"), str) and re.fullmatch(r"[0-9A-Za-z.+_-]{1,64}", parsed["version"]):
            version = parsed["version"]
    if len(rows) > MAX_FINDINGS:
        raise ValueError("Finding count exceeds limit")
    findings = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid finding record")
        if tool == "ruff":
            loc = row.get("location")
            path, rule, message = row.get("filename"), row.get("code"), row.get("message")
            severity = "ERROR"
        else:
            loc = row.get("start")
            extra = row.get("extra")
            if not isinstance(extra, dict):
                raise ValueError("Invalid Semgrep finding metadata")
            path, rule, message = row.get("path"), row.get("check_id"), extra.get("message")
            severity = extra.get("severity")
        if not isinstance(loc, dict):
            raise ValueError("Missing finding position")
        line = loc.get("row" if tool == "ruff" else "line")
        column = loc.get("column" if tool == "ruff" else "col")
        if type(line) is not int or line < 1 or type(column) is not int or column < 1:
            raise ValueError("Invalid finding position")
        if not all(isinstance(v, str) and v.strip() for v in (rule, message, severity)):
            raise ValueError("Missing finding text")
        if tool == "ruff":
            if rule != "invalid-syntax" and not re.fullmatch(r"[A-Z]+[0-9]{1,4}", rule):
                raise ValueError("Invalid Ruff rule identifier")
            message = f"Ruff reported {rule}; review the indicated location."
        else:
            rule = rule.rsplit(".", 1)[-1]
            if rule not in RULE_MESSAGES or severity not in ("ERROR", "WARNING", "INFO"):
                raise ValueError("Unknown bundled rule or severity")
            message = RULE_MESSAGES[rule]
        findings.append({
            "tool": tool, "rule_id": rule, "path": relative_result_path(path, stage, selected),
            "line": line, "column": column, "severity": severity, "message": message[:512],
        })
    return findings, version


def run_static_checks(repo_root: Path, targets: list[str], tools: list[str] | tuple[str, ...] = TOOLS) -> dict:
    report = {
        "schema_version": "1.0.0", "mode": "LOCAL_CHECK_ONLY", "status": "ERROR",
        "network_policy": "Local rules; metrics and version checks disabled. Not an OS egress sandbox.",
        "limits": {"timeout_seconds_per_tool": TIMEOUT_SECONDS, "max_files": MAX_FILES,
                   "max_file_bytes": MAX_FILE_BYTES, "max_total_bytes": MAX_TOTAL_BYTES},
        "sources": [], "results": [],
    }
    try:
        if os.name != "posix":
            report["status"] = "UNSUPPORTED_PLATFORM"
            return report
        if not tools or any(t not in TOOLS for t in tools) or len(set(tools)) != len(tools):
            raise ValueError("Select each supported tool at most once")
        files = select_files(repo_root, targets)
    except (ValueError, OSError, UnicodeError) as exc:
        report["error"] = type(exc).__name__ + ": invalid target selection"
        return report
    report["sources"] = [{"path": n, "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)} for n, b in files]
    selected = {n for n, _ in files}
    with tempfile.TemporaryDirectory(prefix="quality-check-") as tmp:
        base = Path(tmp)
        stage, home = base / "source", base / "home"
        stage.mkdir()
        home.mkdir()
        for name, data in files:
            dest = stage / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        names = sorted(selected)
        for tool in tools:
            result = {"tool": tool, "status": "UNAVAILABLE", "passed": False, "findings": [], "version": "unknown"}
            binary = find_executable(tool, repo_root)
            if binary is None:
                report["results"].append(result)
                continue
            if tool == "ruff":
                command = [binary, "check", "--isolated", "--no-cache", "--ignore-noqa", "--target-version", "py311",
                           "--output-format", "json", "--select", "E9,F63,F7,F82", "--", *names]
            else:
                try:
                    with RULES_PATH.open("rb") as source:
                        rules = source.read(64 * 1024 + 1)
                    if hashlib.sha256(rules).hexdigest() != RULES_SHA256:
                        raise OSError("Bundled rules do not match the pinned hash")
                    config = base / "semgrep-python.json"
                    config.write_bytes(rules)
                except OSError:
                    result["status"] = "CONFIG_ERROR"
                    report["results"].append(result)
                    continue
                result["rules_sha256"] = hashlib.sha256(rules).hexdigest()
                command = [binary, "scan", "--oss-only", "--config", str(config), "--metrics=off",
                           "--disable-version-check", "--disable-nosem", "--json", "--error", "--strict", "--jobs", "1",
                           "--timeout", "10", "--max-memory", "512", "--no-git-ignore", "--", *names]
            outcome = execute(command, stage, isolated_env(home, repo_root))
            result.update({k: v for k, v in outcome.items() if k != "stdout"})
            if outcome["status"] == "FINISHED":
                if outcome["returncode"] not in (0, 1):
                    result["status"] = "TOOL_ERROR"
                else:
                    try:
                        findings, version = normalize(tool, outcome.get("stdout", ""), stage, selected)
                        # Both --error Semgrep and Ruff use 0 clean / 1 findings.
                        if bool(findings) != (outcome["returncode"] == 1):
                            raise ValueError("Exit code and findings disagree")
                        result.update(findings=findings, version=version,
                                      status="FINDINGS" if findings else "PASSED", passed=not findings)
                    except (ValueError, TypeError, KeyError):
                        result["status"] = "INVALID_OUTPUT"
            report["results"].append(result)
            if result["status"] == "CLEANUP_ERROR":
                # Do not overlap another engine when process cleanup is uncertain.
                for remaining in tools[len(report["results"]):]:
                    report["results"].append({"tool": remaining, "status": "NOT_RUN", "passed": False,
                                              "findings": [], "version": "unknown"})
                break
    report["status"] = "PASSED" if all(r["passed"] for r in report["results"]) else "FAILED"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--target", action="append", required=True, help="Explicit relative .py file; repeat for each file")
    parser.add_argument("--tool", action="append", choices=TOOLS, help="Installed tool to execute; default both")
    args = parser.parse_args()
    report = run_static_checks(args.repo_root, args.target, args.tool or TOOLS)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
