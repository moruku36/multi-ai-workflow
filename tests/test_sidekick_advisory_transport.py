"""Exercise the HOLD transport with local event and HTTPS fixtures."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import hashlib
import http.client
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import unittest
from unittest.mock import mock_open, patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/sidekick_advisory_transport.py"
SPEC = importlib.util.spec_from_file_location("sidekick_advisory_transport", SCRIPT)
transport = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(transport)

HUB = "/repos/moruku36/multi-ai-workflow"
HUB_MAIN = "f13e899ffd3270776a7f3b248c115f42b1566d4e"
RELEASE = "a" * 40
TAG_REF = "refs/tags/sidekick-hold-26-20261121"
TAG = f"{HUB}/git/ref/tags/sidekick-hold-26-20261121"
HUB_BRANCH = f"{HUB}/branches/main"
HUB_COMMIT = f"{HUB}/git/commits/{RELEASE}"
REPO = "/repos/moruku36/local-ai-sidekick"
BASE = "c9b1e3c68e9d897aee355361eaaffd038fe7e23e"
HEAD = "4b6cb7c0d1ebf224fa7c1d053c3fee9a4464c20c"
CANDIDATE = "2ed45d1726402efc722ac5bd03917cc00d4d91db"
MERGE = f"{REPO}/git/commits/{CANDIDATE}"
NAME = "central-hub-advisory-transport-v1"
EXTERNAL_ID = f"{NAME}:1369269341:26:{HEAD}"
APP = {"id": 5715914, "slug": "moruku36-central-source-review"}
SCOPE = "/installation/repositories?per_page=2"
COMMIT = f"{REPO}/commits/{HEAD}"
SUITES = f"{COMMIT}/check-suites?per_page=1"
RUNS = f"{COMMIT}/check-runs?filter=all&per_page=50&page="
PULL = f"{REPO}/pulls/26"
RULES = f"{REPO}/rules/branches/main?per_page=100"
BRANCH = f"{REPO}/branches/main"
WRITE = f"{REPO}/check-runs"
READBACK = f"{WRITE}/73"
FIXTURE_RULES_HASH = hashlib.sha256(
    b'[{"parameters":{"required_status_checks":[{"context":"ci-gate","integration_id":15368}]},'
    b'"type":"required_status_checks"}]'
).hexdigest()
CLASSIC_HASH = hashlib.sha256(
    b'{"enabled":false,"required_status_checks":{"contexts":[],"enforcement_level":"off"}}'
).hexdigest()


class Response:
    def __init__(self, status, body, link=""):
        self.status = status
        self.body = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        self.link = link

    def getheader(self, name, default):
        return self.link if name == "Link" and self.link else default

    def read(self, size):
        return self.body[:size]


def public_repo(path, identity):
    return {"id": identity, "full_name": path.removeprefix("/repos/"),
            "owner": {"id": 12478466}, "default_branch": "main",
            "private": False, "visibility": "public"}


class FakeGitHub:
    def __init__(self):
        hub = public_repo(HUB, 1365934149)
        repo = public_repo(REPO, 1369269341)
        self.event = {"repository": deepcopy(hub), "ref": TAG_REF, "before": "0" * 40,
                      "after": RELEASE, "created": True, "deleted": False, "forced": False}
        self.checkout = RELEASE
        self.reads = {
            HUB: (200, hub),
            HUB_BRANCH: (200, {"name": "main", "commit": {"sha": HUB_MAIN}}),
            TAG: (200, {"ref": TAG_REF, "object": {"type": "commit", "sha": RELEASE}}),
            HUB_COMMIT: (200, {"sha": RELEASE, "parents": [{"sha": HUB_MAIN}]}),
            REPO: (200, repo),
            SCOPE: (200, {"total_count": 1, "repositories": [deepcopy(repo)]}),
            SUITES: (200, {"total_count": 1, "check_suites": [{"id": 2}]}),
            PULL: (200, {"id": 5372674586, "number": 26, "state": "open", "draft": False,
                         "user": {"id": 12478466}, "merge_commit_sha": CANDIDATE,
                         "base": {"ref": "main", "sha": BASE, "repo": deepcopy(repo)},
                         "head": {"sha": HEAD, "repo": deepcopy(repo)}}),
            MERGE: (200, {"sha": CANDIDATE, "parents": [{"sha": BASE}, {"sha": HEAD}],
                          "tree": {"sha": "de48270e5e3342ab683cbb6e3b0d160f99b640e0"}}),
            RULES: (200, [{"type": "required_status_checks", "parameters": {
                "required_status_checks": [{"integration_id": 15368, "context": "ci-gate"}]}}]),
            BRANCH: (200, {"name": "main", "commit": {"sha": BASE}, "protected": True,
                           "protection": {"enabled": False, "required_status_checks":
                                          {"enforcement_level": "off", "contexts": []}}}),
        }
        self.calls = []
        self.authorizations = []
        self.rows = [{"id": 135080128831, "name": "ci-gate", "head_sha": HEAD,
                      "external_id": None, "app": {"id": 15368},
                      "status": "completed", "conclusion": "success"}]
        self.saved = None
        self.show_saved = True
        self.post_response = None
        self.readback = None
        self.after_write = None

    def data(self, path):
        return self.reads[path][1]

    def request(self, method, path, body, headers):
        self.calls.append((method, path))
        self.authorizations.append(headers.get("Authorization"))
        self.method, self.path, self.body = method, path, body

    def getresponse(self):
        if (self.method, self.path) == ("POST", WRITE):
            self.saved = {"id": 73, **json.loads(self.body), "app": dict(APP)}
            if self.after_write:
                self.after_write(self)
            if self.post_response is None:
                return Response(201, {"id": 73})
            if isinstance(self.post_response, Exception):
                raise self.post_response
            return Response(*self.post_response)
        assert self.method == "GET"
        if self.path == READBACK:
            return Response(200, self.saved if self.readback is None else self.readback)
        if self.path.startswith(RUNS) and self.path not in self.reads:
            rows = self.rows + ([self.saved] if self.saved and self.show_saved else [])
            page = int(self.path.removeprefix(RUNS))
            link = f'<https://api.github.com{RUNS}{page + 1}>; rel="next"' if len(rows) > page * 50 else ""
            page_rows = rows[(page - 1) * 50:page * 50]
            return Response(200, {"total_count": len(rows), "check_runs": page_rows}, link)
        return Response(*self.reads[self.path])

    def close(self):
        pass


class AdvisoryTransport(unittest.TestCase):
    def invoke(self, fake, args=(), env=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        before = len(fake.calls)
        run_env = {
            "GITHUB_EVENT_NAME": "push", "GITHUB_EVENT_PATH": "/fake-event",
            "GITHUB_OUTPUT": "/fake-output", "GITHUB_REF": TAG_REF, "GITHUB_SHA": RELEASE,
            "GITHUB_REPOSITORY": "moruku36/multi-ai-workflow", "GITHUB_REPOSITORY_ID": "1365934149",
            "GITHUB_ACTOR_ID": "12478466", "GITHUB_RUN_ATTEMPT": "1", "CONFIGURED_APP_ID": "5715914",
        }
        if not args:
            run_env.update(SIDEKICK_APP_TOKEN="ghs_fake", SIDEKICK_INSTALLATION_ID="180960402",
                           SIDEKICK_APP_SLUG=APP["slug"], CLASSIC_PROTECTION_SHA256=CLASSIC_HASH)
        opened = mock_open(read_data=json.dumps(fake.event))
        with (patch.dict(os.environ, {**run_env, **(env or {})}, clear=True),
              patch.object(transport, "RULES_SHA256", FIXTURE_RULES_HASH),
              patch("builtins.open", opened),
              patch("subprocess.check_output", return_value=fake.checkout + "\n") as checkout,
              patch("http.client.HTTPSConnection", return_value=fake) as connect,
              redirect_stdout(stdout), redirect_stderr(stderr)):
            code = transport.main(list(args))
        self.assertEqual(connect.call_count, len(fake.calls) - before)
        for call in connect.call_args_list:
            self.assertEqual(call.args, ("api.github.com",))
        for call in checkout.call_args_list:
            self.assertEqual(call.args[0], ["/usr/bin/git", "rev-parse", "--verify", "HEAD"])
            self.assertEqual(call.kwargs["env"], {})
        for (_, path), authorization in zip(fake.calls[before:], fake.authorizations[before:]):
            uses_token = not args and (path in (SCOPE, SUITES, WRITE, READBACK) or path.startswith(RUNS))
            self.assertEqual(authorization, "Bearer ghs_fake" if uses_token else None)
        preflight_output = "".join(call.args[0] for call in opened.return_value.write.call_args_list)
        return code, stdout.getvalue() + stderr.getvalue(), preflight_output

    def assert_no_write(self, fake, args=(), env=None):
        code, output, preflight = self.invoke(fake, args, env)
        self.assertEqual(code, 1)
        self.assertIn("Blocked before write", output)
        self.assertNotIn(("POST", WRITE), fake.calls)
        self.assertNotIn("private diagnostic", output)
        self.assertEqual(preflight, "")

    def assert_unverified_write(self, fake):
        code, output, _ = self.invoke(fake)
        self.assertEqual(code, 1)
        self.assertIn("Reconcile in GitHub. Do not replay.", output)
        self.assertNotIn("Verified neutral", output)
        self.assertNotIn("ghs_fake", output)
        self.assertNotIn("private diagnostic", output)
        self.assertEqual(fake.calls.count(("POST", WRITE)), 1)

    def test_preflight_neutral_post_independent_readback_and_rescan(self):
        fake = FakeGitHub()
        code, _, preflight = self.invoke(fake, ("preflight",))
        self.assertEqual(code, 0)
        self.assertEqual(preflight, f"classic-protection-sha256={CLASSIC_HASH}\n")
        self.assertNotIn(("GET", SCOPE), fake.calls)
        self.assertTrue(all(method == "GET" for method, _ in fake.calls))

        code, output, _ = self.invoke(fake, env={"CLASSIC_PROTECTION_SHA256": preflight.split("=")[1].strip()})
        self.assertEqual(code, 0)
        self.assertIn("Verified neutral Sidekick HOLD advisory check 73", output)
        post = fake.calls.index(("POST", WRITE))
        self.assertEqual(fake.calls[post + 1], ("GET", READBACK))
        for path in (TAG, PULL, MERGE, RULES, BRANCH, SUITES, RUNS + "1"):
            self.assertIn(("GET", path), fake.calls[post + 2:])
            self.assertEqual(fake.calls.count(("GET", path)), 3)
        self.assertEqual(fake.saved, {
            "id": 73, "name": NAME, "head_sha": HEAD, "external_id": EXTERNAL_ID,
            "status": "completed", "conclusion": "neutral", "app": APP,
            "output": {"title": "HOLD — Sidekick transport advisory",
                       "summary": ("HOLD. Advisory transport only. This is neither a provider review nor an "
                                   "accepted review. This check grants no merge authority.")},
        })
        self.assertEqual(self.invoke(fake)[0], 1)
        self.assertEqual(fake.calls.count(("POST", WRITE)), 1)

    def test_wrong_run_identity_and_configured_app_stop_preflight(self):
        for key, value in (
            ("GITHUB_EVENT_NAME", "workflow_dispatch"), ("GITHUB_REF", TAG_REF.upper()),
            ("GITHUB_ACTOR_ID", "1"), ("GITHUB_REPOSITORY_ID", "1"), ("GITHUB_REPOSITORY", "wrong"),
            ("GITHUB_RUN_ATTEMPT", "2"), ("GITHUB_SHA", "abc"), ("GITHUB_SHA", HUB_MAIN),
            ("CONFIGURED_APP_ID", "1"),
        ):
            with self.subTest(key=key, value=value):
                fake = FakeGitHub()
                self.assert_no_write(fake, ("preflight",), {key: value})
                self.assertEqual(fake.calls, [])

    def test_wrong_push_event_or_checkout_stops_preflight(self):
        for key, value in (("ref", "refs/heads/main"), ("created", False), ("deleted", True),
                           ("forced", True), ("before", HUB_MAIN), ("after", HUB_MAIN)):
            with self.subTest(key=key):
                fake = FakeGitHub()
                fake.event[key] = value
                self.assert_no_write(fake, ("preflight",))
                self.assertEqual(fake.calls, [])
        fake = FakeGitHub()
        fake.checkout = HUB_MAIN
        self.assert_no_write(fake, ("preflight",))
        self.assertEqual(fake.calls, [])

    def test_wrong_action_outputs_stop_before_using_token(self):
        for key, value in (("SIDEKICK_INSTALLATION_ID", "1"), ("SIDEKICK_APP_SLUG", "other-app")):
            with self.subTest(key=key):
                fake = FakeGitHub()
                self.assert_no_write(fake, env={key: value})
                self.assertEqual(fake.calls, [])

    def test_actual_installation_membership_and_403_fail_closed(self):
        for field, value in (("id", 1), ("owner", {"id": 1}), ("full_name", "wrong"),
                             ("default_branch", "wrong"), ("private", True), ("visibility", "private")):
            with self.subTest(field=field):
                fake = FakeGitHub()
                fake.data(SCOPE)["repositories"][0][field] = value
                self.assert_no_write(fake)
        for response in ((403, {"message": "private diagnostic"}),
                         (200, {"total_count": 2, "repositories": []}),
                         (200, {"total_count": 1, "repositories": [public_repo(REPO, 1369269341)]},
                          '<https://api.github.com/installation/repositories?page=2>; rel="next"')):
            with self.subTest(status=response[0]):
                fake = FakeGitHub()
                fake.reads[SCOPE] = response
                self.assert_no_write(fake)
                self.assertEqual(fake.calls, [("GET", SCOPE)])

    def test_source_and_target_drift_block_both_phases(self):
        for path, fields, value in (
            (HUB, ("owner", "id"), 1),
            (HUB_BRANCH, ("commit", "sha"), "1" * 40),
            (TAG, ("object", "type"), "tag"),
            (TAG, ("object", "sha"), HUB_MAIN),
            (HUB_COMMIT, ("parents",), [{"sha": HUB_MAIN}, {"sha": HEAD}]),
            (REPO, ("visibility",), "private"),
            (PULL, ("id",), 1),
            (PULL, ("user", "id"), 1),
            (PULL, ("head", "repo", "id"), 1),
            (PULL, ("base", "sha"), RELEASE),
            (PULL, ("head", "sha"), RELEASE),
            (PULL, ("merge_commit_sha",), RELEASE),
            (MERGE, ("parents",), [{"sha": HEAD}, {"sha": BASE}]),
            (MERGE, ("tree", "sha"), RELEASE),
            (BRANCH, ("commit", "sha"), RELEASE),
            (BRANCH, ("protected",), False),
        ):
            for args in (("preflight",), ()):
                with self.subTest(path=path, fields=fields, args=args):
                    fake = FakeGitHub()
                    field = fake.data(path)
                    for key in fields[:-1]:
                        field = field[key]
                    field[fields[-1]] = value
                    self.assert_no_write(fake, args)

    def test_rules_and_classic_protection_fail_closed(self):
        digest = "2e77fbec4f2baf8cfda413b92565974b0ac72247806e4b57e12d4c9d8e8019d2"
        self.assertEqual(transport.RULES_SHA256, digest)
        for response in ((200, []), (403, {"message": "private diagnostic"})):
            fake = FakeGitHub()
            fake.reads[RULES] = response
            self.assert_no_write(fake, ("preflight",))
            self.assert_no_write(fake)
        for required_context in ("different-required-context", NAME.upper()):
            fake = FakeGitHub()
            status = fake.data(BRANCH)["protection"]["required_status_checks"]
            status["contexts"] = [required_context]
            self.assert_no_write(fake)
        self.assert_no_write(FakeGitHub(), env={"CLASSIC_PROTECTION_SHA256": ""})

    def test_wrong_genuine_ci_identity_or_result_blocks(self):
        for field, value in (("id", 1), ("name", "other"), ("app", {"id": 1}),
                             ("head_sha", RELEASE), ("status", "in_progress"), ("conclusion", "neutral")):
            with self.subTest(field=field):
                fake = FakeGitHub()
                fake.rows[0][field] = value
                self.assert_no_write(fake, ("preflight",))
                self.assert_no_write(fake)

    def test_external_id_or_case_folded_name_on_later_page_blocks(self):
        for duplicate in ({"external_id": EXTERNAL_ID}, {"name": NAME.upper()}):
            with self.subTest(duplicate=duplicate):
                fake = FakeGitHub()
                fake.rows.extend({"id": i, "name": "unrelated", "head_sha": HEAD, "external_id": None}
                                 for i in range(1, 52))
                fake.rows[-1].update(duplicate)
                self.assert_no_write(fake)
                self.assertIn(("GET", RUNS + "2"), fake.calls)

    def test_capped_suites_and_inconsistent_pagination_block(self):
        fake = FakeGitHub()
        fake.data(SUITES)["total_count"] = 1000
        self.assert_no_write(fake)
        fake = FakeGitHub()
        fake.rows.extend({"id": i, "name": "unrelated", "head_sha": HEAD, "external_id": None}
                         for i in range(1, 52))
        fake.reads[RUNS + "2"] = (200, {"total_count": 51, "check_runs": [fake.rows[0]]})
        self.assert_no_write(fake)
        self.assertIn(("GET", RUNS + "2"), fake.calls)

    def test_ambiguous_post_has_no_retry_or_readback(self):
        for response in (http.client.RemoteDisconnected(), (201, b'{"id":73,"id":73}'),
                         (201, [{"id": 73}]), (201, {"id": True}), (503, {"message": "private diagnostic"}),
                         (201, {"id": 73}, '<https://api.github.com/>; rel="prev"')):
            with self.subTest(response=response):
                fake = FakeGitHub()
                fake.post_response = response
                self.assert_unverified_write(fake)
                self.assertEqual(fake.calls[-1], ("POST", WRITE))

    def test_wrong_result_readback_stops_without_retry(self):
        for fields, value in (
            (("id",), 74), (("app", "id"), 1), (("app", "slug"), "other-app"),
            (("head_sha",), RELEASE), (("name",), NAME.upper()), (("external_id",), "wrong"),
            (("status",), "queued"), (("conclusion",), "success"),
            (("output", "title"), "wrong"), (("output", "summary"), "private diagnostic"),
        ):
            with self.subTest(fields=fields):
                fake = FakeGitHub()

                def wrong_readback(github):
                    github.readback = deepcopy(github.saved)
                    parent = github.readback if len(fields) == 1 else github.readback[fields[0]]
                    parent[fields[-1]] = value

                fake.after_write = wrong_readback
                self.assert_unverified_write(fake)
                self.assertEqual(fake.calls[-1], ("GET", READBACK))

    def test_post_scan_and_exact_tuple_rechecks_fail_without_retry(self):
        for change in (
            lambda fake: setattr(fake, "show_saved", False),
            lambda fake: fake.rows.append({**fake.saved, "id": 74}),
            lambda fake: fake.rows[0].update(conclusion="failure"),
            lambda fake: fake.rows[0].update(external_id="changed"),
            lambda fake: fake.data(TAG)["object"].update(sha=HUB_MAIN),
            lambda fake: fake.data(PULL).update(merge_commit_sha=RELEASE),
            lambda fake: fake.data(RULES).clear(),
            lambda fake: fake.data(BRANCH)["protection"].update(enabled=True),
        ):
            with self.subTest(change=change):
                fake = FakeGitHub()
                fake.after_write = change
                self.assert_unverified_write(fake)


class WorkflowSource(unittest.TestCase):
    def setUp(self):
        self.workflow = (ROOT / ".github/workflows/central-review-hub.yml").read_text(encoding="utf-8")

    def test_tag_is_the_only_launcher_and_first_creation_is_required(self):
        trigger = re.search(r"^on:\n((?:(?: +[^\n]*)?\n)+)", self.workflow, re.MULTILINE)
        self.assertEqual(trigger[1].rstrip(), "  push:\n    tags: [sidekick-hold-26-20261121]")
        condition = re.search(r"^    if: >-\n((?:      [^\n]+\n)+)", self.workflow, re.MULTILINE)
        guards = [line.strip() for line in condition[1].splitlines()]
        self.assertEqual(guards[-1], "github.run_attempt == '1'")
        self.assertTrue(all(line.endswith(" &&") for line in guards[:-1]))
        self.assertNotIn("||", condition[1])
        for guard in ("github.event_name == 'push'", "github.run_attempt == '1'",
                      "github.actor_id == '12478466'", "github.event.repository.owner.id == 12478466",
                      "github.ref == 'refs/tags/sidekick-hold-26-20261121'",
                      "github.event.created == true", "github.event.deleted == false",
                      "github.event.forced == false", "github.event.after == github.sha",
                      "github.event.before == '0000000000000000000000000000000000000000'"):
            self.assertIn(guard, condition[1])
        self.assertIn("group: sidekick-advisory-transport-v1\n  cancel-in-progress: false", self.workflow)
        self.assertIn("uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683", self.workflow)
        self.assertIn("ref: ${{ github.sha }}", self.workflow)
        self.assertIn("persist-credentials: false", self.workflow)

    def test_single_private_key_consumer_and_exact_permissions(self):
        self.assertEqual(self.workflow.count("APP_PRIVATE_KEY"), 1)
        self.assertEqual(self.workflow.count("secrets."), 1)
        self.assertNotIn("GITHUB_TOKEN", self.workflow)
        self.assertEqual(re.findall(r"^ +permission-.*$", self.workflow, re.MULTILINE),
                         ["          permission-checks: write"])
        self.assertEqual(re.findall(r"^ *permissions:\n((?: +[a-z-]+: [a-z]+\n)+)",
                                    self.workflow, re.MULTILINE), ["      contents: read\n"])
        mint = """        uses: actions/create-github-app-token@fee1f7d63c2ff003460e3d139729b119787bc349
        with:
          app-id: '5715914'
          private-key: ${{ secrets.APP_PRIVATE_KEY }}
          owner: moruku36
          repositories: local-ai-sidekick
          permission-checks: write
"""
        self.assertEqual(self.workflow.count(mint), 1)
        self.assertIn("CONFIGURED_APP_ID: ${{ vars.APP_ID }}", self.workflow)
        self.assertLess(self.workflow.index("sidekick_advisory_transport.py preflight"), self.workflow.index(mint))
        self.assertIn("SIDEKICK_INSTALLATION_ID: ${{ steps.app-token.outputs.installation-id }}", self.workflow)
        self.assertIn("SIDEKICK_APP_SLUG: ${{ steps.app-token.outputs.app-slug }}", self.workflow)


if __name__ == "__main__":
    unittest.main()
