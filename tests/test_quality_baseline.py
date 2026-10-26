from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

# テスト対象モジュールのインポート
import sys
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
            # 存在しない架空の必須スイートを設定
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
        # Ground truth の注釈やID、CWE番号がプロンプトに含まれていないことを検証
        for defect in defect_meta.get("ground_truth_defects", []):
            self.assertNotIn(defect["id"], user_content)
            self.assertNotIn(defect["cwe"], user_content)
            self.assertNotIn(defect["description"], user_content)

    def test_clean_patch_semantic_equivalence(self):
        # 正常例パッチにDEFECTなどの不正キーワードが含まれず、正当なdiff形式であることを検証
        fixtures_dir = REPO_ROOT / "tests" / "fixtures" / "synthetic_samples"
        clean_content = (fixtures_dir / "clean_refactor.patch").read_text(encoding="utf-8")
        defect_content = (fixtures_dir / "defect_seeded.patch").read_text(encoding="utf-8")

        self.assertNotIn("DEFECT", clean_content)
        self.assertNotIn("DEFECT", defect_content)
        self.assertTrue(clean_content.startswith("diff --git"))
        self.assertTrue(defect_content.startswith("diff --git"))


if __name__ == "__main__":
    unittest.main()
