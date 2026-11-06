from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("static_checks", ROOT / "tools/run_static_checks.py")
checks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checks)


class StaticCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "a.py").write_text("answer = 42\n")

    def tearDown(self):
        self.temp.cleanup()

    def run_fake(self, tool="ruff", output="[]", code=0, status="FINISHED"):
        with patch.object(checks, "find_executable", return_value="/trusted/" + tool), patch.object(
            checks, "execute", return_value={"status": status, "returncode": code, "stdout": output}
        ) as run:
            report = checks.run_static_checks(self.root, ["a.py"], [tool])
            return report, run

    @staticmethod
    def semgrep(**changes):
        value = {"version": "1.0.0", "results": [], "errors": [], "paths": {"scanned": ["a.py"]}}
        value.update(changes)
        return json.dumps(value)

    def test_rejects_unsafe_targets_without_launch(self):
        (self.root / "link.py").symlink_to(self.root / "a.py")
        (self.root / "directory.py").mkdir()
        for names in ([], ["../a.py"], [str(self.root / "a.py")], ["link.py"],
                      ["directory.py"], ["a.py", "a.py"], ["missing.py"], ["a.txt"]):
            with self.subTest(names=names), patch.object(checks, "execute") as run:
                self.assertEqual(checks.run_static_checks(self.root, names)["status"], "ERROR")
                run.assert_not_called()
        (self.root / "large.py").write_bytes(b"x" * 11)
        with patch.object(checks, "MAX_FILE_BYTES", 10):
            with self.assertRaises(ValueError):
                checks.select_files(self.root, ["large.py"])

    def test_no_tool_is_not_a_pass(self):
        with patch.object(checks, "find_executable", return_value=None), patch.object(checks, "execute") as run:
            report = checks.run_static_checks(self.root, ["a.py"])
        self.assertEqual(report["status"], "FAILED")
        self.assertEqual([r["status"] for r in report["results"]], ["UNAVAILABLE", "UNAVAILABLE"])
        run.assert_not_called()

    def test_clean_scan_has_hashes_and_no_source_mutation(self):
        before = (self.root / "a.py").read_bytes()
        report, run = self.run_fake()
        self.assertEqual(report["status"], "PASSED")
        self.assertEqual(report["sources"][0]["sha256"], hashlib.sha256(before).hexdigest())
        command, stage, env = run.call_args.args
        self.assertEqual(command[0], "/trusted/ruff")
        for flag in ("--isolated", "--no-cache", "--ignore-noqa"):
            self.assertIn(flag, command)
        self.assertNotIn("--fix", command)
        self.assertEqual(command[-2:], ["--", "a.py"])
        self.assertFalse(stage.exists())
        self.assertEqual(before, (self.root / "a.py").read_bytes())

    def test_findings_fail_and_raw_messages_are_not_exposed(self):
        finding = {"filename": "a.py", "code": "F821", "message": "PRIVATE SOURCE TEXT",
                   "location": {"row": 1, "column": 1}}
        report, _ = self.run_fake(output=json.dumps([finding]), code=1)
        self.assertEqual(report["results"][0]["status"], "FINDINGS")
        self.assertNotIn("PRIVATE SOURCE TEXT", json.dumps(report))
        finding["code"] = "invalid-syntax"
        report, _ = self.run_fake(output=json.dumps([finding]), code=1)
        self.assertEqual(report["results"][0]["status"], "FINDINGS")
        finding["filename"] = "../outside.py"
        report, _ = self.run_fake(output=json.dumps([finding]), code=1)
        self.assertEqual(report["results"][0]["status"], "INVALID_OUTPUT")

    def test_invalid_exit_json_and_timeout_fail_closed(self):
        for output, code, status, expected in [
            ("not-json", 0, "FINISHED", "INVALID_OUTPUT"),
            ("{}", 0, "FINISHED", "INVALID_OUTPUT"),
            ("[]", 1, "FINISHED", "INVALID_OUTPUT"),
            ("[]", 2, "FINISHED", "TOOL_ERROR"),
            ("[]", None, "TIMEOUT", "TIMEOUT"),
        ]:
            with self.subTest(expected=expected):
                report, _ = self.run_fake(output=output, code=code, status=status)
                self.assertEqual(report["results"][0]["status"], expected)
                self.assertNotEqual(report["status"], "PASSED")

    def test_semgrep_malformed_or_partial_paths_never_pass(self):
        for paths in (None, [], "bad", {}, {"scanned": []}, {"scanned": ["a.py", "a.py"]},
                      {"scanned": ["outside.py"]}):
            with self.subTest(paths=paths):
                report, _ = self.run_fake("semgrep", self.semgrep(paths=paths))
                self.assertEqual(report["results"][0]["status"], "INVALID_OUTPUT")
        report, _ = self.run_fake("semgrep", self.semgrep(errors=[{"message": "parser failed"}]))
        self.assertEqual(report["results"][0]["status"], "INVALID_OUTPUT")

    def test_semgrep_complete_scan_and_pinned_local_rules(self):
        report, run = self.run_fake("semgrep", self.semgrep())
        self.assertEqual(report["status"], "PASSED")
        self.assertEqual(report["results"][0]["rules_sha256"], checks.RULES_SHA256)
        command = run.call_args.args[0]
        for flag in ("scan", "--oss-only", "--metrics=off", "--disable-version-check", "--disable-nosem", "--strict"):
            self.assertIn(flag, command)
        self.assertEqual(command[command.index("--jobs") + 1], "1")
        self.assertTrue(Path(command[command.index("--config") + 1]).is_absolute())
        self.assertFalse(any("https://" in v for v in command))
        wrong = self.root / "rules.json"
        wrong.write_text('{"rules": []}')
        with patch.object(checks, "RULES_PATH", wrong):
            report, run = self.run_fake("semgrep", self.semgrep())
        self.assertEqual(report["results"][0]["status"], "CONFIG_ERROR")
        run.assert_not_called()

    def test_semgrep_finding_normalization_and_limits(self):
        row = {"path": "a.py", "check_id": "local-python-dynamic-eval", "start": {"line": 1, "col": 1},
               "extra": {"message": "PRIVATE SOURCE", "severity": "ERROR", "lines": "eval(secret)"}}
        report, _ = self.run_fake("semgrep", self.semgrep(results=[row]), 1)
        self.assertEqual(report["results"][0]["status"], "FINDINGS")
        self.assertNotIn("PRIVATE SOURCE", json.dumps(report))
        self.assertNotIn("eval(secret)", json.dumps(report))
        with patch.object(checks, "MAX_FINDINGS", 0):
            report, _ = self.run_fake("semgrep", self.semgrep(results=[row]), 1)
        self.assertEqual(report["results"][0]["status"], "INVALID_OUTPUT")

    def test_env_strips_credentials_and_binary_discovery_rejects_repo_shims(self):
        with patch.dict(os.environ, {"SEMGREP_APP_TOKEN": "do-not-copy", "OPENAI_API_KEY": "do-not-copy",
                                    "HTTPS_PROXY": "do-not-copy", "PYTHONPATH": "do-not-copy"}):
            env = checks.isolated_env(self.root, self.root)
        for key in ("SEMGREP_APP_TOKEN", "OPENAI_API_KEY", "HTTPS_PROXY", "PYTHONPATH"):
            self.assertNotIn(key, env)
        with patch.dict(os.environ, {"PATH": f".:{self.root}:/trusted/bin"}), patch.object(
            checks.shutil, "which", return_value=str(self.root / "ruff")
        ) as which:
            self.assertIsNone(checks.find_executable("ruff", self.root))
            self.assertEqual(which.call_args.kwargs["path"], "/trusted/bin")
            self.assertEqual(checks.isolated_env(self.root, self.root)["PATH"], "/trusted/bin")

    def test_uncertain_cleanup_stops_next_tool(self):
        with patch.object(checks, "find_executable", return_value="/trusted/tool"), patch.object(
            checks, "execute", return_value={"status": "CLEANUP_ERROR", "returncode": None}
        ) as run:
            report = checks.run_static_checks(self.root, ["a.py"])
        self.assertEqual(run.call_count, 1)
        self.assertEqual(report["results"][1]["status"], "NOT_RUN")

    @unittest.skipUnless(os.name == "posix", "POSIX process-group adapter")
    def test_real_local_subprocess_success_timeout_and_output_bound(self):
        env = checks.isolated_env(self.root, self.root)
        result = checks.execute([sys.executable, "-c", "print('[]')"], self.root, env)
        self.assertEqual(result["status"], "FINISHED")
        self.assertEqual(result["stdout"].strip(), "[]")
        with patch.object(checks, "TIMEOUT_SECONDS", 0.05):
            result = checks.execute([sys.executable, "-c", "import time; time.sleep(10)"], self.root, env)
        self.assertEqual(result["status"], "TIMEOUT")
        with patch.object(checks, "MAX_OUTPUT_BYTES", 128):
            result = checks.execute([sys.executable, "-c", "print('x'*1024)"], self.root, env)
        self.assertEqual(result["status"], "OUTPUT_LIMIT")

    @unittest.skipUnless(os.name == "posix", "POSIX process-group adapter")
    def test_exited_leader_does_not_leave_running_child(self):
        marker = self.root / "child-survived"
        child = f"import time,pathlib; time.sleep(.3); pathlib.Path({str(marker)!r}).write_text('bad')"
        leader = f"import subprocess,sys; subprocess.Popen([sys.executable,'-c',{child!r}]); print('done')"
        result = checks.execute([sys.executable, "-c", leader], self.root, checks.isolated_env(self.root, self.root))
        self.assertEqual(result["status"], "FINISHED")
        time.sleep(.4)
        self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
