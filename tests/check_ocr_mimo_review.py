#!/usr/bin/env python3
"""Exactly four selected cases; real pinned CLI uses loopback mock only."""
import argparse
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import ocr_mimo_review as review
import ocr_mimo_connection as connection

BINARY = None


def request():
    return json.dumps({"model": connection.MODEL,
                       "messages": [{"role": "user", "content": "synthetic"}]}).encode()


class ReviewChecks(unittest.TestCase):
    def test_real_cli_both_samples_without_ground_truth(self):
        result = review.run_review(BINARY)
        self.assertEqual(result["status"], "MOCK_REVIEW_PASSED", result)
        self.assertEqual([r["findings_count"] for r in result["results"]], [0, 1])
        self.assertFalse(result["review_quality_accepted"])
        self.assertLessEqual(result["http_attempts"], 8)

    def test_partial_skipped_wrong_model_and_invalid_locations_rejected(self):
        valid = {"status": "complete", "llm": {"model": connection.MODEL},
                 "summary": {"files_reviewed": 1}, "comments": []}
        self.assertEqual(review.ingest(valid, "a.py", 2)["findings_count"], 0)
        for status in ("partial", "failed", "skipped", "completed_with_warnings"):
            with self.assertRaises(connection.ProbeError):
                review.ingest({**valid, "status": status}, "a.py", 2)
        with self.assertRaises(connection.ProbeError):
            review.ingest({**valid, "llm": {"model": "other"}}, "a.py", 2)
        with self.assertRaises(connection.ProbeError):
            review.ingest({**valid, "comments": [{
                "path": "../a.py", "content": "x", "start_line": 1, "end_line": 1,
            }]}, "a.py", 2)

    def test_unknown_outcome_latches_and_limits_applied(self):
        relay = review.ReviewRelay(live=True)
        with patch.object(relay, "_forward", side_effect=TimeoutError()) as forward:
            for _ in range(2):
                with self.assertRaises(connection.ProbeError):
                    relay.exchange(request(), f"Bearer {relay.token}", "/v1/chat/completions")
            self.assertEqual(forward.call_count, 1)
        self.assertEqual(relay.attempts, 1)
        relay = review.ReviewRelay(live=True)
        sent = []
        def forward(body):
            sent.append(json.loads(body))
            return relay.mock_review(json.loads(body))
        with patch.object(relay, "_forward", side_effect=forward):
            for _ in range(8):
                relay.exchange(request(), f"Bearer {relay.token}", "/v1/chat/completions")
            with self.assertRaises(connection.ProbeError):
                relay.exchange(request(), f"Bearer {relay.token}", "/v1/chat/completions")
        self.assertEqual(len(sent), 8)
        self.assertEqual(sent[0]["max_tokens"], 2048)

    def test_coarse_category_is_not_fabricated_exact_match(self):
        data = {"status": "complete", "llm": {"model": connection.MODEL},
                "summary": {"files_reviewed": 1}, "comments": [{
                    "path": "a.py", "content": "review text", "category": "security",
                    "severity": "high", "start_line": 1, "end_line": 1,
                }]}
        result = review.ingest(data, "a.py", 2)
        self.assertEqual(result["findings"][0]["category"], "security")
        self.assertEqual(result["fine_category_matches"], "NOT_SCORED")
        self.assertEqual(result["missed_defects"], "PENDING_HUMAN_REVIEW")
        self.assertTrue(result["human_verification_required"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    BINARY = parser.parse_args().binary
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReviewChecks)
    if suite.countTestCases() != 4:
        raise SystemExit("selection changed; review budget")
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    raise SystemExit(not result.wasSuccessful())
