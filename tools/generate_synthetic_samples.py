#!/usr/bin/env python3
"""
tools/generate_synthetic_samples.py

before / after の合成ソースファイルから Git diff パッチを自動生成し、
synthetic_samples_manifest.json の行番号整合性を担保する。
"""

from __future__ import annotations

import difflib
import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "synthetic_samples"
SOURCES_DIR = FIXTURES_DIR / "sources"


def generate_patch(rel_file: str, before_file: Path, after_file: Path) -> str:
    before_lines = before_file.read_text(encoding="utf-8").splitlines(keepends=True)
    after_lines = after_file.read_text(encoding="utf-8").splitlines(keepends=True)

    diff_lines = list(
        difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"a/{rel_file}",
            tofile=f"b/{rel_file}",
        )
    )

    header = [
        f"diff --git a/{rel_file} b/{rel_file}\n",
    ]
    return "".join(header + diff_lines)


def main():
    # 1. Clean sample
    clean_rel = "app/service/data_processor.py"
    clean_before = SOURCES_DIR / "clean" / "before" / "app" / "service" / "data_processor.py"
    clean_after = SOURCES_DIR / "clean" / "after" / "app" / "service" / "data_processor.py"
    clean_patch = generate_patch(clean_rel, clean_before, clean_after)
    (FIXTURES_DIR / "clean_refactor.patch").write_text(clean_patch, encoding="utf-8", newline="\n")

    # 2. Defect sample
    defect_rel = "app/service/file_handler.py"
    defect_before = SOURCES_DIR / "defect" / "before" / "app" / "service" / "file_handler.py"
    defect_after = SOURCES_DIR / "defect" / "after" / "app" / "service" / "file_handler.py"
    defect_patch = generate_patch(defect_rel, defect_before, defect_after)
    (FIXTURES_DIR / "defect_seeded.patch").write_text(defect_patch, encoding="utf-8", newline="\n")

    # 3. Ground truth target line verification
    after_code_lines = defect_after.read_text(encoding="utf-8").splitlines()
    manifest_path = FIXTURES_DIR / "synthetic_samples_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    expected_anchors = {
        "DEFECT-01": "self.base_path / user_supplied_name",
        "DEFECT-02": "open(target_path,",
        "DEFECT-03": "eval(filter_expr,",
        "DEFECT-04": "pass",
    }

    defect_entries = manifest["samples"]["defect_seeded.patch"]["ground_truth_defects"]
    for defect in defect_entries:
        did = defect["id"]
        line_no = defect["target_line"]
        actual_line = after_code_lines[line_no - 1]
        anchor = expected_anchors.get(did, "")
        if anchor not in actual_line:
            raise ValueError(
                f"Line mismatch for {did}: line {line_no} is '{actual_line}', expected anchor '{anchor}'"
            )

    print("Successfully generated and verified synthetic patches and manifest.")


if __name__ == "__main__":
    main()
