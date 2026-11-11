#!/usr/bin/env python3
"""Five authored offline cases; not executed as part of this draft.

All GitHub, source extraction, lane and preflight dependencies are injected mocks.
No network, Git/OCR CLI, provider, target process or credential is used.
"""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import central_review_hub as hub


NOW = hub.utc("2030-01-02T12:00:00Z")
CUTOFF = "2030-01-02T00:00:00Z"
UPDATED = "2030-01-02T01:00:00Z"
BASE, HEAD, MERGE = "a" * 40, "b" * 40, "f" * 40
TARGET = hub.OWNER + "/sample-project"
DIFF = "--- a/src/sample.py\n+++ b/src/sample.py\n@@ -1 +1 @@\n-value = 1\n+value = 2\n"
SNAPSHOTS = {"src/sample.py": ["value = 1\n", "value = 2\n"]}
ENV = {"CENTRAL_REVIEW_ENABLED": "true", "CENTRAL_REVIEW_SINCE": CUTOFF}


def repository(name=TARGET, identity=1, **changes):
    return {"id": identity, "full_name": name,
            "owner": {"login": name.split("/")[0]}, "private": False,
            "fork": False, "archived": False, "disabled": False,
            "default_branch": "trunk", **changes}


def pull(number=1, head=HEAD, updated=UPDATED, **changes):
    return {"id": 1000 + number, "number": number, "state": "open",
            "draft": False, "updated_at": updated,
            "base": {"sha": BASE, "ref": "trunk", "repo": repository()},
            "head": {"sha": head, "ref": "feature", "repo": repository()},
            **changes}


def binding(base=BASE, head=HEAD):
    return {"base_tip_sha": base, "base_sha": MERGE, "head_sha": head,
            "diff_sha256": hashlib.sha256(DIFF.encode()).hexdigest()}


class MemoryGitHub:
    """Minimal REST shapes: arrays for pulls, counted objects for Checks/repos.

    Writes persist before returning; later GETs read that state, never the POST
    argument or a canned acknowledgment. Unrecognized routes fail immediately.
    """

    def __init__(self):
        self.repositories = [repository()]
        self.pulls = {TARGET: [pull()]}
        self.tips = {TARGET: BASE}
        self.checks = {}
        self.unread_writes = set()
        self.next_id = 100

    def page(self, rows, query, key=None):
        size = int(query["per_page"][0])
        start = (int(query["page"][0]) - 1) * size
        batch = deepcopy(rows[start:start + size])
        result = batch if key is None else {"total_count": len(rows), key: batch}
        return result, start + size < len(rows)

    def __call__(self, method, path, payload=None):
        parsed = urlsplit(path)
        query = parse_qs(parsed.query)
        if method == "GET" and parsed.path == "/installation/repositories":
            return self.page(self.repositories, query, "repositories")
        match = re.fullmatch(r"/repos/([^/]+/[^/]+)(/.*)?", parsed.path)
        if match is None:
            raise AssertionError("Unexpected fixture route: " + method + " " + path)
        repo, suffix = match.group(1), match.group(2) or ""
        if method == "GET" and suffix == "":
            return deepcopy(next(r for r in self.repositories if r["full_name"] == repo)), False
        if method == "GET" and suffix == "/commits/" + hub.ANCHOR and repo == hub.HUB:
            return {"sha": hub.ANCHOR}, False
        if method == "GET" and suffix == "/pulls":
            return self.page(self.pulls[repo], query)
        if method == "GET" and re.fullmatch(r"/pulls/[0-9]+", suffix):
            number = int(suffix.rsplit("/", 1)[1])
            return deepcopy(next(p for p in self.pulls[repo] if p["number"] == number)), False
        if method == "GET" and suffix == "/branches/trunk":
            return {"name": "trunk", "commit": {"sha": self.tips[repo]}}, False
        listing = re.fullmatch(r"/commits/([0-9a-f]{40})/check-runs", suffix)
        if method == "GET" and listing:
            assert query["filter"] == ["all"]
            rows = [row for (owner, _identity), row in self.checks.items()
                    if owner == repo and row["head_sha"] == listing.group(1)
                    and row["name"] == query["check_name"][0]]
            return self.page(rows, query, "check_runs")
        if method == "POST" and suffix == "/check-runs":
            identity = self.next_id
            self.next_id += 1
            row = {"id": identity, "started_at": hub.stamp(NOW),
                   "conclusion": None, **deepcopy(payload)}
            row["output"].update(text=None, annotations_count=0)
            self.checks[repo, identity] = row
            self.unread_writes.add((repo, identity))
            return deepcopy(row), False
        detail = re.fullmatch(r"/check-runs/([0-9]+)", suffix)
        if detail and method in ("GET", "PATCH"):
            key = repo, int(detail.group(1))
            if method == "PATCH":
                self.checks[key].update(deepcopy(payload))
                self.checks[key]["output"].update(text=None, annotations_count=0)
                self.unread_writes.add(key)
            else:
                self.unread_writes.discard(key)
            return deepcopy(self.checks[key]), False
        raise AssertionError("Unexpected fixture route: " + method + " " + path)


def report(row):
    return json.loads(row["output"]["summary"].split("```json\n", 1)[1].rsplit("\n```", 1)[0])


class Harness:
    def __init__(self, case):
        self.case = case
        self.memory = MemoryGitHub()
        self.api = Mock(side_effect=self.memory)
        self.sources = Mock(side_effect=self.source)
        self.lanes = Mock(side_effect=self.lane)
        self.preflight = Mock(return_value=Path("/offline/opencodereview"))

    @contextmanager
    def source(self, repository_name, base, head):
        self.case.assertEqual(repository_name, TARGET)
        yield binding(base, head), DIFF, deepcopy(SNAPSHOTS)

    def lane(self, lane, binary, diff, snapshots):
        self.case.assertEqual(binary, Path("/offline/opencodereview"))
        self.case.assertEqual(diff, DIFF)
        self.case.assertEqual(snapshots, SNAPSHOTS)
        self.case.assertFalse(self.memory.unread_writes)
        receipt = self.receipts()[-1]
        self.case.assertEqual(report(receipt)["lanes"][lane]["status"], "OUTCOME_UNKNOWN")
        self.case.assertTrue(self.ledger())
        return {"status": "completed", "reviewer_provider": "xiaomi",
                "reviewer_model": "mimo-v2.6-pro", "finding_count": 0, "gap_count": 0}

    def controller(self):
        config = json.loads((hub.ROOT / "config/central-review-hub.json").read_text())
        # Enable only this in-memory fixture; the checked-in draft stays disabled.
        config.update(enabled=True, paid_execution_authorized=True)
        return hub.Hub(config, api=self.api, sources=self.sources, lanes=self.lanes,
                       preflight=self.preflight, now=lambda: NOW)

    def ledger(self):
        return [row for (repo, _identity), row in self.memory.checks.items()
                if repo == hub.HUB and row["name"] == hub.LEDGER]

    def receipts(self):
        return [row for (repo, _identity), row in self.memory.checks.items()
                if repo == TARGET and row["name"] == hub.RECEIPT]


class CentralReviewHubCases(unittest.TestCase):
    def test_discovery_cutoff_default_branch_and_private_exclusion(self):
        h = Harness(self)
        h.memory.repositories = [
            repository(), repository(hub.HUB, 2),
            repository(hub.OWNER + "/private-project", 3, private=True),
            repository(hub.OWNER + "/fork-project", 4, fork=True),
            repository(hub.OWNER + "/archived-project", 5, archived=True),
        ]
        draft = pull(4, "4" * 40, draft=True)
        wrong_base = pull(5, "5" * 40)
        wrong_base["base"]["ref"] = "release"
        fork_head = pull(6, "6" * 40)
        fork_head["head"]["repo"] = repository("contributor/fork-project", 6, fork=True)
        h.memory.pulls[TARGET] = [
            pull(1, "1" * 40, updated=CUTOFF),
            pull(2, "2" * 40, updated="2030-01-01T23:59:59Z"),
            pull(3), draft, wrong_base, fork_head,
        ]
        result = h.controller().run(ENV)
        self.assertEqual(result, {"status": "COMPLETE", "reservations": 1,
                                  "completed": 1, "failed_or_unknown": 0})
        h.sources.assert_called_once_with(TARGET, BASE, HEAD)
        h.preflight.assert_called_once_with()
        self.assertEqual(h.lanes.call_count, 2)
        pull_lists = [c.args[1].split("?", 1)[0] for c in h.api.call_args_list
                      if c.args[0] == "GET" and "/pulls?" in c.args[1]]
        self.assertEqual(pull_lists, ["/repos/" + TARGET + "/pulls"])
        self.assertFalse(h.memory.unread_writes)

    def test_durable_daily_quota_counts_unknown_across_hub_source_runs(self):
        h = Harness(self)
        h.memory.pulls[TARGET] = [pull(1, "1" * 40), pull(2, "2" * 40),
                                 pull(3, "3" * 40), pull(4, "4" * 40),
                                 pull(5, "5" * 40), pull(6, "6" * 40),
                                 pull(7, "7" * 40)]

        def unknown(lane, binary, diff, snapshots):
            h.lane(lane, binary, diff, snapshots)
            return {"status": "FAILED_OR_UNKNOWN"}

        h.lanes.side_effect = unknown
        first, second, third, fourth = h.controller(), h.controller(), h.controller(), h.controller()
        with patch.dict(hub.os.environ, {"GITHUB_SHA": "1" * 40}):
            one = first.run(ENV)
        # An interrupted-looking Check still represents a consumed reservation.
        h.ledger()[0]["status"] = "in_progress"
        h.ledger()[0]["conclusion"] = None
        with patch.dict(hub.os.environ, {"GITHUB_SHA": "2" * 40}):
            two = second.run(ENV)
        with patch.dict(hub.os.environ, {"GITHUB_SHA": "3" * 40}):
            three = third.run(ENV)
        with patch.dict(hub.os.environ, {"GITHUB_SHA": "4" * 40}):
            four = fourth.run(ENV)
        self.assertEqual((one["reservations"], two["reservations"], three["reservations"],
                          four["reservations"]), (2, 2, 2, 0))
        self.assertEqual(len({first.run_id, second.run_id, third.run_id, fourth.run_id}), 4)
        self.assertEqual(len(h.ledger()), 6)
        self.assertNotIn("created_at", h.ledger()[0])
        self.assertEqual(h.ledger()[0]["started_at"], hub.stamp(NOW))
        self.assertEqual(h.sources.call_count, 6)
        self.assertEqual(h.lanes.call_count, 12)
        self.assertEqual(four["status"], "COMPLETE")
        self.assertEqual({json.loads(row["output"]["summary"])["state"]
                          for row in h.ledger()}, {"RESERVED_OUTCOME_UNKNOWN"})
        self.assertEqual({json.loads(row["output"]["summary"])["consumed"]
                          for row in h.ledger()}, {True})
        self.assertFalse(h.memory.unread_writes)

    def test_source_only_dedup_and_stale_binding(self):
        h = Harness(self)
        seen_head = "e" * 40
        h.memory.pulls[TARGET].append(pull(2, seen_head))
        # An existing target reservation suppresses work even without a hub row.
        seeded, _more = h.api("POST", "/repos/" + TARGET + "/check-runs", {
            "name": hub.RECEIPT, "head_sha": seen_head,
            "external_id": BASE + ":" + seen_head, "status": "in_progress",
            "output": {"title": "Existing reservation", "summary": "Unknown outcome"}})
        h.api("GET", "/repos/" + TARGET + "/check-runs/" + str(seeded["id"]))

        def moved_head(lane, binary, diff, snapshots):
            outcome = h.lane(lane, binary, diff, snapshots)
            if lane == "cloudflare":
                h.memory.pulls[TARGET][0]["head"]["sha"] = "d" * 40
            return outcome

        h.lanes.side_effect = moved_head
        first = h.controller().run(ENV)
        receipt = h.receipts()[-1]
        saved = report(receipt)
        self.assertEqual(first["status"], "BLOCKED_OR_UNKNOWN")
        self.assertEqual(receipt["head_sha"], HEAD)
        self.assertEqual(receipt["external_id"], BASE + ":" + HEAD)
        self.assertEqual(receipt["conclusion"], "failure")
        self.assertEqual(saved["status"], "STALE_OR_UNVERIFIABLE")
        self.assertEqual({key: saved[key] for key in binding()}, binding())
        self.assertEqual(saved["lanes"]["alibaba"]["head_sha"], HEAD)
        self.assertEqual(saved["lanes"]["cloudflare"]["diff_sha256"], binding()["diff_sha256"])
        self.assertFalse(saved["merge_authorized"])
        # Rediscovery of that same revision on a new hub source run cannot retry.
        h.memory.pulls[TARGET][0]["head"]["sha"] = HEAD
        with patch.dict(hub.os.environ, {"GITHUB_SHA": "9" * 40}):
            again = h.controller().run(ENV)
        self.assertEqual(again["reservations"], 0)
        h.sources.assert_called_once_with(TARGET, BASE, HEAD)
        self.assertEqual(h.lanes.call_count, 2)
        self.assertEqual(len(h.ledger()), 1)
        self.assertFalse(h.memory.unread_writes)

    def test_failed_lane_safe_reporting_and_no_retry(self):
        h = Harness(self)
        unsafe_error = "RAW_PROVIDER_BODY @someone <secret> ```"

        def failed_lane(lane, binary, diff, snapshots):
            outcome = h.lane(lane, binary, diff, snapshots)
            if lane == "alibaba":
                raise RuntimeError(unsafe_error)
            return outcome

        h.lanes.side_effect = failed_lane
        result = h.controller().run(ENV)
        receipt = h.receipts()[0]
        saved = report(receipt)
        self.assertEqual(result, {"status": "BLOCKED_OR_UNKNOWN", "reservations": 1,
                                  "completed": 0, "failed_or_unknown": 1})
        self.assertEqual(saved["status"], "INCOMPLETE")
        self.assertEqual(saved["lanes"]["alibaba"]["status"], "FAILED_OR_UNKNOWN")
        self.assertEqual(saved["lanes"]["cloudflare"]["status"], "completed")
        self.assertEqual(receipt["conclusion"], "failure")
        self.assertFalse(saved["merge_authorized"])
        self.assertFalse(saved["review_quality_accepted"])
        self.assertNotIn(unsafe_error, json.dumps(h.receipts()))
        self.assertNotIn(DIFF, receipt["output"]["summary"])
        self.assertEqual([c.args[0] for c in h.lanes.call_args_list], ["alibaba", "cloudflare"])
        again = h.controller().run(ENV)
        self.assertEqual(again["reservations"], 0)
        self.assertEqual(h.sources.call_count, 1)
        self.assertEqual(h.lanes.call_count, 2)
        self.assertEqual(len(h.ledger()), 1)
        self.assertFalse(h.memory.unread_writes)

    def test_unsupported_source_consumed_then_next_candidate_and_no_retry(self):
        h = Harness(self)
        next_head = "c" * 40
        h.memory.pulls[TARGET] = [pull(1), pull(2, next_head, updated="2030-01-02T02:00:00Z")]
        unsafe_error = "RAW_SOURCE_BODY @someone <secret> ```"

        @contextmanager
        def source(repository_name, base, head):
            self.assertEqual(repository_name, TARGET)
            self.assertFalse(h.memory.unread_writes)
            self.assertEqual(h.receipts()[-1]["head_sha"], head)
            self.assertEqual(report(h.receipts()[-1])["status"], "RESERVED_OUTCOME_UNKNOWN")
            if head == HEAD:
                self.assertEqual(len(h.ledger()), 1)
                self.assertTrue(json.loads(h.ledger()[0]["output"]["summary"])["consumed"])
                h.lanes.assert_not_called()
                raise hub.Blocked(unsafe_error)
            self.assertEqual(head, next_head)
            self.assertEqual(len(h.ledger()), 2)
            h.lanes.assert_not_called()
            yield binding(base, head), DIFF, deepcopy(SNAPSHOTS)

        h.sources.side_effect = source
        result = h.controller().run(ENV)
        first, second = h.receipts()
        failed = report(first)
        self.assertEqual(result, {"status": "BLOCKED_OR_UNKNOWN", "reservations": 2,
                                  "completed": 1, "failed_or_unknown": 1})
        self.assertEqual(first["head_sha"], HEAD)
        self.assertEqual(first["external_id"], BASE + ":" + HEAD)
        self.assertEqual(first["status"], "completed")
        self.assertEqual(first["conclusion"], "failure")
        self.assertEqual(failed["status"], "SOURCE_BLOCKED_OR_UNKNOWN")
        self.assertEqual(failed["lanes"], {})
        self.assertFalse(failed["merge_authorized"])
        self.assertFalse(failed["review_quality_accepted"])
        self.assertNotIn(unsafe_error, json.dumps(h.receipts()))
        self.assertEqual(second["head_sha"], next_head)
        self.assertEqual(report(second)["status"], "BOTH_RECORDED_NOT_ACCEPTED")
        self.assertEqual([c.args[0] for c in h.lanes.call_args_list], ["alibaba", "cloudflare"])
        self.assertEqual(len(h.ledger()), 2)
        self.assertTrue(json.loads(h.ledger()[0]["output"]["summary"])["consumed"])
        again = h.controller().run(ENV)
        self.assertEqual(again["reservations"], 0)
        self.assertEqual(h.sources.call_count, 2)
        self.assertEqual(h.lanes.call_count, 2)
        self.assertEqual(len(h.receipts()), 2)
        self.assertEqual(len(h.ledger()), 2)
        self.assertFalse(h.memory.unread_writes)


if __name__ == "__main__":
    unittest.main()
