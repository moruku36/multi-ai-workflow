#!/usr/bin/env python3
"""Vendor the complete MIT Cloudflare skill at one immutable revision. No install hooks."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess

REVISION = "c1c8a8c1471069fb0e188eeaff69b8e8db6564a8"
REPOSITORY = "cloudflare/security-audit-skill"
ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / ".agents/skills/security-audit"
NOTICE = ROOT / "third_party/cloudflare-security-audit"


def api(endpoint):
    return json.loads(subprocess.run(
        ["gh", "api", endpoint], check=True, capture_output=True,
        timeout=30).stdout)


def main():
    if DEST.exists() or NOTICE.exists():
        raise SystemExit("Destination exists; reconcile before vendoring.")
    tree = api(f"repos/{REPOSITORY}/git/trees/{REVISION}?recursive=1")
    if tree.get("truncated"):
        raise SystemExit("Incomplete upstream tree.")
    blobs = {}
    prefix = "skills/security-audit/"
    for item in tree["tree"]:
        name = item["path"]
        if item["type"] != "blob" or not (
                name.startswith(prefix) or name in ("README.md", "LICENSE")):
            continue
        relative = name[len(prefix):] if name.startswith(prefix) else name
        if "/" in relative or relative in (".", "..") or item["mode"] not in ("100644", "100755"):
            raise SystemExit("Unexpected upstream path or mode.")
        raw = base64.b64decode(api(
            f"repos/{REPOSITORY}/git/blobs/{item['sha']}")["content"])
        if len(raw) > 500000:
            raise SystemExit("Upstream file outside bounds.")
        header = f"blob {len(raw)}\0".encode()
        if hashlib.sha1(header + raw).hexdigest() != item["sha"]:
            raise SystemExit("Git blob mismatch.")
        target = (DEST / relative) if name.startswith(prefix) else (NOTICE / name)
        blobs[target] = raw
    if DEST / "SKILL.md" not in blobs or NOTICE / "LICENSE" not in blobs:
        raise SystemExit("Required files missing.")
    manifest = {"repository": REPOSITORY, "revision": REVISION, "files": {
        str(path.relative_to(ROOT)): hashlib.sha256(raw).hexdigest()
        for path, raw in sorted(blobs.items())}}
    for path, raw in blobs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
    with (NOTICE / "manifest.json").open("x") as stream:
        json.dump(manifest, stream, indent=2)
        stream.write("\n")
    print(f"Vendored {len(blobs)} files; no upstream code executed.")


if __name__ == "__main__":
    main()
