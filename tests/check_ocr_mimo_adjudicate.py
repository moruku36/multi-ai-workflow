#!/usr/bin/env python3
"""One selected receipt-binding case; handcrafted evidence, no CLI or API."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import ocr_mimo_adjudicate as adjudicate
import ocr_mimo_connection as connection
import ocr_mimo_review as review


class AdjudicationCheck(unittest.TestCase):
    def test_human_decision_is_bound_to_exact_receipt(self):
        # This live-shaped JSON is handcrafted test input, NOT live evidence.
        data = {
            "schema_version": "1.0", "mode": "live", "status": "LIVE_REVIEW_COMPLETED",
            "review_quality_accepted": False, "requested_model": connection.MODEL,
            "ocr_version": connection.VERSION, "ocr_source_commit": connection.SOURCE_COMMIT,
            "binary_sha256": sorted(connection.BINARY_HASHES)[0],
            "http_attempts": 2, "completed_responses": 2,
            "limits": {"http_attempts_total": review.MAX_CALLS, "request_bytes": review.MAX_BYTES,
                       "output_tokens_per_request": review.MAX_OUTPUT,
                       "request_timeout_seconds": connection.REQUEST_TIMEOUT},
            "results": [
                {"sample": sample, "status": "REVIEW_COMPLETED", "cli_exit_code": 0,
                 "diff_sha256": "a" * 64, "findings": [], "findings_count": 0}
                for sample in review.SAMPLES],
        }
        data["results"][1].update(findings_count=1, findings=[{
            "path": review.SAMPLES["defect"], "start_line": 11, "end_line": 11,
            "category": "security", "content": "Synthetic path containment finding.",
            "severity": "high"}])
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / "receipt.json"
            receipt.write_text(json.dumps(data))
            packet = adjudicate.prepare(receipt)
            finding = packet["samples"][1]["findings"][0]
            finding.update(decision="confirmed", ground_truth_ids=["DEFECT-01"],
                           rationale="Human test decision: missing path containment.")
            packet.update(human_review_completed=True,
                          completion_rationale="All findings and four seeded defects inspected.")
            report = adjudicate.summarize(receipt, packet)
            self.assertEqual(report["status"], "HUMAN_ADJUDICATED")
            self.assertEqual(report["metrics"][1]["confirmed_defects"], ["DEFECT-01"])
            self.assertEqual(report["metrics"][1]["missed_defects"],
                             ["DEFECT-02", "DEFECT-03", "DEFECT-04"])
            self.assertEqual(finding["finding"]["category"], "security")
            self.assertFalse(report["review_quality_accepted"])
            # Same parsed JSON but different bytes must invalidate prior decisions.
            receipt.write_text(receipt.read_text() + "\n")
            with self.assertRaises(ValueError):
                adjudicate.summarize(receipt, packet)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AdjudicationCheck)
    if suite.countTestCases() != 1:
        raise SystemExit("selection changed; review budget")
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    raise SystemExit(not result.wasSuccessful())
