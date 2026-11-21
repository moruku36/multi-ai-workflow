"""Exercise the workflow's Python entrypoint through a fake HTTPS connection."""

from contextlib import redirect_stderr, redirect_stdout
import http.client
import io
import json
import os
from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import mock_open, patch


SCRIPT = Path(__file__).resolve().parents[1] / "tools/sidekick_advisory_transport.py"
REPO = "/repos/moruku36/local-ai-sidekick"
BASE = "c9b1e3c68e9d897aee355361eaaffd038fe7e23e"
HEAD = "4b6cb7c0d1ebf224fa7c1d053c3fee9a4464c20c"
NAME = "central-hub-advisory-transport-v1"
EXTERNAL_ID = f"{NAME}:1369269341:26:{HEAD}"
SCOPE = "/installation/repositories?per_page=2"
COMMIT = f"{REPO}/commits/{HEAD}"
SUITES = f"{COMMIT}/check-suites?per_page=1"
RUNS = f"{COMMIT}/check-runs?filter=all&per_page=50&page="
PULL = f"{REPO}/pulls/26"
RULES = f"{REPO}/rules/branches/main?per_page=100"
BRANCH = f"{REPO}/branches/main"
WRITE = f"{REPO}/check-runs"


class Response:
    def __init__(self, status, body, link=""):
        self.status = status
        self.body = json.dumps(body).encode("utf-8")
        self.link = link

    def getheader(self, name, default):
        return self.link if name == "Link" and self.link else default

    def read(self, size):
        return self.body[:size]


class FakeGitHub:
    def __init__(self):
        repo = {"id": 1369269341, "full_name": "moruku36/local-ai-sidekick",
                "default_branch": "main", "private": False, "visibility": "public"}
        self.reads = {
            SCOPE: (200, {"total_count": 1, "repositories": [repo]}),
            SUITES: (200, {"total_count": 1, "check_suites": [{"id": 2}]}),
            PULL: (200, {"number": 26, "state": "open", "draft": False,
                         "base": {"ref": "main", "sha": BASE, "repo": dict(repo)},
                         "head": {"ref": "candidate", "sha": HEAD, "repo": dict(repo)}}),
            RULES: (200, []),
            BRANCH: (200, {"name": "main", "commit": {"sha": BASE}, "protected": False,
                           "protection": {"enabled": False, "required_status_checks":
                                          {"enforcement_level": "off", "contexts": []}}}),
        }
        self.calls = []
        self.rows = []
        self.saved = None
        self.lose_write_response = False
        self.readback_app = 5715914

    def request(self, method, path, body, headers):
        self.calls.append((method, path))
        self.method, self.path, self.body = method, path, body
        assert headers.get("Authorization") == (None if path in (BRANCH, RULES) else "Bearer ghs_fake")

    def getresponse(self):
        if (self.method, self.path) == ("POST", WRITE):
            self.saved = {"id": 73, **json.loads(self.body), "app": {"id": 5715914}}
            if self.lose_write_response:
                raise http.client.RemoteDisconnected()
            return Response(201, self.saved)
        assert self.method == "GET"
        if self.path == WRITE + "/73":
            return Response(200, {**self.saved, "app": {"id": self.readback_app}})
        if self.path.startswith(RUNS):
            rows = self.rows + ([self.saved] if self.saved else [])
            page = int(self.path.removeprefix(RUNS))
            link = f'<https://api.github.com{RUNS}{page + 1}>; rel="next"' if len(rows) > page * 50 else ""
            return Response(200, {"total_count": len(rows), "check_runs": rows[(page - 1) * 50:page * 50]}, link)
        return Response(*self.reads[self.path])

    def close(self):
        pass


class AdvisoryTransport(unittest.TestCase):
    def invoke(self, fake, args=(), env=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        before = len(fake.calls)
        with (patch.dict(os.environ, {"SIDEKICK_APP_TOKEN": "ghs_fake", **(env or {})}, clear=True),
              patch.object(sys, "argv", [str(SCRIPT), *args]),
              patch("http.client.HTTPSConnection", return_value=fake) as connect,
              redirect_stdout(stdout), redirect_stderr(stderr), self.assertRaises(SystemExit) as exited):
            runpy.run_path(str(SCRIPT), run_name="__main__")
        for call in connect.call_args_list:
            self.assertEqual(call.args, ("api.github.com",))
        self.assertEqual(connect.call_count, len(fake.calls) - before)
        return exited.exception.code, stdout.getvalue() + stderr.getvalue()

    def assert_no_write(self, fake):
        code, output = self.invoke(fake)
        self.assertEqual(code, 1)
        self.assertIn("Blocked before write", output)
        self.assertNotIn(("POST", WRITE), fake.calls)
        self.assertNotIn("private diagnostic", output)

    def test_authorize_requires_exact_confirmation_ref_and_app(self):
        text = "WRITE ONE NEUTRAL SIDEKICK PR 26 ADVISORY CHECK"
        for confirmation, ref, app, expected in (
            (text, "refs/heads/main", "5715914", 0),
            (text.lower(), "refs/heads/main", "5715914", 1),
            (text + " ", "refs/heads/main", "5715914", 1),
            (text, "refs/heads/MAIN", "5715914", 1),
            (text, "refs/heads/main", "1", 1),
        ):
            with self.subTest(confirmation=confirmation, ref=ref, app=app):
                fake = FakeGitHub()
                event = {"inputs": {"confirmation": confirmation}, "repository": {"default_branch": "main"}}
                env = {"GITHUB_EVENT_PATH": "/fake-event", "GITHUB_REF": ref, "CONFIGURED_APP_ID": app}
                with patch("builtins.open", mock_open(read_data=json.dumps(event))):
                    code, output = self.invoke(fake, ("authorize",), env)
                self.assertEqual(code, expected)
                self.assertEqual(fake.calls, [])
                self.assertNotIn(confirmation, output)

    def test_neutral_post_readback_and_dedup_across_invocations(self):
        fake = FakeGitHub()
        code, output = self.invoke(fake)
        self.assertEqual(code, 0)
        self.assertIn("Verified neutral Sidekick advisory check 73", output)
        self.assertEqual(fake.calls[-2:], [("POST", WRITE), ("GET", WRITE + "/73")])
        self.assertEqual({key: fake.saved[key] for key in
                          ("name", "head_sha", "external_id", "status", "conclusion")},
                         {"name": NAME, "head_sha": HEAD, "external_id": EXTERNAL_ID,
                          "status": "completed", "conclusion": "neutral"})
        self.assertIn("No review was performed", fake.saved["output"]["summary"])
        self.assertEqual(self.invoke(fake)[0], 1)
        self.assertEqual(fake.calls.count(("POST", WRITE)), 1)

    def test_external_id_under_another_context_on_later_page(self):
        fake = FakeGitHub()
        fake.rows = [{"id": i, "name": "unrelated", "head_sha": HEAD, "external_id": None}
                     for i in range(1, 52)]
        fake.rows[-1]["external_id"] = EXTERNAL_ID
        self.assert_no_write(fake)
        self.assertIn(("GET", RUNS + "2"), fake.calls)

    def test_scope_tuple_and_protection_fail_closed(self):
        for failure in ("scope", "fork", "head", "tip", "unreadable", "classic", "ruleset"):
            with self.subTest(failure=failure):
                fake = FakeGitHub()
                pull, branch = fake.reads[PULL][1], fake.reads[BRANCH][1]
                if failure == "scope":
                    fake.reads[SCOPE][1]["total_count"] = 2
                elif failure == "fork":
                    pull["head"]["repo"]["id"] = 1
                elif failure == "head":
                    pull["head"]["sha"] = "1" * 40
                elif failure == "tip":
                    branch["commit"]["sha"] = "1" * 40
                elif failure == "unreadable":
                    fake.reads[RULES] = (403, {"message": "private diagnostic"})
                elif failure == "classic":
                    branch["protected"] = branch["protection"]["enabled"] = True
                    branch["protection"]["required_status_checks"]["contexts"] = [NAME.upper()]
                else:
                    fake.reads[RULES] = (200, [{"type": "required_status_checks", "parameters": {
                        "required_status_checks": [{"context": NAME, "integration_id": 5715914}]}}])
                self.assert_no_write(fake)

    def test_ambiguous_post_or_mismatched_readback_has_no_retry(self):
        for lost in (True, False):
            with self.subTest(lost=lost):
                fake = FakeGitHub()
                fake.lose_write_response = lost
                fake.readback_app = 1
                code, output = self.invoke(fake)
                self.assertEqual(code, 1)
                self.assertIn("Reconcile in GitHub. Do not replay.", output)
                self.assertEqual(fake.calls.count(("POST", WRITE)), 1)
                self.assertNotIn("ghs_fake", output)


if __name__ == "__main__":
    unittest.main()
