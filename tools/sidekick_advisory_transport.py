#!/usr/bin/env python3
"""Publish one neutral HOLD advisory for the frozen public Sidekick PR."""

import hashlib
import http.client
import json
import os
import re
import subprocess
import sys
import time

HUB = "moruku36/multi-ai-workflow"
HUB_ID = 1365934149
HUB_MAIN = "f13e899ffd3270776a7f3b248c115f42b1566d4e"
HUB_REPO = f"/repos/{HUB}"
TAG_REF = "refs/tags/sidekick-hold-26-20261121"
OWNER_ID = 12478466
TARGET = "moruku36/local-ai-sidekick"
TARGET_ID = 1369269341
PR = 26
PR_ID = 5372674586
BASE = "c9b1e3c68e9d897aee355361eaaffd038fe7e23e"
HEAD = "4b6cb7c0d1ebf224fa7c1d053c3fee9a4464c20c"
CANDIDATE = "2ed45d1726402efc722ac5bd03917cc00d4d91db"
CANDIDATE_TREE = "de48270e5e3342ab683cbb6e3b0d160f99b640e0"
RULES_SHA256 = "2e77fbec4f2baf8cfda413b92565974b0ac72247806e4b57e12d4c9d8e8019d2"
CI_ID = 135080128831
CI_APP_ID = 15368
APP_ID = 5715914
APP_SLUG = "moruku36-central-source-review"
INSTALLATION_ID = 180960402
NAME = "central-hub-advisory-transport-v1"
EXTERNAL_ID = f"{NAME}:{TARGET_ID}:{PR}:{HEAD}"
REPO = f"/repos/{TARGET}"
CHECK = {
    "name": NAME,
    "head_sha": HEAD,
    "external_id": EXTERNAL_ID,
    "status": "completed",
    "conclusion": "neutral",
    "output": {
        "title": "HOLD — Sidekick transport advisory",
        "summary": ("HOLD. Advisory transport only. This is neither a provider review nor an "
                    "accepted review. This check grants no merge authority."),
    },
}
MAX_RESPONSE = 4 * 1024 * 1024
PAGE_SIZE = 50
MAX_PAGES = 10
PINNED_RELEASE = "e0b679cc4c101b55b408361cfeffbb20b79b38b9"
CHECK_ID = 136774058834
CLASSIC_SHA256 = "a277945f0f1f109f55e2565dba4b1d735015a05afba596f2c57060085254a883"
VISIBILITY_DELAYS = (1, 2)


class Blocked(ValueError):
    """A fixed diagnostic safe for the workflow log."""


class NotFound(Blocked):
    """A GET returned HTTP 404."""


class Invisible(Blocked):
    """The acknowledged check is not publicly visible yet."""


def require(condition, message):
    if not condition:
        raise Blocked(message)


def verify_source(api):
    release = os.environ.get("GITHUB_SHA", "")
    require(re.fullmatch(r"[0-9a-f]{40}", release) and release not in ("0" * 40, HUB_MAIN)
            and os.environ.get("GITHUB_EVENT_NAME") == "push"
            and os.environ.get("GITHUB_REF") == TAG_REF
            and os.environ.get("GITHUB_REPOSITORY") == HUB
            and os.environ.get("GITHUB_REPOSITORY_ID") == str(HUB_ID)
            and os.environ.get("GITHUB_ACTOR_ID") == str(OWNER_ID)
            and os.environ.get("GITHUB_RUN_ATTEMPT") == "1", "Unexpected Hub run identity.")
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as event_file:
        event = json.load(event_file, object_pairs_hook=unique_object)
    repo = event["repository"]
    require(is_repo(repo, HUB, HUB_ID) and repo["default_branch"] == "main"
            and event["ref"] == TAG_REF and event["created"] is True
            and event["deleted"] is False and event["forced"] is False
            and event["before"] == "0" * 40 and event["after"] == release,
            "Unexpected Hub tag creation event.")
    checked_out = subprocess.check_output(
        ["/usr/bin/git", "rev-parse", "--verify", "HEAD"], env={},
        stderr=subprocess.DEVNULL, text=True, timeout=5).strip()
    require(checked_out == release, "Hub checkout does not match the tagged revision.")
    verify_public_source(api, release)


def verify_public_source(api, release):
    require(is_public_main(api.one(HUB_REPO), HUB, HUB_ID), "Public Hub repository drifted.")
    main = api.one(f"{HUB_REPO}/branches/main")
    require(main["name"] == "main" and main["commit"]["sha"] == HUB_MAIN, "Hub main drifted.")
    tag = api.one(f"{HUB_REPO}/git/ref/{TAG_REF.removeprefix('refs/')}")
    require(tag["ref"] == TAG_REF and tag["object"]["type"] == "commit"
            and tag["object"]["sha"] == release, "Hub tag is not the exact lightweight release tag.")
    verify_git_commit(api, HUB_REPO, release, [HUB_MAIN])


def unique_object(pairs):
    result = dict(pairs)
    require(len(result) == len(pairs), "Ambiguous JSON object.")
    return result


class RateLimited(Blocked):
    pass


class GitHub:
    def __init__(self, token=None):
        require(token is None or re.fullmatch(r"[A-Za-z0-9_\-.]+", token),
                "Installation token unavailable.")
        self.token = token

    def request(self, path, *, authenticated=False, payload=None):
        # A fixed HTTPS host without redirects, proxies or retry. Public branch
        # and rules reads need no additional installation permission.
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": NAME,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if authenticated:
            require(self.token is not None, "Installation token unavailable.")
            headers["Authorization"] = "Bearer " + self.token
        body = None
        if payload is not None:
            require(authenticated, "Check write requires the installation token.")
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode("utf-8")
        connection = http.client.HTTPSConnection("api.github.com", timeout=10)
        try:
            connection.request("GET" if body is None else "POST", path, body, headers)
            response = connection.getresponse()
            if body is None and response.status == 404:
                raise NotFound("GitHub returned HTTP 404.")
            if (body is None and response.status in (403, 429)
                    and response.getheader("X-RateLimit-Remaining", "") == "0"):
                raise RateLimited(f"GitHub returned HTTP {response.status} (rate limit exhausted).")
            require(response.status == (200 if body is None else 201),
                    f"GitHub returned HTTP {response.status}.")
            link = response.getheader("Link", "")
            relations = set()
            parts = link.split(",") if link else ()
            for part in parts:
                match = re.fullmatch(r'<[^<>]+>; rel="(next|prev|first|last)"', part.strip())
                require(match and match[1] not in relations, "Unreadable GitHub pagination.")
                relations.add(match[1])
            raw = response.read(MAX_RESPONSE + 1)
            require(len(raw) <= MAX_RESPONSE, "GitHub response exceeds its read limit.")
            return json.loads(raw, object_pairs_hook=unique_object), relations
        finally:
            connection.close()

    def one(self, path, **kwargs):
        result, relations = self.request(path, **kwargs)
        require(not relations, "Unexpected pagination for a single GitHub response.")
        return result


class ReadbackGitHub(GitHub):
    # Read-only client: refuses every payload before any network use and sends the
    # ephemeral read token (if one exists) on GET requests only.
    def request(self, path, *, authenticated=False, payload=None):
        require(payload is None, "Read-only client cannot write.")
        return super().request(path, authenticated=self.token is not None)


def is_repo(repo, name, identity):
    return (type(repo["id"]) is int and repo["id"] == identity and repo["full_name"] == name
            and type(repo["owner"]["id"]) is int and repo["owner"]["id"] == OWNER_ID)


def is_public_main(repo, name, identity):
    return (is_repo(repo, name, identity) and repo["private"] is False
            and repo["visibility"] == "public" and repo["default_branch"] == "main")


def verify_git_commit(api, repo, sha, parents, *, tree=None):
    commit = api.one(f"{repo}/git/commits/{sha}")
    require(commit["sha"] == sha and isinstance(commit["parents"], list)
            and [parent["sha"] for parent in commit["parents"]] == parents
            and (tree is None or commit["tree"]["sha"] == tree), "Git commit tuple drifted.")


def verify_scope(api):
    require(os.environ.get("SIDEKICK_INSTALLATION_ID") == str(INSTALLATION_ID)
            and os.environ.get("SIDEKICK_APP_SLUG") == APP_SLUG, "Installation action identity mismatch.")
    scope = api.one("/installation/repositories?per_page=2", authenticated=True)
    repos = scope["repositories"]
    require(type(scope["total_count"]) is int and scope["total_count"] == 1
            and isinstance(repos, list) and len(repos) == 1,
            "Installation token scope differs from the one allowed repository.")
    require(is_public_main(repos[0], TARGET, TARGET_ID), "Installation repository identity drifted.")


def ci_identity(row):
    app_id = row["app"]["id"]
    return {"id": row["id"], "head_sha": row["head_sha"], "name": row["name"],
            "external_id": row["external_id"], "status": row["status"],
            "conclusion": row["conclusion"], "app_id": app_id}


def verify_checks(api, *, authenticated=False, published_id=None, expected_ci=None):
    commit = f"{REPO}/commits/{HEAD}"
    suites, relations = api.request(f"{commit}/check-suites?per_page=1", authenticated=authenticated)
    # The check-runs endpoint can omit runs beyond the most recent 1,000 suites.
    suite_count = suites["total_count"]
    require(type(suite_count) is int and 0 <= suite_count < 1000
            and isinstance(suites["check_suites"], list)
            and len(suites["check_suites"]) == min(suite_count, 1)
            and ("next" in relations) == (suite_count > 1),
            "Cannot establish a complete check-run scan for this head.")

    seen = set()
    expected = None
    ci = None
    published_seen = False
    for page in range(1, MAX_PAGES + 1):
        listing, relations = api.request(
            f"{commit}/check-runs?filter=all&per_page={PAGE_SIZE}&page={page}",
            authenticated=authenticated)
        count, rows = listing["total_count"], listing["check_runs"]
        if expected is None:
            expected = count
        require(type(count) is int and count == expected and 0 <= count <= PAGE_SIZE * MAX_PAGES
                and isinstance(rows, list) and len(rows) == min(PAGE_SIZE, count - len(seen)),
                "Incomplete or changing check-run listing.")
        for row in rows:
            identity, name, external_id = row["id"], row["name"], row["external_id"]
            require(type(identity) is int and identity > 0 and identity not in seen
                    and row["head_sha"] == HEAD and isinstance(name, str)
                    and (external_id is None or isinstance(external_id, str)),
                    "Unreadable or changing check run on this head.")
            if identity == CI_ID:
                app_id = row["app"]["id"]
                require(name == "ci-gate" and type(app_id) is int and app_id == CI_APP_ID
                        and row["status"] == "completed" and row["conclusion"] == "success",
                        "The pinned CI check did not match.")
                ci = row
            if identity == published_id or name.casefold() == NAME or external_id == EXTERNAL_ID:
                require(identity == published_id, "Unexpected advisory context or transport ID.")
                verify_published(row, published_id)
                published_seen = True
            seen.add(identity)
        require(("next" in relations) == (len(seen) < count), "Incomplete check-run pagination.")
        if "next" not in relations:
            require(ci is not None, "The pinned CI check was not found.")
            pinned_ci = ci_identity(ci)
            require(expected_ci is None or pinned_ci == expected_ci, "The pinned CI check changed.")
            if published_id is not None and not published_seen:
                raise Invisible("Published check missing from the scan.")
            return pinned_ci
    raise Blocked("Check-run scan exceeded its page limit.")


def verify_pull(api):
    pull = api.one(f"{REPO}/pulls/{PR}")
    require(type(pull["number"]) is int and pull["number"] == PR
            and type(pull["id"]) is int and pull["id"] == PR_ID
            and type(pull["user"]["id"]) is int and pull["user"]["id"] == OWNER_ID
            and pull["state"] == "open" and pull["draft"] is False,
            "Sidekick PR is no longer the allowed open non-draft PR.")
    base, head = pull["base"], pull["head"]
    require(is_repo(base["repo"], TARGET, TARGET_ID) and is_repo(head["repo"], TARGET, TARGET_ID)
            and base["repo"]["default_branch"] == "main" and base["ref"] == "main"
            and base["sha"] == BASE and head["sha"] == HEAD and pull["merge_commit_sha"] == CANDIDATE,
            "Sidekick PR tuple drifted.")
    verify_git_commit(api, REPO, CANDIDATE, [BASE, HEAD], tree=CANDIDATE_TREE)


def fingerprint(value):
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_protection(api):
    rules = api.one(f"{REPO}/rules/branches/main?per_page=100")
    require(isinstance(rules, list) and len(rules) < 100 and fingerprint(rules) == RULES_SHA256,
            "Effective Sidekick branch rules drifted or are incomplete.")
    contexts = []
    for rule in rules:
        require(isinstance(rule["type"], str) and rule["type"], "Unreadable branch rule type.")
        if rule["type"] == "required_status_checks":
            checks = rule["parameters"]["required_status_checks"]
            require(isinstance(checks, list), "Unreadable ruleset status checks.")
            contexts.extend(check["context"] for check in checks)

    branch = api.one(f"{REPO}/branches/main")
    require(branch["name"] == "main" and branch["commit"]["sha"] == BASE,
            "Sidekick main tip drifted.")
    protection = branch["protection"]
    protected, classic_enabled = branch["protected"], protection["enabled"]
    require(protected is True and type(classic_enabled) is bool and (classic_enabled or rules),
            "Unreadable branch protection.")
    status = protection["required_status_checks"]
    classic_contexts, classic_checks = status["contexts"], status.get("checks", [])
    require(isinstance(classic_contexts, list) and isinstance(classic_checks, list),
            "Unreadable classic required status checks.")
    contexts.extend(classic_contexts)
    contexts.extend(check["context"] for check in classic_checks)
    require(all(isinstance(context, str) and context for context in contexts),
            "Unreadable required-check context.")
    require(all(context.casefold() != NAME for context in contexts),
            "Advisory name collides with a required check on Sidekick main.")
    return fingerprint(protection)


def verify_target(api):
    require(is_public_main(api.one(REPO), TARGET, TARGET_ID), "Public Sidekick repository drifted.")
    verify_pull(api)
    return verify_protection(api)


def verify_published(saved, identity):
    app_id = saved["app"]["id"]
    require(type(saved["id"]) is int and saved["id"] == identity
            and type(app_id) is int and app_id == APP_ID and saved["app"]["slug"] == APP_SLUG
            and all(saved[field] == CHECK[field] for field in
                    ("head_sha", "name", "external_id", "status", "conclusion"))
            and all(saved["output"][field] == CHECK["output"][field] for field in ("title", "summary")),
            "Published check did not match the HOLD advisory.")


def acknowledge_write(api):
    created = api.one(f"{REPO}/check-runs", authenticated=True, payload=CHECK)
    identity = created["id"]
    require(type(identity) is int and identity > 0, "Missing created check ID.")
    return identity


def read_published(api, identity):
    try:
        saved = api.one(f"{REPO}/check-runs/{identity}")
    except NotFound:
        raise Invisible("Published check is not directly visible yet.") from None
    verify_published(saved, identity)


def visible(operation):
    for delay in (*VISIBILITY_DELAYS, None):
        try:
            return operation()
        except Invisible:
            if delay is None:
                raise
            time.sleep(delay)


def preflight():
    require(os.environ.get("CONFIGURED_APP_ID") == str(APP_ID), "Configured App ID mismatch.")
    api = GitHub()
    verify_source(api)
    classic = verify_target(api)
    verify_checks(api)
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"classic-protection-sha256={classic}\n")


def recheck_release(api, classic):
    verify_source(api)
    require(verify_target(api) == classic, "Classic Sidekick branch protection changed.")


def phased(phase, operation):
    # Fixed phase labels only; no raw body, headers or token text.
    try:
        return operation()
    except Blocked as error:
        raise Blocked(f"{phase}: {error}") from None
    except (ValueError, OSError, http.client.HTTPException, subprocess.SubprocessError,
            KeyError, TypeError, AttributeError, RecursionError):
        raise Blocked(f"{phase}: Unreadable input or GitHub response.") from None


def check_protection(api):
    require(verify_target(api) == CLASSIC_SHA256, "Classic Sidekick branch protection changed.")


def reconcile():
    # GET-only: the optional ephemeral read token is never a write credential and
    # the client refuses every payload. Anonymous mode remains when it is absent.
    api = ReadbackGitHub(os.environ.get("SIDEKICK_READBACK_TOKEN") or None)
    phased("source", lambda: verify_public_source(api, PINNED_RELEASE))
    phased("protection", lambda: check_protection(api))
    phased("direct-readback", lambda: visible(lambda: read_published(api, CHECK_ID)))
    phased("listing", lambda: visible(lambda: verify_checks(api, published_id=CHECK_ID)))
    print(f"Reconciled existing neutral Sidekick HOLD advisory check {CHECK_ID}; "
          "no new check was published.")


def main(args):
    phase = None
    identity = None
    reconciling = args == ["reconcile"]
    try:
        if args == ["preflight"]:
            preflight()
            return 0
        if reconciling:
            reconcile()
            return 0
        require(not args, "Unknown transport command.")
        api = GitHub(os.environ.get("SIDEKICK_APP_TOKEN", ""))
        verify_scope(api)
        classic = os.environ.get("CLASSIC_PROTECTION_SHA256", "")
        require(re.fullmatch(r"[0-9a-f]{64}", classic), "Missing preflight protection fingerprint.")
        recheck_release(api, classic)
        ci = verify_checks(api, authenticated=True)
        phase = "post-acknowledgment"
        print("Submitting the single HOLD advisory check.", flush=True)
        identity = acknowledge_write(api)
        public = GitHub()
        phase = "direct-readback"
        visible(lambda: read_published(public, identity))
        phase = "listing"
        visible(lambda: verify_checks(public, published_id=identity, expected_ci=ci))
        phase = "recheck"
        recheck_release(public, classic)
        print(f"Verified neutral Sidekick HOLD advisory check {identity}.")
        return 0
    except (ValueError, OSError, http.client.HTTPException, subprocess.SubprocessError,
            KeyError, TypeError, AttributeError, RecursionError) as error:
        detail = str(error) if isinstance(error, Blocked) else "Unreadable input or GitHub response."
        if phase is not None:
            known = "" if identity is None else f" for check {identity}"
            message = (f"Check write unverified at {phase}{known}. "
                       "Reconcile in GitHub. Do not replay.")
        elif reconciling:
            message = f"Reconciliation failed. {detail}"
        else:
            message = f"Blocked before write. {detail}"
        print(message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
