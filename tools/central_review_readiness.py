#!/usr/bin/env python3
"""Offline observations only. No flags, credentials, fetch, writes or authority."""
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import stat
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
MAX_PATHS, MAX_SOURCE, MAX_OUTPUT = 20, 65536, 131072
SHA = re.compile(rb"[0-9a-f]{40}")


class Blocked(ValueError):
    pass


def git(*args, deadline):
    """Fixed local operations only; bound captured bytes and total elapsed time."""
    env = {"PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_ATTR_NOSYSTEM": "1",
           "GIT_TERMINAL_PROMPT": "0", "GIT_NO_LAZY_FETCH": "1",
           "GIT_NO_REPLACE_OBJECTS": "1", "GIT_OPTIONAL_LOCKS": "0"}
    command = ["/usr/bin/git", "-c", "core.hooksPath=/dev/null", "-c",
               "core.fsmonitor=false", "-c", "core.attributesFile=/dev/null", *args]
    with subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL) as proc:
        try:
            data = bytearray()
            with selectors.DefaultSelector() as poll:
                poll.register(proc.stdout, selectors.EVENT_READ)
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not poll.select(remaining):
                        raise Blocked("git_deadline")
                    chunk = os.read(proc.stdout.fileno(), min(8192, MAX_OUTPUT + 1 - len(data)))
                    if not chunk:
                        break
                    data.extend(chunk)
                    if len(data) > MAX_OUTPUT:
                        raise Blocked("git_output_cap")
            if proc.wait(timeout=max(0.001, deadline - time.monotonic())):
                raise Blocked("git_failed")
            return bytes(data)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()


def fixed_file(relative):
    path = ROOT / relative
    current = ROOT
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            raise Blocked("policy_symlink")
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > 16384:
            raise Blocked("policy_file_cap")
        raw = stream.read(16385)
    if len(raw) > 16384:
        raise Blocked("policy_file_cap")
    return raw


def policy_observations():
    config = json.loads(fixed_file("config/central-review-hub.json"))
    flags = {key: config[key] for key in ("enabled", "paid_execution_authorized")}
    if any(type(value) is not bool for value in flags.values()):
        raise Blocked("policy_shape")
    workflow = fixed_file(".github/workflows/central-review-hub.yml")
    return {"config_flags_observed": flags,
            "workflow_sha256": hashlib.sha256(workflow).hexdigest(),
            "scope": "fixed worktree files; observations confer no authority"}


def measure():
    deadline = time.monotonic() + 30
    report = {"status": "BLOCKED", "blockers": [], "diff_bytes": None,
              "paths": None, "before_after_blob_bytes": None,
              "caps": {"paths": MAX_PATHS, "diff_bytes": MAX_SOURCE,
                       "before_after_blob_bytes": MAX_SOURCE},
              "scope": "local origin/main merge-base to HEAD; uncommitted edits excluded"}
    try:
        refs = []
        for ref in ("refs/remotes/origin/main", "HEAD"):
            value = git("rev-parse", "--verify", ref + "^{commit}", deadline=deadline).strip()
            if not SHA.fullmatch(value):
                raise Blocked("invalid_commit")
            refs.append(value.decode("ascii"))
        base = git("merge-base", *refs, deadline=deadline).strip()
        if not SHA.fullmatch(base):
            raise Blocked("invalid_merge_base")
        base, head = base.decode("ascii"), refs[1]
        report.update(origin_main=refs[0], base=base, head=head)
        names = git("diff", "--no-ext-diff", "--no-textconv", "--no-renames",
                    "--name-only", "-z", base, head, "--", deadline=deadline)
        paths = names.split(b"\0")[:-1]
        report["paths"] = len(paths)
        if not paths:
            report["blockers"].append("empty_diff")
        if len(paths) > MAX_PATHS:
            report["blockers"].append("path_cap")
        # Retain oversized-input blockers even when another measurement fails.
        try:
            diff = git("diff", "--no-ext-diff", "--no-textconv", "--no-renames",
                       "--binary", base, head, "--", deadline=deadline)
            report["diff_bytes"] = len(diff)
            if len(diff) > MAX_SOURCE:
                report["blockers"].append("diff_cap")
            if any(line == b"GIT binary patch" or line.startswith(b"Binary files ")
                   for line in diff.splitlines()):
                report["blockers"].append("binary_diff")
        except Blocked as error:
            report["blockers"].append(str(error))
            if str(error) == "git_output_cap":
                report["diff_bytes_at_least"] = MAX_OUTPUT + 1
                report["blockers"].append("diff_cap")
        if len(paths) <= MAX_PATHS:
            total = 0
            for ref in (base, head):
                for path in paths:
                    entry = git("ls-tree", "-l", "-z", ref, "--",
                                ":(literal)" + path.decode("utf-8"), deadline=deadline)
                    if entry:
                        fields = entry.split(b"\t", 1)[0].split()
                        if len(fields) != 4 or fields[:2] != [b"100644", b"blob"]:
                            raise Blocked("non_regular_blob")
                        total += int(fields[3])
            report["before_after_blob_bytes"] = total
            if total > MAX_SOURCE:
                report["blockers"].append("snapshot_cap")
        # No source extraction, exclusion or policy substitution is attempted.
        if not report["blockers"]:
            report["status"] = "LOCAL_SIZE_CAPS_ONLY"
    except (Blocked, OSError, UnicodeError, ValueError, subprocess.TimeoutExpired) as error:
        report["blockers"].append(str(error) if isinstance(error, Blocked) else "measurement_unknown")
    return report


def readiness():
    result = {"status": "PENDING_NOT_AUTHORIZED", "live_acceptance": False,
              "stages": {stage: "PENDING_EXTERNAL_EVIDENCE" for stage in (
                  "human_merge", "new_paid_allowance", "fresh_real_pr_check_ledger_acceptance",
                  "runtime_enable")}, "local_diff": measure()}
    try:
        result["policy_observations"] = policy_observations()
    except (Blocked, OSError, ValueError, KeyError, TypeError):
        result["policy_observations"] = {"status": "BLOCKED_OR_UNKNOWN"}
    return result


if __name__ == "__main__":
    if len(sys.argv) != 1:
        raise SystemExit("No caller flags accepted; local evidence cannot authorize execution.")
    print(json.dumps(readiness(), indent=2, sort_keys=True))
