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

    def test_valid_fixtures_accepted_without_errors(self):
        fixtures_dir = REPO_ROOT / "tests" / "fixtures" / "synthetic_samples" / "mock_reviews"

        clean_data = json.loads((fixtures_dir / "mock_review_clean.json").read_text(encoding="utf-8"))
        errs_clean = eval_ocr_mimo.validate_reviewer_output(
            clean_data,
            expected_sample_file="clean_refactor.patch",
            expected_target_file="app/service/data_processor.py",
        )
        self.assertEqual(errs_clean, [], f"clean fixture should have no errors: {errs_clean}")

        defect_data = json.loads((fixtures_dir / "mock_review_defect.json").read_text(encoding="utf-8"))
        errs_defect = eval_ocr_mimo.validate_reviewer_output(
            defect_data,
            expected_sample_file="defect_seeded.patch",
            expected_target_file="app/service/file_handler.py",
        )
        self.assertEqual(errs_defect, [], f"defect fixture should have no errors: {errs_defect}")

    def test_validate_reviewer_output_rejects_non_dict_top_level(self):
        self.assertTrue(any("dictionary object" in e for e in eval_ocr_mimo.validate_reviewer_output(["not", "a", "dict"])))
        self.assertTrue(any("dictionary object" in e for e in eval_ocr_mimo.validate_reviewer_output("string")))

    def test_validate_reviewer_output_rejects_invalid_is_mock(self):
        base = {
            "schema_version": "1.0.0",
            "sample_file": "clean_refactor.patch",
            "status": "SUCCESS",
            "findings": [],
        }
        errs_str = eval_ocr_mimo.validate_reviewer_output({**base, "is_mock": "true"})
        self.assertTrue(any("boolean true" in e for e in errs_str))

        errs_num = eval_ocr_mimo.validate_reviewer_output({**base, "is_mock": 1})
        self.assertTrue(any("boolean true" in e for e in errs_num))

        errs_false = eval_ocr_mimo.validate_reviewer_output({**base, "is_mock": False})
        self.assertTrue(any("boolean true" in e for e in errs_false))

        errs_none = eval_ocr_mimo.validate_reviewer_output(base)
        self.assertTrue(any("boolean true" in e for e in errs_none))

    def test_validate_reviewer_output_rejects_invalid_schema_or_status_or_sample(self):
        base = {
            "schema_version": "1.0.0",
            "is_mock": True,
            "sample_file": "clean_refactor.patch",
            "status": "SUCCESS",
            "findings": [],
        }
        errs_ver = eval_ocr_mimo.validate_reviewer_output({**base, "schema_version": "2.0.0"})
        self.assertTrue(any("schema_version" in e for e in errs_ver))

        errs_st = eval_ocr_mimo.validate_reviewer_output({**base, "status": "FAILED"})
        self.assertTrue(any("status" in e for e in errs_st))

        errs_sf = eval_ocr_mimo.validate_reviewer_output(
            base, expected_sample_file="other_sample.patch"
        )
        self.assertTrue(any("sample_file mismatch" in e for e in errs_sf))

    def test_validate_reviewer_output_rejects_invalid_finding_fields(self):
        base = {
            "schema_version": "1.0.0",
            "is_mock": True,
            "sample_file": "defect_seeded.patch",
            "status": "SUCCESS",
        }
        target = "app/service/file_handler.py"

        bad_file = {**base, "findings": [{"file": "wrong_file.py", "line": 10, "severity": "LOW", "category": "sec/x"}]}
        errs = eval_ocr_mimo.validate_reviewer_output(bad_file, expected_target_file=target)
        self.assertTrue(any("file' mismatch" in e for e in errs))

        bad_line_bool = {**base, "findings": [{"file": target, "line": True, "severity": "LOW", "category": "sec/x"}]}
        errs = eval_ocr_mimo.validate_reviewer_output(bad_line_bool, expected_target_file=target)
        self.assertTrue(any("excluding booleans" in e for e in errs))

        bad_line_zero = {**base, "findings": [{"file": target, "line": 0, "severity": "LOW", "category": "sec/x"}]}
        errs = eval_ocr_mimo.validate_reviewer_output(bad_line_zero, expected_target_file=target)
        self.assertTrue(any("positive integer" in e for e in errs))

        bad_sev = {**base, "findings": [{"file": target, "line": 10, "severity": "INFORMATIONAL", "category": "sec/x"}]}
        errs = eval_ocr_mimo.validate_reviewer_output(bad_sev, expected_target_file=target)
        self.assertTrue(any("severity" in e for e in errs))

        bad_cat = {**base, "findings": [{"file": target, "line": 10, "severity": "LOW", "category": "nosep"}]}
        errs = eval_ocr_mimo.validate_reviewer_output(bad_cat, expected_target_file=target)
        self.assertTrue(any("category" in e for e in errs))

    def test_unhashable_schema_status_severity_rejected_without_exception(self):
        # 1. schema_version・status・severityに配列・辞書を渡してもTypeErrorを出さず検査エラーとして拒否
        base = {
            "schema_version": "1.0.0",
            "is_mock": True,
            "sample_file": "defect_seeded.patch",
            "status": "SUCCESS",
            "findings": [],
        }
        target = "app/service/file_handler.py"

        for invalid_val in [["1.0.0"], {"v": "1.0.0"}, 100, None]:
            errs = eval_ocr_mimo.validate_reviewer_output({**base, "schema_version": invalid_val})
            self.assertTrue(any("schema_version" in e for e in errs), f"Failed for schema_version={invalid_val!r}")

        for invalid_val in [["SUCCESS"], {"s": "SUCCESS"}, 200, None]:
            errs = eval_ocr_mimo.validate_reviewer_output({**base, "status": invalid_val})
            self.assertTrue(any("status" in e for e in errs), f"Failed for status={invalid_val!r}")

        for invalid_val in [["CRITICAL"], {"sev": "CRITICAL"}, 1, None]:
            finding = {"file": target, "line": 11, "severity": invalid_val, "category": "security/path_traversal"}
            errs = eval_ocr_mimo.validate_reviewer_output({**base, "findings": [finding]}, expected_target_file=target)
            self.assertTrue(any("severity" in e for e in errs), f"Failed for severity={invalid_val!r}")

    def test_message_and_rationale_type_validation(self):
        # 2. message・rationaleは省略時は空文字扱い（受理）、存在時は文字列のみ許可。null・数値・配列・辞書は拒否
        base = {
            "schema_version": "1.0.0",
            "is_mock": True,
            "sample_file": "defect_seeded.patch",
            "status": "SUCCESS",
        }
        target = "app/service/file_handler.py"
        valid_finding_minimal = {"file": target, "line": 11, "severity": "CRITICAL", "category": "security/path_traversal"}

        # 省略時はエラーなし
        errs_omitted = eval_ocr_mimo.validate_reviewer_output(
            {**base, "findings": [valid_finding_minimal]}, expected_target_file=target
        )
        self.assertEqual(errs_omitted, [])

        # 文字列時はエラーなし
        errs_str = eval_ocr_mimo.validate_reviewer_output(
            {**base, "findings": [{**valid_finding_minimal, "message": "ok", "rationale": "ok"}]},
            expected_target_file=target,
        )
        self.assertEqual(errs_str, [])

        # null, 数値, 配列, 辞書はすべて拒否され、採点関数に直接渡した場合も ValueError で遮断
        for field in ["message", "rationale"]:
            for bad_val in [None, 123, True, ["text"], {"text": "val"}]:
                bad_f = {**valid_finding_minimal, field: bad_val}
                bad_payload = {**base, "findings": [bad_f]}
                errs = eval_ocr_mimo.validate_reviewer_output(
                    bad_payload, expected_target_file=target
                )
                self.assertTrue(
                    any(field in e for e in errs),
                    f"Field {field!r} with {bad_val!r} should be rejected, got {errs}",
                )
                with self.assertRaises(ValueError):
                    eval_ocr_mimo.score_review_findings("defect_seeded.patch", bad_payload, {})

    def test_scoring_rejects_namespace_or_substring_false_match(self):
        # 3. 同じ行・無関係なカテゴリ・説明に「security」だけ含む例がmatchedにならないことを確認
        manifest = eval_ocr_mimo.load_manifest(
            REPO_ROOT / "tests" / "fixtures" / "synthetic_samples" / "synthetic_samples_manifest.json"
        )
        sample_meta = manifest["samples"]["defect_seeded.patch"]

        # ケースA: 行11 (GT: security/path_traversal)、無関係カテゴリ style/naming、説明に "security" を含む
        false_security_keyword_review = {
            "schema_version": "1.0.0",
            "is_mock": True,
            "sample_file": "defect_seeded.patch",
            "status": "SUCCESS",
            "findings": [
                {
                    "file": "app/service/file_handler.py",
                    "line": 11,
                    "severity": "LOW",
                    "category": "style/naming",
                    "message": "Naming convention issue in security module",
                    "rationale": "This is just a naming note mentioning security.",
                }
            ],
        }
        score_a = eval_ocr_mimo.score_review_findings("defect_seeded.patch", false_security_keyword_review, sample_meta)
        self.assertEqual(score_a["metrics"]["matched_defects"], 0, "Substring 'security' in message must NOT cause a match")
        self.assertEqual(score_a["metrics"]["pending_human_review"], 1)

        # ケースB: 行11、同じ namespace だが別カテゴリ security/hardcoded_secret
        same_namespace_diff_cat_review = {
            "schema_version": "1.0.0",
            "is_mock": True,
            "sample_file": "defect_seeded.patch",
            "status": "SUCCESS",
            "findings": [
                {
                    "file": "app/service/file_handler.py",
                    "line": 11,
                    "severity": "MAJOR",
                    "category": "security/hardcoded_secret",
                    "message": "Hardcoded secret found",
                    "rationale": "Unrelated security category on same line",
                }
            ],
        }
        score_b = eval_ocr_mimo.score_review_findings("defect_seeded.patch", same_namespace_diff_cat_review, sample_meta)
        self.assertEqual(score_b["metrics"]["matched_defects"], 0, "Same namespace 'security/' alone must NOT cause a match")
        self.assertEqual(score_b["metrics"]["pending_human_review"], 1)

        # ケースC: 明示した別名 (security/directory_traversal) は matched になる
        alias_review = {
            "schema_version": "1.0.0",
            "is_mock": True,
            "sample_file": "defect_seeded.patch",
            "status": "SUCCESS",
            "findings": [
                {
                    "file": "app/service/file_handler.py",
                    "line": 11,
                    "severity": "CRITICAL",
                    "category": "security/directory_traversal",
                    "message": "Directory traversal detected",
                }
            ],
        }
        score_c = eval_ocr_mimo.score_review_findings("defect_seeded.patch", alias_review, sample_meta)
        self.assertEqual(score_c["metrics"]["matched_defects"], 1, "Explicitly mapped alias should match")

    def test_execution_metadata_omitted_normalizes_to_unknown(self):
        minimal_output = {
            "schema_version": "1.0.0",
            "is_mock": True,
            "sample_file": "clean_refactor.patch",
            "status": "SUCCESS",
            "findings": [],
        }
        errs = eval_ocr_mimo.validate_reviewer_output(minimal_output)
        self.assertEqual(errs, [])

        score = eval_ocr_mimo.score_review_findings(
            "clean_refactor.patch",
            minimal_output,
            {"expected_defects_count": 0, "ground_truth_defects": []},
        )
        obs = score["observed_execution"]
        for k in ["latency_sec", "input_tokens", "output_tokens", "cost_usd", "model_id"]:
            self.assertEqual(obs[k], "unknown", f"{k} should be normalized to unknown, not 0")

    def test_scoring_categorizes_matched_duplicate_missed_pending(self):
        fixtures_dir = REPO_ROOT / "tests" / "fixtures" / "synthetic_samples"
        mock_defect_path = fixtures_dir / "mock_reviews" / "mock_review_defect.json"
        mock_data = json.loads(mock_defect_path.read_text(encoding="utf-8"))

        manifest = eval_ocr_mimo.load_manifest(fixtures_dir / "synthetic_samples_manifest.json")
        sample_meta = manifest["samples"]["defect_seeded.patch"]

        score = eval_ocr_mimo.score_review_findings("defect_seeded.patch", mock_data, sample_meta)
        m = score["metrics"]

        self.assertEqual(m["matched_defects"], 3)
        self.assertEqual(m["duplicate_findings"], 1)
        self.assertEqual(m["missed_defects"], 1)
        self.assertEqual(m["pending_human_review"], 1)
        self.assertTrue(m["human_verification_required"])
        self.assertEqual(score["observed_execution"]["latency_sec"], "unknown")
        self.assertEqual(score["observed_execution"]["cost_usd"], "unknown")

    def test_scoring_divergent_content_on_same_line_marked_pending(self):
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

        self.assertEqual(m["matched_defects"], 0)
        self.assertEqual(m["pending_human_review"], 1)
        self.assertEqual(m["missed_defects"], 4)
        self.assertTrue(m["human_verification_required"])

    def test_evaluate_mock_reviews_fails_on_missing_fixture(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            fdir = tmp_root / "tests" / "fixtures" / "synthetic_samples"
            fdir.mkdir(parents=True)
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
