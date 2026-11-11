#!/usr/bin/env python3
"""Three authored, UNEXECUTED mocked cases; no live acceptance is implied.

No Git/OCR CLI, HTTP, provider, thread or process runs. Separate owner approval
and a new evaluation budget are required before executing these cases.
"""
from contextlib import ExitStack, contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import automatic_dual_review as auto
import central_review_hub as hub
from check_central_review_hub import BASE, ENV, HEAD, Harness, binding, report


SNAPSHOTS = {"README.md": [None, "# Review fixture\n"],
             "docs/guide.md": ["Before\n", "After\n"],
             "src/sample.py": ["value = 1\n", "value = 2\n"]}
UNSAFE = "PRIVATE_PROVIDER_TEXT /private/example Bearer dummy @someone ```"


@contextmanager
def mocked_adapter(relay, cli, shutdown=None):
    """Real adapter/file wiring, with every execution/credential seam replaced."""
    state = SimpleNamespace()

    class OfflineServer:
        def __init__(self, *_args):
            state.server = self
            self.server_port = 1
            self.serve_forever = Mock()
            self.shutdown = Mock(side_effect=shutdown)
            self.server_close = Mock()

    state.worker = Mock()
    state.worker.is_alive.return_value = False
    with tempfile.TemporaryDirectory(prefix="central-offline-home-") as home, ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, {"MIMO_API_KEY": "offline-dummy"}, clear=True))
        stack.enter_context(patch.object(auto.Path, "home", return_value=Path(home)))
        stack.enter_context(patch.object(auto.connection, "checked_binary", return_value=(
            Path("/offline/ocr"), sorted(auto.connection.BINARY_HASHES)[0])))
        stack.enter_context(patch.object(auto.connection, "child_environment", return_value={
            "OCR_LLM_TOKEN": "offline-relay", "OCR_LLM_URL": "http://127.0.0.1:1/v1"}))
        stack.enter_context(patch.object(auto, "ReviewRelay", return_value=relay))
        stack.enter_context(patch.object(auto, "HTTPServer", OfflineServer))
        stack.enter_context(patch.object(auto.threading, "Thread", return_value=state.worker))
        state.git = stack.enter_context(patch.object(auto, "git", return_value=b""))
        state.cli = stack.enter_context(patch.object(auto.subprocess, "run", side_effect=cli))
        yield state


class CentralReviewRepairCases(unittest.TestCase):
    def test_trusted_markdown_rule_wiring(self):
        relay = SimpleNamespace(token="offline-relay", attempts=1, completed=1,
                                halted=False, usage=[])

        def cli(argv, **kwargs):
            repo = Path(argv[argv.index("--repo") + 1])
            rule = Path(argv[argv.index("--rule") + 1])
            self.assertEqual(rule.parent, repo.parent)
            self.assertNotEqual(rule.parent, repo)
            self.assertEqual(json.loads(rule.read_text()), {"include": ["**/*.md"]})
            self.assertFalse((repo / "rules.json").exists())
            self.assertEqual((repo / "README.md").read_text(), SNAPSHOTS["README.md"][1])
            tools = json.loads(Path(argv[argv.index("--tools") + 1]).read_text())
            self.assertEqual([tool["name"] for tool in tools], ["task_done", "code_comment"])
            self.assertIn("--no-filter", argv)
            self.assertEqual(argv[argv.index("--concurrency") + 1], "1")
            self.assertEqual(argv[argv.index("--timeout") + 1], "1")
            self.assertEqual(kwargs["timeout"], 150)
            self.assertEqual(kwargs["cwd"], repo)
            self.assertEqual(kwargs["stderr"], subprocess.DEVNULL)
            self.assertNotIn("MIMO_API_KEY", kwargs["env"])
            self.assertNotIn("GH_TOKEN", kwargs["env"])
            Path(argv[argv.index("--output") + 1]).write_text(json.dumps({
                "status": "complete", "warnings": [], "llm": {"model": auto.connection.MODEL},
                "summary": {"files_reviewed": len(SNAPSHOTS)}, "comments": []}))
            return SimpleNamespace(returncode=0)

        with mocked_adapter(relay, cli) as state:
            result = auto.alibaba(Path("/offline/ocr"), SNAPSHOTS)
        state.cli.assert_called_once()
        state.server.shutdown.assert_called_once()
        state.server.server_close.assert_called_once()
        state.worker.join.assert_called_once_with(timeout=31)
        self.assertEqual(result["findings"], [])
        self.assertEqual((result["http_attempts"], result["completed_responses"]), (1, 1))

    def test_safe_alibaba_failure_diagnostics(self):
        relay = SimpleNamespace(token="offline-relay", attempts=2, completed=1,
                                halted=False, usage=[{"prompt_tokens": 7,
                                    "completion_tokens": True, "total_tokens": 10**30,
                                    "headers": UNSAFE}])

        def shutdown():
            relay.attempts, relay.completed, relay.halted = 3, 2, True
            relay.usage.append({"prompt_tokens": 11, "completion_tokens": 2,
                                "total_tokens": 13, "provider_text": UNSAFE})
            raise RuntimeError(UNSAFE)  # Secondary failure must not mask CLI exit.

        with mocked_adapter(relay, Mock(return_value=SimpleNamespace(returncode=9)), shutdown) as state:
            with self.assertRaises(auto.LaneError) as caught:
                auto.alibaba(Path("/offline/ocr"), SNAPSHOTS)
        diagnostic = caught.exception.diagnostics
        self.assertEqual(diagnostic, {
            "failure_stage": "cli_exit_nonzero", "cli_exit_code": 9,
            "http_attempts": 3, "completed_responses": 2, "relay_halted": True,
            "usage": [{"prompt_tokens": 7, "completion_tokens": "unknown", "total_tokens": "unknown"},
                      {"prompt_tokens": 11, "completion_tokens": 2, "total_tokens": 13}]})
        self.assertIsNone(caught.exception.__cause__)
        self.assertNotIn(UNSAFE, str(caught.exception) + json.dumps(diagnostic))
        state.server.server_close.assert_called_once()
        state.worker.join.assert_called_once_with(timeout=31)
        rejected = auto.safe_diagnostics("alibaba", {
            "failure_stage": UNSAFE, "cli_exit_code": 256, "http_attempts": True,
            "completed_responses": -1, "relay_halted": UNSAFE, "usage": UNSAFE})
        self.assertEqual(rejected, {"failure_stage": "internal", "cli_exit_code": None,
            "http_attempts": "unknown", "completed_responses": "unknown",
            "relay_halted": "unknown", "usage": "unknown"})

    def test_central_failed_receipt_persists_safe_metadata(self):
        h = Harness(self)
        relay = SimpleNamespace(attempts=3, completed=2, halted=True,
                                usage=[{"prompt_tokens": 17, "completion_tokens": 3,
                                        "total_tokens": 20, "headers": UNSAFE}])
        error = auto.LaneError("alibaba", "cli_exit_nonzero", relay, 7)
        error.diagnostics["stderr"] = UNSAFE

        def lane(name, binary, diff, snapshots):
            h.lane(name, binary, diff, snapshots)  # Verifies durable pre-call readback.
            if name == "cloudflare":
                raise RuntimeError(UNSAFE)  # Untyped failures retain unknown counts.
            pipe = Mock()
            with patch.object(hub.os, "setsid"), patch.object(hub.os, "dup2"), \
                    patch.object(auto, "alibaba", side_effect=error):
                # Call the function with all process effects mocked; no worker is spawned.
                hub._lane_worker(pipe, auto, name, binary, diff, snapshots)
            pipe.close.assert_called_once()
            raw = pipe.send_bytes.call_args.args[0]
            self.assertNotIn(UNSAFE, raw.decode())
            outcome = json.loads(raw)
            # Persistence must reproject even a malformed injected/IPC outcome.
            outcome.update(provider_text=UNSAFE, head_sha="d" * 40)
            outcome["diagnostics"].update(headers=UNSAFE, path=UNSAFE)
            return outcome

        h.lanes.side_effect = lane
        result = h.controller().run(ENV)
        receipt = h.receipts()[0]
        saved = report(receipt)
        self.assertEqual(result, {"status": "BLOCKED_OR_UNKNOWN", "reservations": 1,
                                  "completed": 0, "failed_or_unknown": 1})
        self.assertEqual(saved["status"], "INCOMPLETE")
        self.assertEqual(receipt["conclusion"], "failure")
        self.assertEqual(receipt["external_id"], BASE + ":" + HEAD)
        self.assertEqual({key: saved[key] for key in binding()}, binding())
        failed = saved["lanes"]["alibaba"]
        self.assertEqual({key: failed[key] for key in binding()}, binding())
        self.assertEqual(failed["diagnostics"], {
            "failure_stage": "cli_exit_nonzero", "cli_exit_code": 7,
            "http_attempts": 3, "completed_responses": 2, "relay_halted": True,
            "usage": [{"prompt_tokens": 17, "completion_tokens": 3, "total_tokens": 20}]})
        self.assertEqual(saved["lanes"]["cloudflare"]["diagnostics"], {
            "failure_stage": "internal", "cli_exit_code": None,
            "http_attempts": "unknown", "completed_responses": "unknown",
            "relay_halted": "unknown", "usage": "unknown"})
        self.assertNotIn(UNSAFE, json.dumps(h.receipts()))
        self.assertFalse(saved["merge_authorized"])
        self.assertFalse(saved["review_quality_accepted"])
        self.assertFalse(h.memory.unread_writes)
        again = h.controller().run(ENV)
        self.assertEqual(again["reservations"], 0)
        self.assertEqual(h.lanes.call_count, 2)
        self.assertEqual(h.sources.call_count, 1)
        self.assertEqual(len(h.ledger()), 1)
        self.assertTrue(json.loads(h.ledger()[0]["output"]["summary"])["consumed"])
        self.assertFalse(h.memory.unread_writes)


if __name__ == "__main__":
    unittest.main()
