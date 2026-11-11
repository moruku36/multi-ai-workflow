#!/usr/bin/env python3
"""Exactly five selected tests; only loopback sockets, never a provider call."""
import argparse
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import ocr_mimo_connection as probe

BINARY = None


def request(*, second=False):
    messages = [{"role": "user", "content": "synthetic"}]
    if second:
        messages.append({"role": "tool", "tool_call_id": "fixture_call_1",
                         "content": "ocr_selftest ok"})
    return json.dumps({"model": probe.MODEL, "messages": messages,
                       "max_completion_tokens": 8192}).encode()


def exchange(relay, body):
    return relay.exchange(body, f"Bearer {relay.token}", "/v1/chat/completions")


class ConnectionChecks(unittest.TestCase):
    def test_real_pinned_cli_mock_tool_round_trip(self):
        result = probe.run_probe(BINARY)
        self.assertEqual(result["status"], "MOCK_PASSED")
        self.assertEqual(result["http_attempts"], 2)
        self.assertEqual(result["completed_responses"], 2)
        self.assertTrue(result["tool_round_trip"])
        self.assertFalse(result["review_quality_accepted"])
        self.assertEqual(result["usage"][0]["prompt_tokens"], "unknown")

    def test_no_credential_in_child_and_unauthenticated_request_never_forwarded(self):
        sentinel = "not-a-real-secret"
        with patch.dict(os.environ, {"MIMO_API_KEY": sentinel,
                                     "ANTHROPIC_API_KEY": sentinel,
                                     "HTTP_PROXY": sentinel, "OCR_ENABLE_TELEMETRY": "1"}):
            env = probe.child_environment("local-session-token", 12345)
        self.assertNotIn(sentinel, env.values())
        self.assertEqual(env["OCR_ENABLE_TELEMETRY"], "0")
        relay = probe.Relay(live=True, api_key=sentinel)
        with patch.object(relay, "_forward") as forward:
            with self.assertRaises(probe.ProbeError):
                relay.exchange(request(), "Bearer wrong", "/v1/chat/completions")
            forward.assert_not_called()
        self.assertEqual(relay.attempts, 0)

    def test_unknown_upstream_outcome_counts_and_latches_without_retry(self):
        relay = probe.Relay(live=True)
        with patch.object(relay, "_forward", side_effect=TimeoutError("sensitive body")) as forward:
            with self.assertRaises(probe.ProbeError) as error:
                exchange(relay, request())
            self.assertNotIn("sensitive", str(error.exception))
            with self.assertRaises(probe.ProbeError):
                exchange(relay, request())
            self.assertEqual(forward.call_count, 1)
        self.assertEqual(relay.attempts, 1)
        self.assertTrue(relay.halted)

    def test_oversize_request_and_model_substitution_are_not_success(self):
        relay = probe.Relay(live=True)
        with patch.object(relay, "_forward") as forward:
            with self.assertRaises(probe.ProbeError):
                exchange(relay, b"x" * (probe.MAX_REQUEST_BYTES + 1))
            forward.assert_not_called()
        relay = probe.Relay(live=True)
        bad = json.dumps({"model": "another-model", "choices": []}).encode()
        with patch.object(relay, "_forward", return_value=bad):
            with self.assertRaises(probe.ProbeError):
                exchange(relay, request())
        self.assertTrue(relay.halted)
        self.assertEqual(relay.completed, 0)

    def test_two_call_cap_and_zero_exit_without_evidence_fail_closed(self):
        relay = probe.Relay(live=True)
        sent = []
        def transport(body):
            sent.append(json.loads(body))
            return relay._mock()
        with patch.object(relay, "_forward", side_effect=transport) as forward:
            exchange(relay, request())
            exchange(relay, request(second=True))
            with self.assertRaises(probe.ProbeError):
                exchange(relay, request(second=True))
            self.assertEqual(forward.call_count, 2)
        self.assertTrue(relay.halted)
        self.assertEqual(sent[0]["max_tokens"], 1024)
        self.assertNotIn("max_completion_tokens", sent[0])
        with patch.object(probe.subprocess, "run") as run:
            run.return_value.returncode = 0
            result = probe.run_probe(BINARY)
        self.assertEqual(result["status"], "FAILED_OR_UNKNOWN")
        self.assertEqual(result["http_attempts"], 0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True, type=Path)
    args = parser.parse_args()
    BINARY = args.binary
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ConnectionChecks)
    if suite.countTestCases() != 5:
        raise SystemExit("selection changed; review the test budget")
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
