from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import check_quality
import eval_ocr_mimo


class QualityBaselineRegressionTests(unittest.TestCase):
    def test_fixtures_integrity_passes_on_current_repo(self):
        res = check_quality.check_fixtures_integrity(REPO_ROOT)
        self.assertTrue(res["passed"], f"Fixtures check failed: {res.get('errors')}")
        self.assertGreaterEqual(res["samples_checked"], 2)

    def test_fixtures_detects_missing_sample(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            fdir = tmp_root / "tests" / "fixtures" / "synthetic_samples"
            fdir.mkdir(parents=True)
            manifest = {
                "samples": {
                    "missing.patch": {"type": "clean", "expected_defects_count": 0}
                }
            }
            (fdir / "synthetic_samples_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            res = check_quality.check_fixtures_integrity(tmp_root)
            self.assertFalse(res["passed"])
            self.assertTrue(any("missing" in err for err in res["errors"]))

    def test_fixtures_detects_empty_sample(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            fdir = tmp_root / "tests" / "fixtures" / "synthetic_samples"
            fdir.mkdir(parents=True)
            manifest = {
                "samples": {
                    "empty.patch": {"type": "clean", "expected_defects_count": 0}
                }
            }
            (fdir / "synthetic_samples_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (fdir / "empty.patch").write_text("", encoding="utf-8")
            res = check_quality.check_fixtures_integrity(tmp_root)
            self.assertFalse(res["passed"])
            self.assertTrue(any("empty" in err for err in res["errors"]))

    def test_unittests_fails_on_missing_required_suite(self):
        original_suites = check_quality.REQUIRED_TEST_SUITES
        try:
            check_quality.REQUIRED_TEST_SUITES = ["configs/non_existent_suite"]
            res = check_quality.check_existing_unittests(REPO_ROOT)
            self.assertFalse(res["passed"])
            self.assertEqual(res["total_tests_run"], 0)
        finally:
            check_quality.REQUIRED_TEST_SUITES = original_suites

    def test_ground_truth_strictly_excluded_from_ocr_payload(self):
        fixtures_dir = REPO_ROOT / "tests" / "fixtures" / "synthetic_samples"
        manifest = eval_ocr_mimo.load_manifest(fixtures_dir / "synthetic_samples_manifest.json")
        defect_meta = manifest["samples"]["defect_seeded.patch"]

        patch_info = eval_ocr_mimo.parse_patch_summary(fixtures_dir / "defect_seeded.patch")
        payload = eval_ocr_mimo.build_ocr_simulation_payload(patch_info)

        user_content = payload["messages"][1]["content"]
        for defect in defect_meta.get("ground_truth_defects", []):
            self.assertNotIn(defect["id"], user_content)
            self.assertNotIn(defect["cwe"], user_content)
            self.assertNotIn(defect["description"], user_content)

    def test_patches_apply_cleanly_to_sources(self):
        fixtures_dir = REPO_ROOT / "tests" / "fixtures" / "synthetic_samples"
        sources_dir = fixtures_dir / "sources"

        # 1. Clean patch apply check
        clean_before = sources_dir / "clean" / "before"
        clean_patch = fixtures_dir / "clean_refactor.patch"
        res_clean = subprocess.run(
            ["git", "apply", "--check", str(clean_patch)],
            cwd=clean_before,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            res_clean.returncode,
            0,
            f"clean_refactor.patch failed git apply --check: {res_clean.stderr}",
        )

        # 2. Defect patch apply check
        defect_before = sources_dir / "defect" / "before"
        defect_patch = fixtures_dir / "defect_seeded.patch"
        res_defect = subprocess.run(
            ["git", "apply", "--check", str(defect_patch)],
            cwd=defect_before,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            res_defect.returncode,
            0,
            f"defect_seeded.patch failed git apply --check: {res_defect.stderr}",
        )

    def test_ground_truth_target_lines_match_seeded_defects(self):
        fixtures_dir = REPO_ROOT / "tests" / "fixtures" / "synthetic_samples"
        manifest_path = fixtures_dir / "synthetic_samples_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        after_code_file = (
            fixtures_dir / "sources" / "defect" / "after" / "app" / "service" / "file_handler.py"
        )
        after_lines = after_code_file.read_text(encoding="utf-8").splitlines()

        expected_anchors = {
            "DEFECT-01": "self.base_path / user_supplied_name",
            "DEFECT-02": "open(target_path,",
            "DEFECT-03": "eval(filter_expr,",
            "DEFECT-04": "pass",
        }

        defects = manifest["samples"]["defect_seeded.patch"]["ground_truth_defects"]
        for defect in defects:
            did = defect["id"]
            line_no = defect["target_line"]
            self.assertLessEqual(line_no, len(after_lines), f"{did} line out of bounds")
            line_content = after_lines[line_no - 1]
            anchor = expected_anchors[did]
            self.assertIn(
                anchor,
                line_content,
                f"{did} at line {line_no} does not contain '{anchor}': got '{line_content}'",
            )


if __name__ == "__main__":
    unittest.main()
