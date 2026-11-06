#!/usr/bin/env python3
"""
tools/check_quality.py

multi-ai-workflow P1 決定的検査（非LLM）最小ラッパー。
外部依存なし（Python 3.11 標準ライブラリのみ）で動作し、
既存のテスト・構文検証・静的整合性を check-only で実行する。
自動修正・全面フォーマット・破壊的変更は行わない。
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import py_compile
import re
import subprocess
import sys
import time
from pathlib import Path


# 必須とされるテストスイート相対パス（存在しない、または実行件数0件の場合はFAILとする）
REQUIRED_TEST_SUITES = [
    "configs/openwebui-local-memory-0.11.4",
    "configs/openwebui-local-memory-0.11.4/confirmed-memory-tool",
    "configs/openwebui-local-memory-0.11.4/public-template/context-guard",
]


def get_git_head(repo_root: Path) -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return "UNKNOWN"


def check_python_syntax(repo_root: Path) -> dict:
    start_time = time.time()
    py_files: list[Path] = []
    for pattern in ["configs/**/*.py", "tools/**/*.py", "tests/**/*.py"]:
        for p in repo_root.glob(pattern):
            if ".venv" not in p.parts and "__pycache__" not in p.parts:
                py_files.append(p)

    errors = []
    for f in py_files:
        try:
            py_compile.compile(str(f), doraise=True)
        except py_compile.PyCompileError as e:
            errors.append({"file": str(f.relative_to(repo_root)), "error": str(e)})

    return {
        "check": "python_syntax",
        "command": "py_compile.compile",
        "passed": len(errors) == 0 and len(py_files) > 0,
        "files_checked": len(py_files),
        "errors": errors,
        "duration_sec": round(time.time() - start_time, 3),
    }


def check_existing_unittests(repo_root: Path) -> dict:
    start_time = time.time()
    total_ran = 0
    total_skipped = 0
    failures = 0
    errors = 0
    details = []

    for req_rel in REQUIRED_TEST_SUITES:
        td = repo_root / req_rel
        if not td.exists():
            failures += 1
            details.append({
                "directory": req_rel,
                "passed": False,
                "error": "Required test suite directory is missing",
                "tests_run": 0,
                "tests_skipped": 0,
            })
            continue

        try:
            cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"]
            res = subprocess.run(
                cmd,
                cwd=td,
                capture_output=True,
                text=True,
            )
            ran_count = 0
            skipped_count = 0
            for line in res.stderr.splitlines():
                if line.startswith("Ran ") and "tests" in line:
                    parts = line.split()
                    if len(parts) >= 2 and parts[1].isdigit():
                        ran_count = int(parts[1])
                skip_match = re.search(r"skipped=(\d+)", line)
                if skip_match:
                    skipped_count = int(skip_match.group(1))

            total_ran += ran_count
            total_skipped += skipped_count

            suite_passed = (res.returncode == 0) and (ran_count > 0)
            if not suite_passed:
                failures += 1

            details.append({
                "directory": req_rel,
                "passed": suite_passed,
                "tests_run": ran_count,
                "tests_skipped": skipped_count,
                "returncode": res.returncode,
                "zero_tests_flag": ran_count == 0,
                "output_tail": res.stderr.strip()[-300:] if res.stderr else "",
            })
        except Exception as e:
            errors += 1
            details.append({
                "directory": req_rel,
                "passed": False,
                "error": str(e),
                "tests_run": 0,
                "tests_skipped": 0,
            })

    all_passed = (failures == 0) and (errors == 0) and (total_ran > 0)
    return {
        "check": "existing_unittests",
        "command": "python -m unittest discover -s tests -p 'test_*.py'",
        "passed": all_passed,
        "total_tests_run": total_ran,
        "total_tests_skipped": total_skipped,
        "suites_checked": len(details),
        "required_suites_count": len(REQUIRED_TEST_SUITES),
        "details": details,
        "duration_sec": round(time.time() - start_time, 3),
    }


def check_fixtures_integrity(repo_root: Path) -> dict:
    start_time = time.time()
    fixtures_dir = repo_root / "tests" / "fixtures" / "synthetic_samples"
    manifest_path = fixtures_dir / "synthetic_samples_manifest.json"

    errors = []
    samples_checked = 0

    if not fixtures_dir.exists():
        errors.append("Fixtures directory does not exist: tests/fixtures/synthetic_samples")
    elif not manifest_path.exists():
        errors.append("Synthetic samples manifest missing: synthetic_samples_manifest.json")
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            samples = manifest.get("samples", {})
            if not samples:
                errors.append("Manifest contains no samples")
            for name, meta in samples.items():
                samples_checked += 1
                sample_file = fixtures_dir / name
                if not sample_file.exists():
                    errors.append(f"Sample patch file missing: {name}")
                elif sample_file.stat().st_size == 0:
                    errors.append(f"Sample patch file is empty: {name}")

            # mock_reviews の整合性検査
            mock_dir = fixtures_dir / "mock_reviews"
            if not mock_dir.exists():
                errors.append("mock_reviews directory missing")
            else:
                for mock_name in ["mock_review_clean.json", "mock_review_defect.json"]:
                    mp = mock_dir / mock_name
                    if not mp.exists():
                        errors.append(f"Mock review file missing: {mock_name}")
                    else:
                        try:
                            m_data = json.loads(mp.read_text(encoding="utf-8"))
                            if not m_data.get("is_mock", False):
                                errors.append(f"{mock_name} must have 'is_mock: true'")
                        except Exception as me:
                            errors.append(f"Invalid JSON in {mock_name}: {me}")
        except Exception as e:
            errors.append(f"Invalid JSON manifest: {e}")

    return {
        "check": "fixtures_integrity",
        "passed": len(errors) == 0 and samples_checked > 0,
        "samples_checked": samples_checked,
        "errors": errors,
        "duration_sec": round(time.time() - start_time, 3),
    }


def check_doc_formatting(repo_root: Path) -> dict:
    start_time = time.time()
    md_files = list(repo_root.glob("*.md")) + list(repo_root.glob("docs/**/*.md"))
    trailing_whitespace_files = []
    read_errors = []

    for f in md_files:
        if ".git" in f.parts:
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()
            abnormal = [
                i + 1 for i, line in enumerate(lines)
                if line.endswith("   ") or line.endswith("\t")
            ]
            if abnormal:
                trailing_whitespace_files.append({
                    "file": str(f.relative_to(repo_root)),
                    "lines": abnormal[:5],
                })
        except Exception as exc:
            read_errors.append({
                "file": str(f.relative_to(repo_root)),
                "error_type": type(exc).__name__,
            })

    return {
        "check": "doc_formatting",
        "command": "check_doc_formatting (internal)",
        "passed": not trailing_whitespace_files and not read_errors,
        "files_checked": len(md_files),
        "issues": trailing_whitespace_files,
        "read_errors": read_errors,
        "duration_sec": round(time.time() - start_time, 3),
    }


def inspect_external_tools() -> dict:
    tools = ["ruff", "semgrep", "node", "npm"]
    status = {}
    for tool in tools:
        found = False
        path = ""
        error_type = None
        cmd = ["where", tool] if os.name == "nt" else ["which", tool]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                path = res.stdout.strip().splitlines()[0]
                found = True
        except Exception as exc:
            error_type = type(exc).__name__
        status[tool] = {
            "available": found,
            "path": path if found else None,
            "status": "ERROR" if error_type else ("AVAILABLE" if found else "MISSING"),
            "error_type": error_type,
            "note": ("Tool availability inspection failed" if error_type else
                     "Available in PATH" if found else "Not installed in current PATH (installation required)"),
        }
    return {
        "check": "external_tool_inspection",
        "tools": status,
    }


def check_selected_static_tools(repo_root: Path, targets: list[str], tools: list[str]) -> dict:
    """Opt-in adapter; import failure is a failed requested check, never a pass."""
    try:
        module_name = f"{__package__}.run_static_checks" if __package__ else "run_static_checks"
        adapter = importlib.import_module(module_name)
        result = adapter.run_static_checks(repo_root, targets, tools)
        if not isinstance(result, dict) or result.get("status") not in (
            "PASSED", "FAILED", "ERROR", "UNSUPPORTED_PLATFORM"
        ) or not isinstance(result.get("results"), list):
            raise ValueError("Invalid static adapter result")
        if any(not isinstance(row, dict) for row in result["results"]):
            raise ValueError("Invalid static engine result")
        if any(not isinstance(row.get("tool"), str) or row["tool"] not in tools
               or not isinstance(row.get("status"), str) for row in result["results"]):
            raise ValueError("Invalid static engine identity or status")
        if len({row["tool"] for row in result["results"]}) != len(result["results"]):
            raise ValueError("Duplicate static engine result")
        if result["status"] == "PASSED" and (
            len(result["results"]) != len(tools)
            or {row.get("tool") for row in result["results"]} != set(tools)
            or any(row.get("status") != "PASSED" or row.get("passed") is not True
                   for row in result["results"])
        ):
            raise ValueError("Incomplete static success report")
        return result
    except Exception as exc:
        # Do not expose paths, source text, or environment values from diagnostics.
        return {"status": "ERROR", "results": [], "sources": [],
                "error": f"Static adapter failed: {type(exc).__name__}"}


def run_all_checks(
    repo_root: Path,
    static_targets: list[str] | None = None,
    static_tools: list[str] | None = None,
) -> dict:
    if static_tools is not None and static_targets is None:
        raise ValueError("Static tools require explicit static targets")
    requested_tools = list(static_tools) if static_tools is not None else ["ruff", "semgrep"]
    if static_targets is not None and (
        not static_targets or not requested_tools
        or any(tool not in ("ruff", "semgrep") for tool in requested_tools)
        or len(set(requested_tools)) != len(requested_tools)
    ):
        raise ValueError("Select nonempty static targets and unique supported tools")
    start_time = time.time()
    head = get_git_head(repo_root)

    syntax = check_python_syntax(repo_root)
    unittests = check_existing_unittests(repo_root)
    fixtures = check_fixtures_integrity(repo_root)
    docs = check_doc_formatting(repo_root)
    tools = inspect_external_tools()
    static = None
    if static_targets is not None:
        static = check_selected_static_tools(repo_root, static_targets, requested_tools)

    all_passed = syntax["passed"] and unittests["passed"] and fixtures["passed"]
    if static is not None:
        all_passed = all_passed and static.get("status") == "PASSED"

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "git_head": head,
        "overall_status": "PASSED" if all_passed else "FAILED",
        "total_duration_sec": round(time.time() - start_time, 3),
        "results": {
            "python_syntax": syntax,
            "existing_unittests": unittests,
            "fixtures_integrity": fixtures,
            "doc_formatting": docs,
            "tool_inspection": tools,
        },
        "unverified_scope": [
            "Ruff formatting (not included in the static adapter)",
            "Pele diagram rebuild (pele dependency requires offline npm ci)",
            "Alibaba OCR tool integration & pinned version (Pending standalone setup)",
            "MiMo API live invocation & cost ceiling enforcement (Pending authorization and quota boundaries)",
            "Cloudflare security audit skill (Reserved for high-risk auth/boundary changes)",
        ],
    }
    if static is not None:
        report["results"]["selected_static_checks"] = static
        report["unverified_scope"].append("Static analysis of files outside the explicit target selection")
    observed = {r.get("tool"): r.get("status") for r in (static or {}).get("results", [])}
    for tool, label in (("ruff", "Ruff lint"), ("semgrep", "Semgrep CE security check")):
        status = observed.get(tool, "NOT_RUN")
        if status not in ("PASSED", "FINDINGS"):
            report["unverified_scope"].append(f"{label} ({status}; no completed scan claimed)")
    return report


def main():
    parser = argparse.ArgumentParser(description="multi-ai-workflow P1 deterministic quality runner")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--static-target", action="append",
                        help="Opt in to static checks of an explicit relative .py file; repeat as needed")
    parser.add_argument("--static-tool", action="append", choices=("ruff", "semgrep"),
                        help="Installed static engine; defaults to both when --static-target is supplied")
    args = parser.parse_args()
    if args.static_tool and not args.static_target:
        parser.error("--static-tool requires --static-target")
    if args.static_tool and len(set(args.static_tool)) != len(args.static_tool):
        parser.error("--static-tool must not repeat the same engine")

    repo_root = Path(__file__).resolve().parent.parent
    report = run_all_checks(repo_root, args.static_target, args.static_tool)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"=== Quality Baseline P1 Report (HEAD: {report['git_head'][:8]}) ===")
        print(f"Status: {report['overall_status']}")
        print(f"Duration: {report['total_duration_sec']}s\n")
        print("Checks:")
        print(f"  - Python Syntax:      {'OK' if report['results']['python_syntax']['passed'] else 'FAIL'} ({report['results']['python_syntax']['files_checked']} files)")
        u_res = report['results']['existing_unittests']
        print(f"  - Unittests:          {'OK' if u_res['passed'] else 'FAIL'} ({u_res['total_tests_run']} ran, {u_res['total_tests_skipped']} skipped across {u_res['suites_checked']} suites)")
        f_res = report['results']['fixtures_integrity']
        print(f"  - Fixtures Integrity: {'OK' if f_res['passed'] else 'FAIL'} ({f_res['samples_checked']} samples verified)")
        print(f"  - Doc Format:         {'OK' if report['results']['doc_formatting']['passed'] else 'WARN'} ({report['results']['doc_formatting']['files_checked']} files)")
        print("\nExternal Tools in PATH:")
        for t, v in report["results"]["tool_inspection"]["tools"].items():
            print(f"  - {t:<8}: {v['status']} ({v['note']})")
        static = report["results"].get("selected_static_checks")
        if static is not None:
            print(f"\nSelected Static Checks: {static['status']}")
            for result in static.get("results", []):
                print(f"  - {result['tool']}: {result['status']} ({len(result.get('findings', []))} findings)")
        print("\nUnverified Scope:")
        for uv in report["unverified_scope"]:
            print(f"  - {uv}")

    sys.exit(0 if report["overall_status"] == "PASSED" else 1)


if __name__ == "__main__":
    main()
