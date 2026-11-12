"""Exactly two authored offline cases. NOT executed; no execution budget added."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import central_review_readiness as readiness


class ReadinessCases(unittest.TestCase):
    def fixture(self, diff_size, blob_size):
        def git(*args, **kwargs):
            if args[0] in ("rev-parse", "merge-base"):
                return b"a" * 40 + b"\n"
            if args[0] == "ls-tree":
                return b"100644 blob " + b"b" * 40 + b" " + str(blob_size).encode() + b"\tapp.py\0"
            if "--name-only" in args:
                return b"app.py\0"
            return b"x" * diff_size
        return patch.object(readiness, "git", side_effect=git)

    def test_local_sizes_never_grant_external_authority(self):
        with self.fixture(10, 12), patch.object(readiness, "policy_observations", return_value={
                "config_flags_observed": {"enabled": True, "paid_execution_authorized": True}}):
            result = readiness.readiness()
        self.assertEqual(result["local_diff"]["diff_bytes"], 10)
        self.assertEqual(result["local_diff"]["before_after_blob_bytes"], 24)
        self.assertEqual(result["status"], "PENDING_NOT_AUTHORIZED")
        self.assertFalse(result["live_acceptance"])
        self.assertEqual(set(result["stages"].values()), {"PENDING_EXTERNAL_EVIDENCE"})

    def test_oversized_diff_and_snapshots_stay_blocked(self):
        with self.fixture(65537, 32769):
            result = readiness.measure()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["diff_bytes"], 65537)
        self.assertEqual(result["before_after_blob_bytes"], 65538)
        self.assertEqual(set(result["blockers"]), {"diff_cap", "snapshot_cap"})
        self.assertEqual(result["caps"], {"paths": 20, "diff_bytes": 65536,
                                          "before_after_blob_bytes": 65536})


if __name__ == "__main__":
    unittest.main()
