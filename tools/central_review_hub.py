#!/usr/bin/env python3
"""Bounded, disabled-by-default central coordinator; trusted hub code/config only.

Deployment requires a trusted hub checkout, a single non-cancelling concurrency
group, retained check runs, an installation GH_TOKEN and explicit runtime secrets.
This file is NOT activation, paid authorization or real-PR acceptance evidence.

Global reservations are append-only check runs on a fixed hub commit. EVERY
reservation, including failure/interruption/unknown, consumes its slot forever;
daily accounting includes every status. No refund, retry or automatic
reconciliation exists. A lost write response stops the entire run.

Git fetch is full (no lazy/promisor auth): all objects/history reachable from the
two validated commits can be downloaded. Time, captured output and OBSERVED disk
are bounded, but aggregate disk/wire bytes have no hard ceiling; a pack can grow
past the observed limit between polls. A runner disk quota is needed for a hard
ceiling. No target checkout, build, dependency, hook or config is executed.
auto.alibaba constructs its own bounded source-only scaffolding; control files
are rejected before it can materialize them. Its real relay/model are retained.

Offline seams: inject api (durable state/pagination), sources (immutable
extraction/rejections), lanes (sequential
outcomes), and preflight/now (activation/quota/staleness).
"""
from __future__ import annotations

from contextlib import ExitStack, contextmanager, redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import base64
import hashlib
import http.client
import json
import multiprocessing
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote
import uuid

ROOT = Path(__file__).resolve().parents[1]
HUB = "moruku36/multi-ai-workflow"
OWNER = "moruku36"
ANCHOR = "f715e63bc2a76a02984c171d87d0b3bc94931676"
LEDGER = "central-review-reservation-v1"
RECEIPT = "dual-review-receipt"
LANES = ("alibaba", "cloudflare")
SHA = re.compile(r"[0-9a-f]{40}\Z")
REPO = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}\Z")
UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
LIMITS = {
    "installation_repositories": (1, 250),
    "pull_requests_per_repository": (1, 100),
    "ledger_entries": (1, 1000), "target_receipts": (1, 1000),
    "reservations_per_run": (1, 2), "reservations_per_utc_day": (1, 6),
    "github_response_bytes": (65536, 2000000),
    "github_timeout_seconds": (1, 30), "git_output_bytes": (65536, 131072),
    "git_timeout_seconds": (1, 30), "fetch_timeout_seconds": (1, 120),
    "fetch_observed_disk_bytes": (1048576, 268435456),
    "lane_timeout_seconds": (1, 240), "run_timeout_seconds": (1, 900),
    "target_output_bytes": (32768, 48000),
}


class Blocked(ValueError):
    """Deliberately carries no target/provider/error text."""


def require(condition):
    if not condition:
        raise Blocked()


def utc(value):
    require(isinstance(value, str) and UTC.fullmatch(value))
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        raise Blocked() from None


def stamp(value):
    require(value.tzinfo is not None and value.utcoffset().total_seconds() == 0)
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def sha(value):
    require(isinstance(value, str) and SHA.fullmatch(value))
    return value


def positive(value):
    require(type(value) is int and value > 0)
    return value


def token(name):
    value = os.environ.get(name, "")
    require(0 < len(value) <= 4096 and all(33 <= ord(c) <= 126 for c in value))
    return value


def json_bytes(value):
    return json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode("ascii")


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result)
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _value: require(False))


def validate_config(c):
    require(isinstance(c, dict) and set(c) == {
        "schema_version", "enabled", "paid_execution_authorized", "hub_repository",
        "owner", "anchor_sha", "activation_cutoff_env", "exclusions", "limits",
        "notes"})
    require(type(c["schema_version"]) is int and c["schema_version"] == 1)
    require(type(c["enabled"]) is bool and type(c["paid_execution_authorized"]) is bool)
    require((c["hub_repository"], c["owner"], c["anchor_sha"], c["activation_cutoff_env"])
            == (HUB, OWNER, ANCHOR, "CENTRAL_REVIEW_SINCE"))
    require(isinstance(c["exclusions"], dict) and set(c["exclusions"]) == {
        "hub", "private", "forks", "archived", "draft", "non_default_base"}
        and all(v is True for v in c["exclusions"].values()))
    require(isinstance(c["limits"], dict) and set(c["limits"]) == set(LIMITS))
    for name, (low, high) in LIMITS.items():
        require(type(c["limits"][name]) is int and low <= c["limits"][name] <= high)
    require(isinstance(c["notes"], dict) and set(c["notes"]) == {"en", "ja"})
    require(all(isinstance(v, str) and 0 < len(v) <= 4096 for v in c["notes"].values()))
    return c


def load_config():
    # No alternate path, target config, environment config or symlink traversal.
    path = ROOT / "config" / "central-review-hub.json"
    require(not path.parent.is_symlink() and not path.is_symlink())
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_size <= 16384)
        raw = stream.read(16385)
        require(len(raw) <= 16384)
    return validate_config(strict_json(raw))


class GitHub:
    """Fixed host, bounded responses/deadline, no redirect or automatic retry."""

    def __init__(self, limits, deadline):
        self.limits, self.deadline = limits, deadline
        self.key = token("GH_TOKEN")

    def __call__(self, method, path, payload=None):
        require(method in ("GET", "POST", "PATCH") and path.startswith("/")
                and not any(c in path for c in "\r\n#"))
        remaining = self.deadline - time.monotonic()
        require(remaining > 0)
        timeout = min(self.limits["github_timeout_seconds"], remaining)
        body = None if payload is None else json_bytes(payload)
        require(body is None or len(body) <= 60000)
        conn = http.client.HTTPSConnection("api.github.com", timeout=timeout)
        end = min(self.deadline, time.monotonic() + timeout)
        try:
            conn.request(method, path, body, {
                "Authorization": "Bearer " + self.key,
                "User-Agent": "central-review-hub", "Accept": "application/vnd.github+json",
                "Content-Type": "application/json", "X-GitHub-Api-Version": "2022-11-28"})
            response = conn.getresponse()
            require(response.status == (201 if method == "POST" else 200))
            link = response.getheader("Link", "")
            require(len(link) <= 4096)
            # Never follow the URL. Only a bounded, locally constructed next page.
            require(not link or all(re.fullmatch(r'<[^<>]+>; rel="(?:next|prev|first|last)"',
                                                part.strip()) for part in link.split(",")))
            chunks, size = [], 0
            while True:
                left = end - time.monotonic()
                require(left > 0)
                if conn.sock is not None:
                    conn.sock.settimeout(left)
                chunk = response.read1(min(65536, self.limits["github_response_bytes"] + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                require(size <= self.limits["github_response_bytes"])
            return strict_json(b"".join(chunks)), 'rel="next"' in link
        finally:
            conn.close()


def object_api(api, method, path, payload=None):
    result, more = api(method, path, payload)
    require(isinstance(result, dict) and not more)
    return result


def pages(api, path, key, maximum):
    """Complete counted GitHub collections, or fail closed; stable page size."""
    rows, expected, seen = [], None, set()
    page_size = min(50, maximum)
    for page in range(1, (maximum + page_size - 1) // page_size + 1):
        data, more = api("GET", path + f"&per_page={page_size}&page={page}")
        require(isinstance(data, dict) and isinstance(data.get(key), list))
        total, batch = data.get("total_count"), data[key]
        require(type(total) is int and 0 <= total <= maximum and len(batch) <= page_size)
        expected = total if expected is None else expected
        require(total == expected and len(rows) + len(batch) <= total)
        for row in batch:
            require(isinstance(row, dict))
            identity = positive(row.get("id"))
            require(identity not in seen)
            seen.add(identity)
        rows.extend(batch)
        if not more:
            require(len(rows) == expected)
            return rows
        require(len(batch) == page_size and len(rows) < expected)
    raise Blocked()


def checks(api, repository, head, name, maximum):
    return pages(api, f"/repos/{repository}/commits/{head}/check-runs?"
                 f"check_name={name}&filter=all", "check_runs", maximum)


def eligible_repo(repo):
    require(isinstance(repo, dict))
    name = repo.get("full_name")
    require(isinstance(name, str) and REPO.fullmatch(name)
            and isinstance(repo.get("owner"), dict))
    for field in ("private", "fork", "archived"):
        require(type(repo.get(field)) is bool)
    if (name.lower() == HUB.lower() or repo["owner"].get("login", "").lower() != OWNER
            or name.split("/")[0].lower() != OWNER or repo["private"]
            or repo["fork"] or repo["archived"] or repo.get("disabled", False)):
        return None
    default = repo.get("default_branch")
    require(isinstance(default, str) and 0 < len(default) <= 250
            and all(ord(c) >= 32 for c in default))
    return name, default


def eligible_pr(pr, repository, default, since):
    require(isinstance(pr, dict) and type(pr.get("draft")) is bool)
    positive(pr.get("number"))
    updated = utc(pr.get("updated_at"))
    if pr.get("state") != "open" or pr["draft"] or updated <= since:
        return False
    base, head = pr.get("base"), pr.get("head")
    require(isinstance(base, dict) and isinstance(head, dict))
    base_repo, head_repo = base.get("repo"), head.get("repo")
    if head_repo is None:  # Deleted fork/head repository.
        return False
    require(isinstance(base_repo, dict) and isinstance(head_repo, dict))
    if (base_repo.get("full_name") != repository or base.get("ref") != default
            or head_repo.get("full_name") != repository or head_repo.get("fork") is not False):
        return False
    sha(base.get("sha"))
    sha(head.get("sha"))
    return True


def discover(api, limits, since):
    repos = pages(api, "/installation/repositories?", "repositories",
                  limits["installation_repositories"])
    candidates = []
    for repo in repos:
        eligible = eligible_repo(repo)
        if eligible is None:
            continue
        repository, default = eligible
        # List endpoints lack total_count. A full last page is uncertain and
        # blocked even when it could mean exactly the configured maximum.
        maximum = limits["pull_requests_per_repository"]
        size, rows = min(50, maximum), []
        for page in range(1, (maximum + size - 1) // size + 1):
            batch, more = api("GET", f"/repos/{repository}/pulls?state=open&sort=updated"
                              f"&direction=asc&per_page={size}&page={page}")
            require(isinstance(batch, list) and len(batch) <= size
                    and len(rows) + len(batch) <= maximum)
            rows.extend(batch)
            if len(batch) < size and not more:
                break
            require(more and len(batch) == size and len(rows) < maximum)
        else:
            raise Blocked()
        numbers = set()
        for pr in rows:
            require(isinstance(pr, dict))
            number = positive(pr.get("number"))
            require(number not in numbers)
            numbers.add(number)
            if eligible_pr(pr, repository, default, since):
                candidates.append((utc(pr["updated_at"]), repository, number,
                                   pr["base"]["sha"], pr["head"]["sha"]))
    # Finish ALL bounded discovery before any reservation or paid lane.
    return sorted(candidates)


def current(api, repository, number, since):
    repo = object_api(api, "GET", f"/repos/{repository}")
    eligible = eligible_repo(repo)
    require(eligible is not None and eligible[0] == repository)
    default = eligible[1]
    pr = object_api(api, "GET", f"/repos/{repository}/pulls/{number}")
    require(pr.get("number") == number and eligible_pr(pr, repository, default, since))
    branch = object_api(api, "GET", f"/repos/{repository}/branches/{quote(default, safe='')}")
    tip = sha(branch["commit"]["sha"])
    require(pr["base"]["sha"] == tip)
    return tip, sha(pr["head"]["sha"])


class SafeGit:
    """No target config, helpers, hooks, prompts, lazy fetch or external protocols."""

    def __init__(self, limits, deadline, scratch):
        self.limits, self.deadline, self.scratch = limits, deadline, scratch
        self.binary = shutil.which("git")
        require(self.binary is not None)

    def run(self, repo, *args, fetch=False):
        env = {"PATH": os.defpath, "GIT_CONFIG_NOSYSTEM": "1",
               "GIT_CONFIG_SYSTEM": os.devnull, "GIT_CONFIG_GLOBAL": os.devnull,
               "GIT_TERMINAL_PROMPT": "0", "GIT_ATTR_NOSYSTEM": "1",
               "GIT_NO_LAZY_FETCH": "1", "GIT_ALLOW_PROTOCOL": "https",
               "GIT_PAGER": "cat", "LC_ALL": "C"}
        if fetch:
            header = base64.b64encode(("x-access-token:" + token("GH_TOKEN")).encode()).decode()
            env.update(GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="http.https://github.com/.extraheader",
                       GIT_CONFIG_VALUE_0="AUTHORIZATION: basic " + header)
        settings = {"core.hooksPath": os.devnull, "credential.helper": "",
                    "core.askPass": "", "init.templateDir": "",
                    "core.attributesFile": os.devnull, "core.excludesFile": os.devnull,
                    "gc.auto": "0", "maintenance.auto": "false",
                    "fetch.writeCommitGraph": "false", "fetch.recurseSubmodules": "false",
                    "submodule.recurse": "false", "http.followRedirects": "false",
                    "protocol.allow": "never", "protocol.https.allow": "always",
                    "pack.threads": "1"}
        command = [self.binary]
        for key, value in settings.items():
            command.extend(("-c", key + "=" + value))
        command.extend(args)
        end = min(self.deadline, time.monotonic() + self.limits[
            "fetch_timeout_seconds" if fetch else "git_timeout_seconds"])
        require(time.monotonic() < end)
        with tempfile.TemporaryFile(dir=self.scratch) as out, tempfile.TemporaryFile(dir=self.scratch) as err:
            proc = subprocess.Popen(command, cwd=repo, env=env, stdin=subprocess.DEVNULL,
                                    stdout=out, stderr=err, start_new_session=True)
            try:
                while True:
                    size = sum(p.stat().st_size for p in self.scratch.rglob("*") if p.is_file())
                    require(size <= self.limits["fetch_observed_disk_bytes"]
                            and out.tell() <= self.limits["git_output_bytes"]
                            and err.tell() <= self.limits["git_output_bytes"]
                            and time.monotonic() < end)
                    if proc.poll() is not None:
                        break
                    time.sleep(min(0.05, max(0, end - time.monotonic())))
                require(proc.returncode == 0)
                out.seek(0)
                data = out.read(self.limits["git_output_bytes"] + 1)
                require(len(data) <= self.limits["git_output_bytes"])
                return data
            finally:
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()


@contextmanager
def immutable_sources(auto, limits, deadline, repository, base, head):
    require(REPO.fullmatch(repository) and repository.split("/")[0].lower() == OWNER)
    sha(base)
    sha(head)
    with tempfile.TemporaryDirectory(prefix="central-review-") as directory:
        scratch = Path(directory)
        repo = scratch / "objects.git"
        repo.mkdir(mode=0o700)
        git = SafeGit(limits, deadline, scratch)
        git.run(repo, "init", "--bare", "--quiet")
        git.run(repo, "fetch", "--no-tags", "--no-recurse-submodules", "--no-write-fetch-head",
                "https://github.com/" + repository + ".git", base, head, fetch=True)
        for value in (base, head):
            require(git.run(repo, "rev-parse", "--verify", value + "^{commit}").decode().strip() == value)
        # Keep auto.collect's actual 20-path/64-KiB/binary/mode/symlink gates,
        # while bounding each of its Git outputs before decoding/allocation.
        previous = auto.git
        auto.git = git.run
        try:
            binding, diff, snapshots = auto.collect(repo, base, head)
        finally:
            auto.git = previous
        sha(binding["base_sha"])
        require(binding["head_sha"] == head)
        # The real Alibaba adapter materializes only these snapshots, not a
        # checkout. Never let target-controlled Git/OCR control files become
        # executable configuration in that scaffolding. Reject rather than omit.
        for path in snapshots:
            parts = path.casefold().split("/")
            require(not any(p.startswith(".") or "opencodereview" in p
                            or p in ("config.json", "rule.json") for p in parts))
        yield {"base_tip_sha": base, **binding}, diff, snapshots


def plain(value, maximum=512):
    """ASCII plain text, no mentions, HTML, code fences or Markdown directives."""
    require(isinstance(value, str))
    result, length = [], 0
    for char in value[:2048]:
        if char.isascii() and (char.isalnum() or char in " .,:;()/_-+=?!"):
            safe = char
        elif char.isspace():
            safe = " "
        else:
            safe = "\\u" + format(ord(char), "04x")
        if length + len(safe) > maximum:
            break
        result.append(safe)
        length += len(safe)
    return "".join(result)


def lane_metadata(auto, lane, result):
    require(isinstance(result, dict))
    findings, gaps = result.get("findings"), result.get("unresolved")
    require(isinstance(findings, list) and len(findings) <= 100
            and isinstance(gaps, list) and len(gaps) <= 100)
    attempts = result.get("http_attempts")
    require(type(attempts) is int and 1 <= attempts <= (8 if lane == "alibaba" else 1))
    previews = []
    for finding in findings[:10]:
        require(isinstance(finding, dict))
        previews.append({"path": plain(finding["path"], 200),
                         "start_line": positive(finding["start_line"]),
                         "end_line": positive(finding["end_line"]),
                         "content_untrusted": plain(finding["content"])})
    usage = result.get("usage", "unknown")
    if usage == "unknown":
        clean_usage = "unknown"
    else:
        require(isinstance(usage, (dict, list)))
        usage = [usage] if isinstance(usage, dict) else usage
        require(len(usage) <= 8 and all(isinstance(item, dict) for item in usage))
        clean_usage = auto.safe_usage(usage, 8 if lane == "alibaba" else 1)
    record = {"status": "completed", "reviewer_provider": "xiaomi",
              "reviewer_model": auto.connection.MODEL, "reviewer_id": lane + "-source-review",
              "scope": "diff-only", "http_attempts": attempts, "usage": clean_usage,
              "finding_count": len(findings), "gap_count": len(gaps),
              "findings_preview": previews, "findings_omitted": max(0, len(findings) - 10),
              "gaps_preview": [plain(gap) for gap in gaps[:10]],
              "gaps_omitted": max(0, len(gaps) - 10)}
    stats = auto.safe_diagnostics(lane, result)
    for key in ("completed_responses", "relay_halted", "cli_exit_code"):
        record[key] = stats[key]
    if lane == "alibaba":
        digest = result.get("binary_sha256")
        require(digest in auto.connection.BINARY_HASHES)
        record["binary_sha256"] = digest
    else:
        record["skill_revision"] = sha(result.get("skill_revision"))
    return record


def failed_lane_metadata(lane, diagnostics=None):
    # Lazy import preserves the disabled path's no-import/no-credential gate.
    # Reproject at IPC/persistence boundaries; never copy exception attributes or
    # arbitrary lane dictionaries into public Checks. Missing counts stay unknown.
    import automatic_dual_review as auto
    require(lane in LANES)
    return {"status": "FAILED_OR_UNKNOWN",
            "diagnostics": auto.safe_diagnostics(lane, diagnostics)}


def _lane_worker(pipe, auto, lane, binary, diff, snapshots, attempt_cap=None, attempt_deadline=None):
    # A whole-lane wall deadline also bounds slow/dribbling HTTP responses and
    # kills the CLI/relay process group on timeout. Never send raw bodies home.
    os.setsid()
    try:
        with open(os.devnull, "w") as sink, redirect_stdout(sink), redirect_stderr(sink):
            os.dup2(sink.fileno(), 1)
            os.dup2(sink.fileno(), 2)
            result = None
            try:
                result = (auto.alibaba(binary, snapshots, attempt_cap=attempt_cap,
                                       attempt_deadline=attempt_deadline) if lane == "alibaba"
                          else auto.cloudflare(diff, snapshots, attempt_cap=attempt_cap,
                                               attempt_deadline=attempt_deadline))
                record = lane_metadata(auto, lane, result)
            except auto.LaneError as exc:
                record = failed_lane_metadata(
                    lane, exc.diagnostics if exc.lane == lane else None)
            except Exception:
                stats = dict(result, failure_stage="lane_result") if type(result) is dict else None
                record = failed_lane_metadata(lane, stats)
            raw = json_bytes(record)
            require(len(raw) <= 32768)
            pipe.send_bytes(raw)
    finally:
        pipe.close()


def real_lane(auto, limits, deadline, lane, binary, diff, snapshots, attempt_cap=None,
              attempt_deadline=None):
    require(lane in LANES and os.name == "posix")
    end = min(deadline, time.monotonic() + limits["lane_timeout_seconds"])
    if attempt_deadline is not None:
        end = min(end, attempt_deadline)
    require(end > time.monotonic())
    context = multiprocessing.get_context("fork")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_lane_worker,
                              args=(sender, auto, lane, binary, diff, snapshots, attempt_cap, attempt_deadline))
    process.start()
    sender.close()
    try:
        require(receiver.poll(max(0, end - time.monotonic())))
        record = strict_json(receiver.recv_bytes(32768))
        process.join(max(0, end - time.monotonic()))
        require(process.exitcode == 0 and isinstance(record, dict))
        return record
    except Exception:
        return failed_lane_metadata(lane, {"failure_stage": "lane_worker"})
    finally:
        # setsid is first in the child; also terminate the worker if it failed
        # before establishing its group. Descendants must not outlive the lane.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        if process.is_alive():
            process.kill()
        process.join()
        receiver.close()
        process.close()


def preflight(auto):
    require(os.name == "posix" and "fork" in multiprocessing.get_all_start_methods())
    require(os.environ.get("GITHUB_REPOSITORY") == HUB)
    require(Path(auto.__file__).resolve() == ROOT / "tools/automatic_dual_review.py")
    require(auto.connection.MODEL == "mimo-v2.6-pro")
    token("GH_TOKEN")
    token("MIMO_API_KEY")
    auto.dual_review.verify_skill()
    for name in ("config.json", "rule.json"):
        require(not os.path.lexists(Path.home() / ".opencodereview" / name))
    binary = os.environ.get("OCR_BINARY", "")
    require(bool(binary))
    binary, _digest = auto.connection.checked_binary(Path(binary))
    require(os.access(binary, os.X_OK) and shutil.which("git") is not None)
    return binary


def check_summary(report, maximum):
    body = json_bytes(report).decode("ascii")
    # All source-derived strings have gone through plain(); no fence breakers
    # or mentions survive. Raw source/provider bodies are never included.
    summary = ("Partial source-only review; same provider/model; independence unverified. "
               "Untrusted finding previews require human resolution. No quality acceptance "
               "or merge authorization. Unknown outcomes consume reservations.\n\n```json\n"
               + body + "\n```")
    require(len(summary.encode()) <= maximum)
    return {"title": "Central review receipt", "summary": summary}


def create_check(api, repository, name, head, identity, output, **extra):
    payload = {"name": name, "head_sha": head, "external_id": identity,
               "status": "in_progress", "output": output, **extra}
    created = object_api(api, "POST", f"/repos/{repository}/check-runs", payload)
    check_id = positive(created.get("id"))
    # Acknowledgment alone is insufficient: require durable readable state.
    saved = object_api(api, "GET", f"/repos/{repository}/check-runs/{check_id}")
    require(saved.get("name") == name and saved.get("head_sha") == head
            and saved.get("external_id") == identity and saved.get("output", {}).get("summary") == output["summary"])
    return check_id


def validate_one_shot(request, *, controller_revision, now):
    """Legacy read-only proposal validation; never grants execution authority.

    Retained for existing offline checks. Production uses signed envelopes,
    not this proposal's evidence digest or caller-supplied revision.
    """
    require(isinstance(request, dict) and set(request) == {
        'repository', 'pr', 'base', 'head', 'controller_revision', 'expires_at',
        'eligible_since', 'lane_attempt_limits', 'authorization_evidence_sha256'})
    repository = request['repository']
    require(isinstance(repository, str) and REPO.fullmatch(repository)
            and repository.split('/')[0] == OWNER and repository.lower() != HUB.lower())
    positive(request['pr'])
    for key in ('base', 'head', 'controller_revision'):
        sha(request[key])
    require(request['controller_revision'] == sha(controller_revision))
    require(utc(request['eligible_since']) <= now < utc(request['expires_at']))
    require((utc(request['expires_at']) - now).total_seconds() <= 3600)
    limits = request['lane_attempt_limits']
    require(isinstance(limits, dict) and set(limits) == set(LANES))
    for lane, cap in (('alibaba', 8), ('cloudflare', 1)):
        require(type(limits[lane]) is int and 1 <= limits[lane] <= cap)
    require(isinstance(request['authorization_evidence_sha256'], str)
            and re.fullmatch(r'[0-9a-f]{64}', request['authorization_evidence_sha256']))
    return dict(request)


class Hub:
    """The injected seams never replace production lanes with synthetic success."""

    def __init__(self, config, *, api, sources, lanes, preflight, now=None, deadline=None):
        self.config = validate_config(config)
        self.limits = config["limits"]
        self.api, self.sources, self.lanes, self.preflight = api, sources, lanes, preflight
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.deadline = deadline or (time.monotonic() + self.limits["run_timeout_seconds"])
        self.aggregate = {"status": "BLOCKED_OR_UNKNOWN", "reservations": 0,
                          "completed": 0, "failed_or_unknown": 0}
        self.run_id = uuid.uuid4().hex

    def prepare_one_shot(self, envelope):
        """Verify operator AND launcher; no injectable authorization callback.

        Runtime provenance verification uses GitHub OIDC, not a local paid route.
        The old digest-only proposal contract is deliberately unsupported.
        """
        import central_one_shot_auth as auth
        from central_one_shot_provenance import verify_launcher
        revision = auth.controller_revision(self.deadline)
        validation_started = time.monotonic()
        request, authorization_deadline = auth.verify_envelope(
            envelope, revision=revision, now=self.now(),
            validation_started=validation_started, deadline=self.deadline)
        verify_launcher(revision=revision, envelope=envelope, deadline=authorization_deadline)
        auth.active(request, self.now())
        require(time.monotonic() < authorization_deadline)
        return request, authorization_deadline

    def run_one_shot(self, envelope):
        try:
            request, authorization_deadline = self.prepare_one_shot(envelope)
            binary = self.preflight()
            since = utc(request["eligible_since"])
            # Exactly one target. Never call installation/PR discovery here.
            candidates = [(since, request["repository"], request["pr"],
                           request["base"], request["head"])]
            return self._run_targets(candidates, since, binary, authorization=request,
                                     authorization_deadline=authorization_deadline)
        except Exception:
            self.aggregate["status"] = "BLOCKED_OR_UNKNOWN"
            self.aggregate["failed_or_unknown"] = max(1, self.aggregate["failed_or_unknown"])
            return dict(self.aggregate)

    def ledger(self):
        # A missing anchor, unavailable collection, corrupt row or any
        # truncation stops ALL paid work; no local/empty-ledger fallback.
        anchor = object_api(self.api, "GET", f"/repos/{HUB}/commits/{ANCHOR}")
        require(anchor.get("sha") == ANCHOR)
        rows = checks(self.api, HUB, ANCHOR, LEDGER, self.limits["ledger_entries"])
        identities, today, current_run = set(), 0, 0
        day = self.now().date()
        for row in rows:
            require(row.get("name") == LEDGER and row.get("head_sha") == ANCHOR)
            external = row.get("external_id")
            require(isinstance(external, str) and re.fullmatch(r"central-v1:[0-9a-f]{64}", external))
            started = utc(row.get("started_at"))
            meta = strict_json(row["output"]["summary"])
            require(isinstance(meta, dict) and set(meta) == {
                "schema_version", "run_id", "reserved_at", "identity_hash", "consumed",
                "state", "refunds", "retries"})
            require(type(meta["schema_version"]) is int and meta["schema_version"] == 1
                    and meta["consumed"] is True and meta["refunds"] is False
                    and meta["retries"] is False and meta["state"] == "RESERVED_OUTCOME_UNKNOWN"
                    and isinstance(meta["run_id"], str) and re.fullmatch(r"[0-9a-f]{32}", meta["run_id"])
                    and external == "central-v1:" + meta["identity_hash"])
            reserved = utc(meta["reserved_at"])
            # Count across a midnight boundary conservatively on either date.
            require(started.date() <= day and reserved.date() <= day)
            today += int(day in (started.date(), reserved.date()))
            current_run += int(meta["run_id"] == self.run_id)
            identities.add(external)
        return identities, today, current_run

    def target_seen(self, repository, base, head):
        identity = base + ":" + head
        rows = checks(self.api, repository, head, RECEIPT, self.limits["target_receipts"])
        require(all(row.get("name") == RECEIPT and row.get("head_sha") == head for row in rows))
        return any(row.get("external_id") == identity for row in rows)

    def update_target(self, repository, check_id, identity, head, report, conclusion=None):
        payload = {"status": "completed" if conclusion else "in_progress",
                   "output": check_summary(report, self.limits["target_output_bytes"])}
        if conclusion:
            payload.update(conclusion=conclusion, completed_at=stamp(self.now()))
        object_api(self.api, "PATCH", f"/repos/{repository}/check-runs/{check_id}", payload)
        saved = object_api(self.api, "GET", f"/repos/{repository}/check-runs/{check_id}")
        require(saved.get("external_id") == identity and saved.get("head_sha") == head
                and saved.get("name") == RECEIPT and saved.get("status") == payload["status"]
                and saved.get("output", {}).get("summary") == payload["output"]["summary"]
                and (not conclusion or saved.get("conclusion") == conclusion))

    def run(self, environ=None):
        env = os.environ if environ is None else environ
        try:
            if env.get("CENTRAL_REVIEW_ENABLED") != "true" or not self.config["enabled"]:
                self.aggregate["status"] = "DISABLED"
                return dict(self.aggregate)
            since = utc(env.get("CENTRAL_REVIEW_SINCE"))
            require(since <= self.now() and self.config["paid_execution_authorized"])
            binary = self.preflight()
            self.ledger()
            candidates = discover(self.api, self.limits, since)
            return self._run_targets(candidates, since, binary)
        except Exception:
            self.aggregate["status"] = "BLOCKED_OR_UNKNOWN"
            self.aggregate["failed_or_unknown"] = max(1, self.aggregate["failed_or_unknown"])
        return dict(self.aggregate)

    def _run_targets(self, candidates, since, binary, authorization=None,
                     authorization_deadline=None):
        """ONE reservation/receipt lifecycle, shared by both production modes."""
        try:
            attempt_deadline = None
            if authorization is not None:
                from central_one_shot_auth import active, validate_lane_attempt_limits
                require(authorization_deadline is not None)
                validate_lane_attempt_limits(authorization["lane_attempt_limits"])
                attempt_deadline = min(self.deadline, authorization_deadline)

            def check_authorization():
                if authorization is not None:
                    active(authorization, self.now())
                    require(time.monotonic() < attempt_deadline)

            any_failure = False
            for _updated, repository, number, base, head in candidates:
                require(time.monotonic() < self.deadline)
                if authorization is not None:
                    check_authorization()
                    require(len(candidates) == 1 and (repository, number, base, head) == tuple(
                        authorization[k] for k in ("repository", "pr", "base", "head")))
                if self.aggregate["reservations"] >= self.limits["reservations_per_run"]:
                    break
                if current(self.api, repository, number, since) != (base, head):
                    require(authorization is None)
                    continue
                digest = hashlib.sha256((repository.lower() + "\0" + base + "\0" + head).encode()).hexdigest()
                external, target_identity = "central-v1:" + digest, base + ":" + head
                identities, today, run_count = self.ledger()
                if external in identities or self.target_seen(repository, base, head):
                    require(authorization is None)
                    continue
                if today >= self.limits["reservations_per_utc_day"]:
                    require(authorization is None)
                    break
                require(run_count < self.limits["reservations_per_run"])
                check_authorization()
                # Global reservation BEFORE target reservation BEFORE sources.
                # Increment locally before a possibly ambiguous POST; never retry.
                self.aggregate["reservations"] += 1
                meta = {"schema_version": 1, "run_id": self.run_id,
                        "reserved_at": stamp(self.now()), "identity_hash": digest,
                        "consumed": True, "state": "RESERVED_OUTCOME_UNKNOWN",
                        "refunds": False, "retries": False}
                create_check(self.api, HUB, LEDGER, ANCHOR, external,
                             {"title": "Consumed reservation; no retry or refund",
                              "summary": json_bytes(meta).decode()},
                             status="completed", conclusion="action_required",
                             started_at=stamp(self.now()),
                             completed_at=stamp(self.now()))
                identities, today, run_count = self.ledger()
                require(external in identities and today <= self.limits["reservations_per_utc_day"]
                        and run_count <= self.limits["reservations_per_run"])
                # Recheck existing target reservations; never edit somebody
                # else's reservation, even if it failed or is incomplete.
                require(not self.target_seen(repository, base, head))
                report = {"schema_version": 1, "base_tip_sha": base, "head_sha": head,
                          "status": "RESERVED_OUTCOME_UNKNOWN", "lanes": {},
                          "merge_authorized": False, "review_quality_accepted": False,
                          "independence": "NOT_VERIFIED_SAME_PROVIDER"}
                if authorization is not None:
                    # Fixed, public-safe attribution; no token/signature/private evidence.
                    from central_one_shot_auth import canonical, DOMAIN
                    report["one_shot"] = {
                        "issuer": authorization["issuer"], "key_id": authorization["key_id"],
                        "controller_revision": authorization["controller_revision"],
                        "eligible_since": authorization["eligible_since"],
                        "expires_at": authorization["expires_at"],
                        "lane_attempt_limits": dict(authorization["lane_attempt_limits"]),
                        "payload_sha256": hashlib.sha256(DOMAIN + canonical(authorization)).hexdigest()}
                check_authorization()
                check_id = create_check(self.api, repository, RECEIPT, head, target_identity,
                                        check_summary(report, self.limits["target_output_bytes"]))
                with ExitStack() as source_stack:
                    # Only source entry/extraction and binding validation are
                    # recoverable here. API/marker ambiguity stops the whole run.
                    try:
                        binding, diff, snapshots = source_stack.enter_context(
                            self.sources(repository, base, head))
                        require(binding["base_tip_sha"] == base and binding["head_sha"] == head)
                        sha(binding["base_sha"])
                        require(re.fullmatch(r"[0-9a-f]{64}", binding["diff_sha256"]))
                    except Exception:
                        report["status"] = "SOURCE_BLOCKED_OR_UNKNOWN"
                        self.update_target(repository, check_id, target_identity, head, report, "failure")
                        self.aggregate["failed_or_unknown"] += 1
                        any_failure = True
                        continue
                    report = {**binding, **report}
                    for lane in LANES:
                        require(time.monotonic() < self.deadline)
                        check_authorization()
                        require(current(self.api, repository, number, since) == (base, head))
                        # Never carry paid calls into a new UTC day using an
                        # earlier day's reservation. Keep the consumed marker.
                        require(utc(meta["reserved_at"]).date() == self.now().date())
                        report["lanes"][lane] = {**binding, "status": "OUTCOME_UNKNOWN"}
                        self.update_target(repository, check_id, target_identity, head, report)
                        # A durable unknown marker must be readable before any
                        # provider request, including after an earlier failure.
                        require(time.monotonic() < self.deadline)
                        require(current(self.api, repository, number, since) == (base, head))
                        require(utc(meta["reserved_at"]).date() == self.now().date())
                        check_authorization()
                        try:
                            outcome = (self.lanes(lane, binary, diff, snapshots) if authorization is None
                                       else self.lanes(lane, binary, diff, snapshots,
                                                       attempt_cap=authorization["lane_attempt_limits"][lane],
                                                       attempt_deadline=attempt_deadline))
                            require(isinstance(outcome, dict) and outcome.get("status") in
                                    ("completed", "FAILED_OR_UNKNOWN"))
                        except Exception:
                            outcome = failed_lane_metadata(lane)
                        if outcome["status"] == "FAILED_OR_UNKNOWN":
                            outcome = failed_lane_metadata(lane, outcome.get("diagnostics"))
                        report["lanes"][lane] = {**outcome, **binding}
                        self.update_target(repository, check_id, target_identity, head, report)
                    complete = all(report["lanes"][lane]["status"] == "completed" for lane in LANES)
                    findings = sum(r.get("finding_count", 0) for r in report["lanes"].values())
                    gaps = sum(r.get("gap_count", 0) for r in report["lanes"].values())
                    try:
                        stale = current(self.api, repository, number, since) != (base, head)
                    except Exception:
                        stale = True  # Unverifiable current revision is a failure.
                    report["status"] = ("STALE_OR_UNVERIFIABLE" if stale else
                                        "BOTH_RECORDED_NOT_ACCEPTED" if complete else "INCOMPLETE")
                    conclusion = ("failure" if stale or not complete else
                                  "action_required" if findings or gaps else "success")
                    self.update_target(repository, check_id, target_identity, head, report, conclusion)
                    failed = stale or not complete
                    self.aggregate["failed_or_unknown"] += int(failed)
                    self.aggregate["completed"] += int(not failed)
                    any_failure |= failed
            self.aggregate["status"] = "BLOCKED_OR_UNKNOWN" if any_failure else "COMPLETE"
        except Exception:
            self.aggregate["status"] = "BLOCKED_OR_UNKNOWN"
            self.aggregate["failed_or_unknown"] = max(1, self.aggregate["failed_or_unknown"])
        return dict(self.aggregate)


def main():
    summary = {"status": "BLOCKED_OR_UNKNOWN", "reservations": 0,
               "completed": 0, "failed_or_unknown": 0}
    # No raw exception, provider body, source, finding or repository name may
    # reach the hub console, including a background HTTPServer traceback.
    try:
        with open(os.devnull, "w") as sink, redirect_stdout(sink), redirect_stderr(sink):
            envelope_text = os.environ.get("CENTRAL_ONE_SHOT_ENVELOPE", "")
            one_shot = bool(envelope_text)
            if not one_shot and os.environ.get("CENTRAL_REVIEW_ENABLED") != "true":
                summary["status"] = "DISABLED"  # No config/key/import/API work.
            else:
                config = load_config()
                if not one_shot and not config["enabled"]:
                    summary["status"] = "DISABLED"
                else:
                    sys.dont_write_bytecode = True
                    limits = config["limits"]
                    deadline = time.monotonic() + limits["run_timeout_seconds"]
                    if one_shot:
                        require(len(envelope_text) <= 8192)
                        envelope = envelope_text.encode("ascii")
                    else:
                        utc(os.environ.get("CENTRAL_REVIEW_SINCE"))
                        require(config["paid_execution_authorized"])
                        from central_one_shot_auth import controller_revision
                        from central_one_shot_provenance import verify_launcher
                        revision = controller_revision(deadline)
                        verify_launcher(revision=revision, envelope=None, deadline=deadline)
                    import automatic_dual_review as auto
                    api = GitHub(limits, deadline)
                    hub = Hub(config, api=api,
                              sources=lambda repo, base, head: immutable_sources(
                                  auto, limits, deadline, repo, base, head),
                              lanes=lambda lane, binary, diff, snapshots, attempt_cap=None, attempt_deadline=None: real_lane(
                                  auto, limits, deadline, lane, binary, diff, snapshots,
                                  attempt_cap, attempt_deadline),
                              preflight=lambda: preflight(auto), deadline=deadline)
                    summary = hub.run_one_shot(envelope) if one_shot else hub.run()
    except Exception:
        summary["failed_or_unknown"] = 1
    print(json.dumps(summary, sort_keys=True))
    return int(summary["status"] == "BLOCKED_OR_UNKNOWN")


if __name__ == "__main__":
    raise SystemExit(main())
