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
import json
import os
import py_compile
import subprocess
import sys
import time
import unittest
from pathlib import Path


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
    # multi-ai-workflow 配下の .py ファイルを探索
    for pattern in ["configs/**/*.py", "tools/**/*.py"]:
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
        "passed": len(errors) == 0,
        "files_checked": len(py_files),
        "errors": errors,
        "duration_sec": round(time.time() - start_time, 3),
    }


def check_existing_unittests(repo_root: Path) -> dict:
    start_time = time.time()
    test_dirs = [
        repo_root / "configs" / "openwebui-local-memory-0.11.4",
        repo_root / "configs" / "openwebui-local-memory-0.11.4" / "confirmed-memory-tool",
        repo_root / "configs" / "openwebui-local-memory-0.11.4" / "public-template" / "context-guard",
    ]

    total_ran = 0
    failures = 0
    errors = 0
    details = []

    for td in test_dirs:
        if not td.exists():
            continue
        rel_dir = str(td.relative_to(repo_root))
        try:
            # 各テストスイートは該当ディレクトリをCWDとして実行
            cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"]
            res = subprocess.run(
                cmd,
                cwd=td,
                capture_output=True,
                text=True,
            )
            passed = res.returncode == 0
            # 標準エラー出力から "Ran X tests" を抽出
            ran_count = 0
            for line in res.stderr.splitlines():
                if line.startswith("Ran ") and "tests" in line:
                    parts = line.split()
                    if len(parts) >= 2 and parts[1].isdigit():
                        ran_count = int(parts[1])
            total_ran += ran_count
            if not passed:
                failures += 1
            details.append({
                "directory": rel_dir,
                "passed": passed,
                "tests_run": ran_count,
                "returncode": res.returncode,
                "output_tail": res.stderr.strip()[-300:] if res.stderr else "",
            })
        except Exception as e:
            errors += 1
            details.append({
                "directory": rel_dir,
                "passed": False,
                "error": str(e),
            })

    return {
        "check": "existing_unittests",
        "command": "python -m unittest discover -s tests -p 'test_*.py'",
        "passed": failures == 0 and errors == 0,
        "total_tests_run": total_ran,
        "suites_checked": len(details),
        "details": details,
        "duration_sec": round(time.time() - start_time, 3),
    }


def check_doc_formatting(repo_root: Path) -> dict:
    start_time = time.time()
    md_files = list(repo_root.glob("*.md")) + list(repo_root.glob("docs/**/*.md"))
    trailing_whitespace_files = []

    for f in md_files:
        if ".git" in f.parts:
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()
            has_tw = any(line.endswith(" ") or line.endswith("\t") for line in lines)
            if has_tw:
                # Markdownでは改行目的で末尾スペース2つを使うことがあるため、3つ以上またはタブを警告対象とする
                abnormal = [
                    i + 1 for i, line in enumerate(lines)
                    if line.endswith("   ") or line.endswith("\t")
                ]
                if abnormal:
                    trailing_whitespace_files.append({
                        "file": str(f.relative_to(repo_root)),
                        "lines": abnormal[:5],
                    })
        except Exception:
            pass

    return {
        "check": "doc_formatting",
        "command": "check_doc_formatting (internal)",
        "passed": len(trailing_whitespace_files) == 0,
        "files_checked": len(md_files),
        "issues": trailing_whitespace_files,
        "duration_sec": round(time.time() - start_time, 3),
    }


def inspect_external_tools() -> dict:
    tools = ["ruff", "semgrep", "node", "npm"]
    status = {}
    for tool in tools:
        found = False
        path = ""
        # which / where check
        cmd = ["where", tool] if os.name == "nt" else ["which", tool]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                found = True
                path = res.stdout.strip().splitlines()[0]
        except Exception:
            pass
        status[tool] = {
            "available": found,
            "path": path if found else None,
            "note": "Available in PATH" if found else "Not installed in current PATH (installation required)",
        }
    return {
        "check": "external_tool_inspection",
        "tools": status,
    }


def run_all_checks(repo_root: Path) -> dict:
    start_time = time.time()
    head = get_git_head(repo_root)

    syntax = check_python_syntax(repo_root)
    unittests = check_existing_unittests(repo_root)
    docs = check_doc_formatting(repo_root)
    tools = inspect_external_tools()

    all_passed = syntax["passed"] and unittests["passed"]

    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "git_head": head,
        "overall_status": "PASSED" if all_passed else "FAILED",
        "total_duration_sec": round(time.time() - start_time, 3),
        "results": {
            "python_syntax": syntax,
            "existing_unittests": unittests,
            "doc_formatting": docs,
            "tool_inspection": tools,
        },
        "unverified_scope": [
            "Ruff lint / format check (Ruff not installed in multi-ai-workflow environment)",
            "Semgrep CE security check (Semgrep not installed in multi-ai-workflow environment)",
            "Pele diagram rebuild (pele dependency requires offline npm ci)",
            "Alibaba OCR + MiMo API Review (Pending P3 authorization and credential budget definition)",
            "Cloudflare security audit skill (Reserved for high-risk auth/boundary changes)",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="multi-ai-workflow P1 deterministic quality runner")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    report = run_all_checks(repo_root)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"=== Quality Baseline P1 Report (HEAD: {report['git_head'][:8]}) ===")
        print(f"Status: {report['overall_status']}")
        print(f"Duration: {report['total_duration_sec']}s\n")
        print("Checks:")
        print(f"  - Python Syntax: {'OK' if report['results']['python_syntax']['passed'] else 'FAIL'} ({report['results']['python_syntax']['files_checked']} files)")
        print(f"  - Unittests:     {'OK' if report['results']['existing_unittests']['passed'] else 'FAIL'} ({report['results']['existing_unittests']['total_tests_run']} tests)")
        print(f"  - Doc Format:    {'OK' if report['results']['doc_formatting']['passed'] else 'WARN'} ({report['results']['doc_formatting']['files_checked']} files)")
        print("\nExternal Tools in PATH:")
        for t, v in report["results"]["tool_inspection"]["tools"].items():
            print(f"  - {t:<8}: {'AVAILABLE' if v['available'] else 'MISSING'} ({v['note']})")
        print("\nUnverified Scope:")
        for uv in report["unverified_scope"]:
            print(f"  - {uv}")

    sys.exit(0 if report["overall_status"] == "PASSED" else 1)


if __name__ == "__main__":
    main()
