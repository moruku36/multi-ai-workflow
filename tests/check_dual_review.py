"""Three selected receipt-gate cases. Not yet executed; existing trial exhausted."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "dual_review", Path(__file__).resolve().parents[1] / "tools/dual_review.py")
dual = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dual)


class DualReviewChecks(unittest.TestCase):
    def setUp(self):
        self.plan = {"base_sha": "a" * 40, "head_sha": "b" * 40, "diff_sha256": "c" * 64}
        self.receipts = {lane: {
            **self.plan, "schema_version": "1.0", "lane": lane, "status": "completed",
            "reviewer_provider": "example-provider", "reviewer_model": "example-model",
            "reviewer_id": lane + "-reviewer", "execution_evidence": "private execution record",
            "scope": "diff-only", "findings": [], "unresolved": [],
        } for lane in dual.LANES}

    def test_missing_and_pending_are_not_completed(self):
        self.assertEqual(dual.evaluate(self.plan, {}, self.plan["head_sha"])["status"],
                         "INCOMPLETE")
        self.receipts["cloudflare"]["status"] = "pending"
        self.assertEqual(dual.evaluate(self.plan, self.receipts, self.plan["head_sha"])["status"],
                         "INCOMPLETE")

    def test_wrong_binding_or_dirty_head_cannot_satisfy_gate(self):
        changed = copy.deepcopy(self.receipts)
        changed["cloudflare"]["diff_sha256"] = "d" * 64
        self.assertEqual(dual.evaluate(self.plan, changed, self.plan["head_sha"])["status"],
                         "INCOMPLETE")
        self.assertEqual(dual.evaluate(self.plan, self.receipts, "e" * 40)["status"], "STALE_HEAD")

    def test_recorded_findings_never_authorize_merge_or_prove_independence(self):
        self.receipts["alibaba"]["findings"] = [{"severity": "high", "content": "unresolved issue"}]
        result = dual.evaluate(self.plan, self.receipts, self.plan["head_sha"])
        self.assertEqual(result["status"], "BOTH_RECORDED_NOT_ACCEPTED")
        self.assertFalse(result["merge_authorized"])
        self.assertFalse(result["review_quality_accepted"])
        self.assertEqual(result["independence"], "NOT_VERIFIED")


if __name__ == "__main__":
    unittest.main(verbosity=0)
