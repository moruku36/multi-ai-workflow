from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_quality
import run_static_checks


class QualityIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.patches = ExitStack()
        self.addCleanup(self.patches.close)
        self.patches.enter_context(patch.object(check_quality, "get_git_head", return_value="test-head"))
        for name in ("check_python_syntax", "check_existing_unittests", "check_fixtures_integrity", "check_doc_formatting"):
            self.patches.enter_context(patch.object(check_quality, name, return_value={"passed": True}))
        self.patches.enter_context(patch.object(check_quality, "inspect_external_tools", return_value={"tools": {}}))

    def test_default_does_not_execute_static_engines(self):
        with patch.object(check_quality, "check_selected_static_tools") as run:
            report = check_quality.run_all_checks(ROOT)
        run.assert_not_called()
        self.assertEqual(report["overall_status"], "PASSED")
        self.assertNotIn("selected_static_checks", report["results"])
        self.assertTrue(any("Ruff lint (NOT_RUN" in v for v in report["unverified_scope"]))
        self.assertTrue(any("Semgrep CE security check (NOT_RUN" in v for v in report["unverified_scope"]))

    def test_selected_clean_scan_runs_once_and_is_included(self):
        result = {"status": "PASSED", "results": [{"tool": "ruff", "status": "PASSED", "passed": True}]}
        with patch.object(check_quality, "check_selected_static_tools", return_value=result) as run:
            report = check_quality.run_all_checks(ROOT, ["tools/check_quality.py"], ["ruff"])
        run.assert_called_once_with(ROOT, ["tools/check_quality.py"], ["ruff"])
        self.assertEqual(report["overall_status"], "PASSED")
        self.assertIs(report["results"]["selected_static_checks"], result)
        self.assertTrue(any("outside the explicit target" in v for v in report["unverified_scope"]))
        self.assertTrue(any("Semgrep CE security check (NOT_RUN" in v for v in report["unverified_scope"]))
        self.assertFalse(any("Ruff lint (NOT_RUN" in v for v in report["unverified_scope"]))

    def test_findings_errors_missing_and_timeout_fail_overall(self):
        for status in ("FINDINGS", "UNAVAILABLE", "TIMEOUT", "INVALID_OUTPUT", "TOOL_ERROR"):
            with self.subTest(status=status):
                result = {"status": "FAILED", "results": [{"tool": "ruff", "status": status, "passed": False}]}
                with patch.object(check_quality, "check_selected_static_tools", return_value=result):
                    report = check_quality.run_all_checks(ROOT, ["tools/check_quality.py"], ["ruff"])
                self.assertEqual(report["overall_status"], "FAILED")
                if status == "FINDINGS":
                    self.assertFalse(any("Ruff lint (FINDINGS" in v for v in report["unverified_scope"]))
                else:
                    self.assertTrue(any(f"Ruff lint ({status}" in v for v in report["unverified_scope"]))

    def test_static_pass_does_not_hide_existing_baseline_failure(self):
        with patch.object(check_quality, "check_python_syntax", return_value={"passed": False}), patch.object(
            check_quality, "check_selected_static_tools", return_value={"status": "PASSED", "results": []}
        ):
            report = check_quality.run_all_checks(ROOT, ["tools/check_quality.py"])
        self.assertEqual(report["overall_status"], "FAILED")

    def test_invalid_selection_fails_before_baseline(self):
        for targets, tools in ((None, ["ruff"]), ([], ["ruff"]), (["a.py"], []),
                               (["a.py"], ["ruff", "ruff"]), (["a.py"], ["unsupported"])):
            with self.subTest(targets=targets, tools=tools), patch.object(check_quality, "check_python_syntax") as baseline:
                with self.assertRaises(ValueError):
                    check_quality.run_all_checks(ROOT, targets, tools)
                baseline.assert_not_called()

    def test_adapter_exception_is_redacted_and_fails(self):
        with patch.object(run_static_checks, "run_static_checks", side_effect=OSError("PRIVATE DIAGNOSTIC")):
            report = check_quality.run_all_checks(ROOT, ["tools/check_quality.py"])
        self.assertEqual(report["overall_status"], "FAILED")
        self.assertEqual(report["results"]["selected_static_checks"]["status"], "ERROR")
        self.assertNotIn("PRIVATE DIAGNOSTIC", str(report))

    def test_actual_adapter_missing_engines_is_not_baseline_success(self):
        with patch.object(run_static_checks, "find_executable", return_value=None), patch.object(run_static_checks, "execute") as launch:
            report = check_quality.run_all_checks(ROOT, ["tools/check_quality.py"])
        launch.assert_not_called()
        self.assertEqual(report["overall_status"], "FAILED")
        self.assertEqual([r["status"] for r in report["results"]["selected_static_checks"]["results"]],
                         ["UNAVAILABLE", "UNAVAILABLE"])

    def test_malformed_or_empty_success_is_rejected(self):
        for result in (None, {"status": "PASSED", "results": []},
                       {"status": "PASSED", "results": ["invalid"]},
                       {"status": "FAILED", "results": [{"tool": [], "status": "ERROR"}]},
                       {"status": "PASSED", "results": [{"tool": "ruff", "status": "PASSED", "passed": False}]}):
            with self.subTest(result=result), patch.object(run_static_checks, "run_static_checks", return_value=result):
                report = check_quality.run_all_checks(ROOT, ["tools/check_quality.py"], ["ruff"])
            self.assertEqual(report["overall_status"], "FAILED")
            self.assertEqual(report["results"]["selected_static_checks"]["status"], "ERROR")


class QualityDiagnosticTests(unittest.TestCase):
    def test_unreadable_document_is_reported_without_private_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("# Example\n")
            with patch.object(Path, "read_text", side_effect=PermissionError("PRIVATE DIAGNOSTIC")):
                result = check_quality.check_doc_formatting(root)
        self.assertFalse(result["passed"])
        self.assertEqual(result["read_errors"], [{"file": "README.md", "error_type": "PermissionError"}])
        self.assertNotIn("PRIVATE DIAGNOSTIC", str(result))

    def test_tool_inspection_exception_is_observable_and_redacted(self):
        with patch.object(check_quality.subprocess, "run", side_effect=OSError("PRIVATE DIAGNOSTIC")):
            result = check_quality.inspect_external_tools()
        for tool in result["tools"].values():
            self.assertFalse(tool["available"])
            self.assertEqual(tool["status"], "ERROR")
            self.assertEqual(tool["error_type"], "OSError")
            self.assertIsNone(tool["path"])
        self.assertNotIn("PRIVATE DIAGNOSTIC", str(result))

    def test_tool_inspection_available_and_missing_are_distinct(self):
        for code, output, expected in ((0, "/usr/bin/example\n", "AVAILABLE"), (1, "", "MISSING")):
            with self.subTest(expected=expected), patch.object(
                check_quality.subprocess, "run",
                return_value=subprocess.CompletedProcess([], code, stdout=output, stderr=""),
            ):
                result = check_quality.inspect_external_tools()
            for tool in result["tools"].values():
                self.assertEqual(tool["status"], expected)
                self.assertEqual(tool["available"], code == 0)
                self.assertIsNone(tool["error_type"])

    def test_empty_successful_tool_discovery_is_not_available(self):
        with patch.object(check_quality.subprocess, "run", return_value=(
            subprocess.CompletedProcess([], 0, stdout="", stderr="")
        )):
            result = check_quality.inspect_external_tools()
        for tool in result["tools"].values():
            self.assertFalse(tool["available"])
            self.assertEqual(tool["status"], "ERROR")
            self.assertIsNone(tool["path"])


if __name__ == "__main__":
    unittest.main()
