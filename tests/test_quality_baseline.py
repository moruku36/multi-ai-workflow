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

    def test_validate_reviewer_output_rejects_missing_keys_or_non_mock(self):
        # 1. 必須キー欠落
        bad_output_missing_key = {
            "schema_version": "1.0.0",
            # missing is_mock
            "sample_file": "clean_refactor.patch",
            "status": "SUCCESS",
            "findings": [],
        }
        errs = eval_ocr_mimo.validate_reviewer_output(bad_output_missing_key)
        self.assertTrue(any("is_mock" in e for e in errs))

        # 2. is_mock が False（実AI結果との誤混同防止）
        bad_output_false_mock = {
            "schema_version": "1.0.0",
            "is_mock": False,
            "sample_file": "clean_refactor.patch",
            "status": "SUCCESS",
            "findings": [],
        }
        errs = eval_ocr_mimo.validate_reviewer_output(bad_output_false_mock)
        self.assertTrue(any("is_mock" in e for e in errs))

        # 3. findings 内の必須フィールド欠落
        bad_finding = {
            "schema_version": "1.0.0",
            "is_mock": True,
            "sample_file": "clean_refactor.patch",
            "status": "SUCCESS",
            "findings": [{"file": "test.py", "line": 10}],  # missing severity, category
        }
        errs = eval_ocr_mimo.validate_reviewer_output(bad_finding)
        self.assertTrue(any("severity" in e for e in errs))

    def test_scoring_categorizes_matched_duplicate_missed_pending(self):
        fixtures_dir = REPO_ROOT / "tests" / "fixtures" / "synthetic_samples"
        mock_defect_path = fixtures_dir / "mock_reviews" / "mock_review_defect.json"
        mock_data = json.loads(mock_defect_path.read_text(encoding="utf-8"))

        manifest = eval_ocr_mimo.load_manifest(fixtures_dir / "synthetic_samples_manifest.json")
        sample_meta = manifest["samples"]["defect_seeded.patch"]

        score = eval_ocr_mimo.score_review_findings("defect_seeded.patch", mock_data, sample_meta)
        m = score["metrics"]

        # 期待値: 3 matched, 1 duplicate, 1 missed, 1 pending
        self.assertEqual(m["matched_defects"], 3)
        self.assertEqual(m["duplicate_findings"], 1)
        self.assertEqual(m["missed_defects"], 1)
        self.assertEqual(m["pending_human_review"], 1)
        self.assertTrue(m["human_verification_required"])
        # usage / cost / latency が未取得なら unknown
        self.assertEqual(score["observed_execution"]["latency_sec"], "unknown")
        self.assertEqual(score["observed_execution"]["input_tokens"], "unknown")
        self.assertEqual(score["observed_execution"]["output_tokens"], "unknown")
        self.assertEqual(score["observed_execution"]["cost_usd"], "unknown")

    def test_scoring_divergent_content_on_same_line_marked_pending(self):
        # 行番号は11でDEFECT-01(Path traversal)と一致するが、内容が全く無関係な場合
        divergent_review = {
            "schema_version": "1.0.0",
            "is_mock": True,
            "sample_file": "defect_seeded.patch",
            "status": "SUCCESS",
            "findings": [
                {
                    "file": "app/service/file_handler.py",
                    "line": 11,
                    "severity": "LOW",
                    "category": "style/variable_naming",
                    "message": "Variable name target_path is not descriptive enough",
                    "rationale": "Style nitpick unrelated to path traversal",
                }
            ],
        }
        manifest = eval_ocr_mimo.load_manifest(
            REPO_ROOT / "tests" / "fixtures" / "synthetic_samples" / "synthetic_samples_manifest.json"
        )
        sample_meta = manifest["samples"]["defect_seeded.patch"]

        score = eval_ocr_mimo.score_review_findings("defect_seeded.patch", divergent_review, sample_meta)
        m = score["metrics"]

        # 行番号一致だけで正解にせず、pending_human_review に分類されること
        self.assertEqual(m["matched_defects"], 0)
        self.assertEqual(m["pending_human_review"], 1)
        self.assertEqual(m["missed_defects"], 4)
        self.assertTrue(m["human_verification_required"])

    def test_evaluate_mock_reviews_fails_on_missing_fixture(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            fdir = tmp_root / "tests" / "fixtures" / "synthetic_samples"
            fdir.mkdir(parents=True)
            # マニフェストだけ用意し、mock_reviews は用意しない
            manifest = {
                "samples": {
                    "clean_refactor.patch": {"type": "clean"},
                    "defect_seeded.patch": {"type": "defect_seeded"},
                }
            }
            (fdir / "synthetic_samples_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            res = eval_ocr_mimo.evaluate_mock_reviews(fdir)
            self.assertEqual(res["status"], "FAILED")
            self.assertTrue(len(res["errors"]) > 0)


if __name__ == "__main__":
    unittest.main()
