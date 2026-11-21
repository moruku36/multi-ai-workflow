#!/usr/bin/env python3
"""Record one neutral transport witness for the frozen public Sidekick PR."""

import http.client
import json
import os
import re
import sys

TARGET = "moruku36/local-ai-sidekick"
TARGET_ID = 1369269341
PR = 26
BASE = "c9b1e3c68e9d897aee355361eaaffd038fe7e23e"
HEAD = "4b6cb7c0d1ebf224fa7c1d053c3fee9a4464c20c"
APP_ID = 5715914
NAME = "central-hub-advisory-transport-v1"
EXTERNAL_ID = f"{NAME}:{TARGET_ID}:{PR}:{HEAD}"
CONFIRMATION = "WRITE ONE NEUTRAL SIDEKICK PR 26 ADVISORY CHECK"
REPO = f"/repos/{TARGET}"
MAX_RESPONSE = 4 * 1024 * 1024
PAGE_SIZE = 50
MAX_PAGES = 10


class Blocked(ValueError):
    """A fixed diagnostic safe for the workflow log."""


def require(condition, message):
    if not condition:
        raise Blocked(message)


def authorize():
    # Read the dispatch input from the event file so it never enters step logs.
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as event_file:
        event = json.load(event_file)
    require(os.environ.get("GITHUB_REF") == "refs/heads/main"
            and event["repository"]["default_branch"] == "main", "Expected Hub default main ref.")
    require(event["inputs"]["confirmation"] == CONFIRMATION, "Confirmation mismatch.")
    require(os.environ.get("CONFIGURED_APP_ID") == str(APP_ID), "Configured App ID mismatch.")


class GitHub:
    def __init__(self, token):
        require(re.fullmatch(r"[A-Za-z0-9_\-.]+", token), "Installation token unavailable.")
        self.token = token

    def request(self, path, *, public=False, payload=None):
        # A fixed HTTPS host without redirects, proxies or retry. Public branch
        # and rules reads need no additional installation permission.
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": NAME,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if not public:
            headers["Authorization"] = "Bearer " + self.token
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode("utf-8")
        connection = http.client.HTTPSConnection("api.github.com", timeout=10)
        try:
            connection.request("GET" if body is None else "POST", path, body, headers)
            response = connection.getresponse()
            require(response.status == (200 if body is None else 201),
                    f"GitHub returned HTTP {response.status} for {path}.")
            link = response.getheader("Link", "")
            require(not link or all(re.fullmatch(r'<[^<>]+>; rel="(?:next|prev|first|last)"',
                                                 part.strip()) for part in link.split(",")),
                    "Unreadable GitHub pagination.")
            raw = response.read(MAX_RESPONSE + 1)
            require(len(raw) <= MAX_RESPONSE, "GitHub response exceeds its read limit.")
            return json.loads(raw), 'rel="next"' in link
        finally:
            connection.close()

    def one(self, path, **kwargs):
        result, more = self.request(path, **kwargs)
        require(not more, "Incomplete GitHub response.")
        return result


def is_target(repo):
    return repo["id"] == TARGET_ID and repo["full_name"] == TARGET


def verify_scope(api):
    scope = api.one("/installation/repositories?per_page=2")
    repos = scope["repositories"]
    require(scope["total_count"] == 1 and isinstance(repos, list) and len(repos) == 1,
            "Installation token scope differs from the one allowed repository.")
    repo = repos[0]
    require(is_target(repo) and repo["private"] is False and repo["visibility"] == "public"
            and repo["default_branch"] == "main", "Sidekick repository identity or state drifted.")


def verify_absent(api):
    commit = f"{REPO}/commits/{HEAD}"
    suites, more = api.request(f"{commit}/check-suites?per_page=1")
    # The check-runs endpoint can omit runs beyond the most recent 1,000 suites.
    suite_count = suites["total_count"]
    require(type(suite_count) is int and 0 <= suite_count < 1000
            and isinstance(suites["check_suites"], list)
            and len(suites["check_suites"]) == min(suite_count, 1) and more == (suite_count > 1),
            "Cannot establish a complete check-run scan for this head.")

    seen = set()
    expected = None
    for page in range(1, MAX_PAGES + 1):
        listing, more = api.request(
            f"{commit}/check-runs?filter=all&per_page={PAGE_SIZE}&page={page}")
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
            require(name.casefold() != NAME and external_id != EXTERNAL_ID,
                    "An advisory context or transport ID already exists on this head.")
            seen.add(identity)
        require(more == (len(seen) < count), "Incomplete check-run pagination.")
        if not more:
            return
    raise Blocked("Check-run scan exceeded its page limit.")


def verify_pull(api):
    pull = api.one(f"{REPO}/pulls/{PR}")
    require(pull["number"] == PR and pull["state"] == "open" and pull["draft"] is False,
            "Sidekick PR is no longer the allowed open non-draft PR.")
    base, head = pull["base"], pull["head"]
    require(is_target(base["repo"]) and is_target(head["repo"])
            and base["repo"]["default_branch"] == "main" and base["ref"] == "main"
            and base["sha"] == BASE and head["sha"] == HEAD, "Sidekick PR tuple drifted.")


def verify_protection(api):
    rules = api.one(f"{REPO}/rules/branches/main?per_page=100", public=True)
    require(isinstance(rules, list) and len(rules) < 100, "Unreadable or incomplete branch rules.")
    contexts = []
    for rule in rules:
        require(isinstance(rule["type"], str) and rule["type"], "Unreadable branch rule type.")
        if rule["type"] == "required_status_checks":
            checks = rule["parameters"]["required_status_checks"]
            require(isinstance(checks, list), "Unreadable ruleset status checks.")
            contexts.extend(check["context"] for check in checks)

    branch = api.one(f"{REPO}/branches/main", public=True)
    require(branch["name"] == "main" and branch["commit"]["sha"] == BASE,
            "Sidekick main tip drifted.")
    protection = branch["protection"]
    protected, classic_enabled = branch["protected"], protection["enabled"]
    require(type(protected) is bool and type(classic_enabled) is bool
            and (not protected or classic_enabled or rules) and (not classic_enabled or protected),
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


def write_and_read_back(api):
    payload = {
        "name": NAME,
        "head_sha": HEAD,
        "external_id": EXTERNAL_ID,
        "status": "completed",
        "conclusion": "neutral",
        "output": {
            "title": "Sidekick advisory transport witness",
            "summary": ("Provider-free transport witness only. No review was performed. "
                        "No acceptance or merge authority."),
        },
    }
    created = api.one(f"{REPO}/check-runs", payload=payload)
    identity = created["id"]
    require(type(identity) is int and identity > 0, "Missing created check ID.")
    saved = api.one(f"{REPO}/check-runs/{identity}")
    require(saved["id"] == identity and saved["app"]["id"] == APP_ID
            and all(saved[field] == payload[field] for field in
                    ("head_sha", "name", "external_id", "status", "conclusion")),
            "Check readback did not match the witness.")
    print(f"Verified neutral Sidekick advisory check {identity}.")


def main(args):
    writing = False
    try:
        if args == ["authorize"]:
            authorize()
            return 0
        require(not args, "Unknown transport command.")
        api = GitHub(os.environ.get("SIDEKICK_APP_TOKEN", ""))
        verify_scope(api)
        verify_absent(api)
        verify_pull(api)
        verify_protection(api)
        writing = True
        print("Submitting the single advisory check.", flush=True)
        write_and_read_back(api)
        return 0
    except (ValueError, OSError, http.client.HTTPException, KeyError, TypeError, AttributeError) as error:
        if writing:
            message = "Check write or readback unverified. Reconcile in GitHub. Do not replay."
        else:
            detail = str(error) if isinstance(error, Blocked) else "Unreadable input or GitHub response."
            message = f"Blocked before write. {detail}"
        print(message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
