"""GitHub-signed launcher provenance for the existing serialized main workflow.

No env boolean is authority. This trusts GitHub TLS/JWKS, OIDC issuance, hosted
runner isolation and the reviewed main workflow's single concurrency group.
Missing/changed claim or certificate contracts block rather than downgrade.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import http.client
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import parse_qsl, quote, urlsplit

from central_one_shot_auth import (
    HUB, OPENSSL, bounded_command, openssl3, require, strict_json,
)

ISSUER = "https://token.actions.githubusercontent.com"
WORKFLOW = HUB + "/.github/workflows/central-review-hub.yml@refs/heads/main"


def audience(envelope):
    suffix = "recurring" if envelope is None else hashlib.sha256(envelope).hexdigest()
    return "urn:central-review-hub:v1:" + suffix


def get_json(host, path, *, deadline, maximum, authorization=None):
    timeout = min(5, deadline - time.monotonic())
    require(timeout > 0)
    end = time.monotonic() + timeout
    conn = http.client.HTTPSConnection(host, timeout=timeout)
    try:
        headers = {"Accept": "application/json", "User-Agent": "central-review-hub"}
        if authorization is not None:
            headers["Authorization"] = "Bearer " + authorization
        conn.request("GET", path, headers=headers)
        response = conn.getresponse()
        require(response.status == 200)  # No redirects, retries or alternate issuer.
        chunks, size = [], 0
        while True:
            left = end - time.monotonic()
            require(left > 0)
            if conn.sock is not None:
                conn.sock.settimeout(left)
            chunk = response.read1(min(4096, maximum + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            require(size <= maximum)
        return strict_json(b"".join(chunks), maximum)
    finally:
        conn.close()


def decode_url(value, maximum):
    require(type(value) is str and 0 < len(value) <= maximum
            and re.fullmatch(r"[A-Za-z0-9_-]+", value))
    raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    require(base64.urlsafe_b64encode(raw).decode().rstrip("=") == value)
    return raw


def validate_claims(c, *, revision, expected_audience, now, one_shot):
    require(type(c) is dict and len(c) <= 128)
    required = {
        "iss": ISSUER, "aud": expected_audience, "repository": HUB,
        "repository_owner": "moruku36", "ref": "refs/heads/main",
        "ref_type": "branch", "sha": revision, "workflow_ref": WORKFLOW,
        "workflow_sha": revision, "runner_environment": "github-hosted",
        "sub": "repo:" + HUB + ":ref:refs/heads/main",
    }
    require(all(type(c.get(k)) is str and c[k] == v for k, v in required.items()))
    require(c.get("event_name") in (("workflow_dispatch",) if one_shot else
                                   ("workflow_dispatch", "schedule")))
    for key in ("job_workflow_ref", "job_workflow_sha"):
        if key in c:
            require(c[key] == (WORKFLOW if key.endswith("ref") else revision))
    for key in ("head_ref", "base_ref"):
        require(c.get(key, "") == "")
    for key in ("run_id", "run_attempt"):
        require(type(c.get(key)) is str and re.fullmatch(r"[1-9][0-9]{0,19}", c[key]))
    if one_shot:
        require(c["run_attempt"] == "1")
    for key in ("iat", "nbf", "exp"):
        require(type(c.get(key)) is int and 0 <= c[key] < 2**40)
    instant = int(now.timestamp())
    require(c["nbf"] <= instant < c["exp"] and c["iat"] <= instant
            and 0 < c["exp"] - c["iat"] <= 600 and instant - c["iat"] <= 600)


def verify_launcher(*, revision, envelope, deadline):
    expected = audience(envelope)
    # These env values only locate the runner capability. A forged value cannot
    # satisfy the subsequent GitHub signature and exact claim checks.
    url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL", "")
    capability = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "")
    require(0 < len(url) <= 4096 and all(33 <= ord(c) <= 126 for c in url))
    parsed = urlsplit(url)
    require(parsed.scheme == "https" and parsed.port is None and parsed.username is None
            and parsed.password is None and not parsed.fragment and parsed.path.startswith("/")
            and parsed.hostname is not None
            and parsed.hostname.endswith(".actions.githubusercontent.com"))
    require(not any(k == "audience" for k, _ in parse_qsl(parsed.query)))
    require(0 < len(capability) <= 8192 and all(33 <= ord(c) <= 126 for c in capability))
    path = parsed.path + "?" + parsed.query + ("&" if parsed.query else "") + "audience=" + quote(expected, safe="")
    token = get_json(parsed.hostname, path, deadline=deadline, maximum=32768,
                     authorization=capability)
    require(type(token) is dict and set(token) == {"value"}
            and type(token["value"]) is str and len(token["value"]) <= 16384)
    parts = token["value"].split(".")
    require(len(parts) == 3)
    header = strict_json(decode_url(parts[0], 2048), 2048)
    claims = strict_json(decode_url(parts[1], 12288), 12288)
    signature = decode_url(parts[2], 1024)
    require(type(header) is dict and {"alg", "kid", "typ"} <= set(header)
            and set(header) <= {"alg", "kid", "typ", "x5t"}
            and header["alg"] == "RS256" and header["typ"] == "JWT"
            and type(header["kid"]) is str
            and re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", header["kid"])
            and 256 <= len(signature) <= 512)
    keys = get_json("token.actions.githubusercontent.com", "/.well-known/jwks",
                    deadline=deadline, maximum=65536)
    require(type(keys) is dict and set(keys) == {"keys"}
            and type(keys["keys"]) is list and 1 <= len(keys["keys"]) <= 16
            and all(type(k) is dict for k in keys["keys"]))
    selected = [k for k in keys["keys"] if k.get("kid") == header["kid"]]
    require(len(selected) == 1)
    key = selected[0]
    require(key.get("kty") == "RSA" and key.get("alg") == "RS256"
            and key.get("use") == "sig" and type(key.get("x5c")) is list
            and 1 <= len(key["x5c"]) <= 4 and type(key["x5c"][0]) is str
            and 0 < len(key["x5c"][0]) <= 8192)
    cert = base64.b64decode(key["x5c"][0], validate=True)
    require(len(cert) <= 6144)
    openssl3(deadline)
    with tempfile.TemporaryDirectory(prefix="central-launcher-") as directory:
        scratch = Path(directory)
        (scratch / "certificate.der").write_bytes(cert)
        public = bounded_command([OPENSSL, "x509", "-inform", "DER", "-in", "certificate.der",
                                  "-pubkey", "-noout"], cwd=scratch, deadline=deadline)
        (scratch / "public.pem").write_bytes(public)
        (scratch / "signature").write_bytes(signature)
        (scratch / "payload").write_bytes((parts[0] + "." + parts[1]).encode("ascii"))
        bounded_command([OPENSSL, "rsa", "-pubin", "-in", "public.pem", "-noout"],
                        cwd=scratch, deadline=deadline, maximum=512)
        bounded_command([OPENSSL, "dgst", "-sha256", "-verify", "public.pem",
                         "-signature", "signature", "payload"],
                        cwd=scratch, deadline=deadline, maximum=512)
    validate_claims(claims, revision=revision, expected_audience=expected,
                    now=datetime.now(timezone.utc),
                    one_shot=envelope is not None)
    # Environment is compared with authenticated claims, never used as evidence.
    require(os.environ.get("GITHUB_REPOSITORY") == HUB
            and os.environ.get("GITHUB_REF") == "refs/heads/main"
            and os.environ.get("GITHUB_SHA") == revision
            and os.environ.get("GITHUB_WORKFLOW_REF") == WORKFLOW
            and os.environ.get("GITHUB_WORKFLOW_SHA") == revision
            and os.environ.get("GITHUB_EVENT_NAME") == claims["event_name"]
            and os.environ.get("GITHUB_RUN_ID") == claims["run_id"]
            and os.environ.get("GITHUB_RUN_ATTEMPT") == claims["run_attempt"])
    return claims
