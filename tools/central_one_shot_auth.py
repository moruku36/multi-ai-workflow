"""Fail-closed operator signatures. No paid entry point or private-key handling."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import selectors
import stat
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = b"central-review-hub\x00one-shot\x00v1\x00"
HUB = "moruku36/multi-ai-workflow"
SHA = re.compile(r"[0-9a-f]{40}\Z")
IDENTITY = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")
# Fixed system paths only; never resolve cryptographic programs from request/PATH.
OPENSSL = "/usr/bin/openssl"
GIT = "/usr/bin/git"


class Blocked(ValueError):
    pass


def require(ok):
    if not ok:
        raise Blocked("ONE_SHOT_AUTHORITY_BLOCKED")


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False).encode("ascii")


def strict_json(raw, maximum=8192):
    require(type(raw) is bytes and 0 < len(raw) <= maximum)

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result)
            result[key] = value
        return result

    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: require(False))


def read_policy_file(path, maximum):
    # Only called with fixed paths below the trusted controller checkout.
    require(path.is_relative_to(ROOT))
    require(all(not p.is_symlink() for p in (path, *path.parents) if p != ROOT.parent))
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                and 0 < info.st_size <= maximum)
        raw = stream.read(maximum + 1)
        require(len(raw) <= maximum)
    return raw


def bounded_command(argv, *, cwd, deadline, maximum=8192):
    """Fixed caller-owned argv, empty environment, bounded pipe and wall time."""
    end = min(deadline, time.monotonic() + 5)
    require(time.monotonic() < end)
    env = {"PATH": os.defpath, "LC_ALL": "C", "OPENSSL_CONF": os.devnull,
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_SYSTEM": os.devnull,
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_OPTIONAL_LOCKS": "0",
           "GIT_TERMINAL_PROMPT": "0", "GIT_NO_REPLACE_OBJECTS": "1"}
    with subprocess.Popen(argv, cwd=cwd, env=env, shell=False,
                          stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT) as proc:
        result = bytearray()
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(proc.stdout, selectors.EVENT_READ)
                while True:
                    left = end - time.monotonic()
                    require(left > 0 and selector.select(left))
                    chunk = os.read(proc.stdout.fileno(), min(4096, maximum + 1 - len(result)))
                    if not chunk:
                        break
                    result.extend(chunk)
                    require(len(result) <= maximum)
            require(proc.wait(timeout=max(0.001, end - time.monotonic())) == 0)
            return bytes(result)
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.wait()


def controller_revision(deadline):
    # HEAD is read independently; env and signed assertions are only comparisons.
    argv = [GIT, "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false",
            "-c", "core.untrackedCache=false"]
    revision = bounded_command(argv + ["rev-parse", "--verify", "HEAD^{commit}"],
                               cwd=ROOT, deadline=deadline, maximum=128).decode().strip()
    require(SHA.fullmatch(revision))
    require(not bounded_command(argv + ["status", "--porcelain=v1", "--untracked-files=all"],
                                cwd=ROOT, deadline=deadline))
    return revision


def openssl3(deadline):
    version = bounded_command([OPENSSL, "version"], cwd=ROOT, deadline=deadline, maximum=512)
    require(re.match(rb"OpenSSL 3\.[0-9]+\.[0-9]+(?:[ -])", version))


def decode64(value, size):
    require(type(value) is str and len(value) == ((size + 2) // 3) * 4)
    raw = base64.b64decode(value, validate=True)
    require(len(raw) == size and base64.b64encode(raw).decode("ascii") == value)
    return raw


def utc(value):
    require(type(value) is str and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value))
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def active(payload, now):
    require(now.tzinfo is not None and now.utcoffset().total_seconds() == 0)
    since, expiry = utc(payload["eligible_since"]), utc(payload["expires_at"])
    require(since <= now < expiry and (expiry - now).total_seconds() <= 3600)


def validate_payload(p, revision, now):
    require(type(p) is dict and set(p) == {
        "schema_version", "domain", "issuer", "key_id", "authorization",
        "repository", "pr", "base", "head", "controller_revision",
        "eligible_since", "expires_at", "lane_attempt_limits"})
    require(type(p["schema_version"]) is int and p["schema_version"] == 1
            and p["domain"] == "central-review-hub/one-shot/v1")
    for name in ("issuer", "key_id"):
        require(type(p[name]) is str and IDENTITY.fullmatch(p[name]))
    require(type(p["authorization"]) is dict and p["authorization"] == {
        "kind": "one_target_dual_review", "targets": 1, "reruns": False, "refunds": False})
    a = p["authorization"]
    require(type(a["targets"]) is int and a["reruns"] is False and a["refunds"] is False)
    repository = p["repository"]
    require(type(repository) is str and re.fullmatch(
        r"moruku36/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", repository)
        and repository.lower() != HUB.lower())
    require(type(p["pr"]) is int and 1 <= p["pr"] <= 2147483647)
    for name in ("base", "head", "controller_revision"):
        require(type(p[name]) is str and SHA.fullmatch(p[name]))
    require(p["controller_revision"] == revision)
    caps = p["lane_attempt_limits"]
    require(type(caps) is dict and set(caps) == {"alibaba", "cloudflare"})
    for lane, maximum in (("alibaba", 8), ("cloudflare", 1)):
        require(type(caps[lane]) is int and 0 <= caps[lane] <= maximum)
    active(p, now)


def verify_envelope(raw, *, revision, now, deadline):
    """Authenticate against ONLY the strict root policy in this checkout."""
    envelope = strict_json(raw)
    require(type(envelope) is dict and set(envelope) == {"payload", "signature"})
    require(canonical(envelope) == raw)  # Exact ASCII encoding; no trailing newline.
    payload = envelope["payload"]
    validate_payload(payload, revision, now)
    signature = decode64(envelope["signature"], 64)
    policy = strict_json(read_policy_file(ROOT / "config/central-one-shot-trust.json", 16384), 16384)
    require(type(policy) is dict and set(policy) == {"schema_version", "keys"}
            and type(policy["schema_version"]) is int and policy["schema_version"] == 1
            and type(policy["keys"]) is list and len(policy["keys"]) <= 16)
    seen, selected = set(), None
    for key in policy["keys"]:
        require(type(key) is dict and set(key) == {"issuer", "key_id", "algorithm", "public_key"})
        for name in ("issuer", "key_id"):
            require(type(key[name]) is str and IDENTITY.fullmatch(key[name]))
        identity = key["issuer"], key["key_id"]
        require(identity not in seen and key["algorithm"] == "Ed25519")
        seen.add(identity)
        public = decode64(key["public_key"], 32)
        if identity == (payload["issuer"], payload["key_id"]):
            selected = public
    require(selected is not None)  # Empty policy is intentionally inactive.
    openssl3(deadline)
    with tempfile.TemporaryDirectory(prefix="central-signature-") as directory:
        scratch = Path(directory)
        # Fixed RFC 8410 SubjectPublicKeyInfo encoding, not signature arithmetic.
        (scratch / "public.der").write_bytes(bytes.fromhex("302a300506032b6570032100") + selected)
        (scratch / "payload").write_bytes(DOMAIN + canonical(payload))
        (scratch / "signature").write_bytes(signature)
        bounded_command([OPENSSL, "pkeyutl", "-verify", "-pubin", "-keyform", "DER",
                         "-inkey", "public.der", "-rawin", "-in", "payload",
                         "-sigfile", "signature"], cwd=scratch, deadline=deadline, maximum=512)
    return payload
