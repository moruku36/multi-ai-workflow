#!/usr/bin/env python3
"""
tools/eval_ocr_mimo.py

P3 合成サンプルおよび入力準備・オフライン評価受入＆採点ツール。
※本ツールは「合成サンプルと評価入力の準備、および模擬結果の受入れと採点ロジック検証」であり、
Alibaba OCR CLI 自体の統合や実 MiMo API 接続を行うものではありません。
外部APIは一切呼び出さず、完全オフラインで動作します。
正解データ（Ground Truth）はレビュアー入力から完全に除外されます。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path


SUPPORTED_SCHEMA_VERSIONS = {"1.0.0"}
ALLOWED_REVIEW_STATUSES = {"SUCCESS"}
ALLOWED_SEVERITIES = {"CRITICAL", "MAJOR", "MEDIUM", "LOW"}
CATEGORY_PATTERN = re.compile(r"^[a-z0-9_-]+/[a-z0-9_-]+$")

# 正規カテゴリに対する明示的な別名対応マップ（部分文字列やnamespaceのみの一致は不許可）
CATEGORY_ALIASES: dict[str, set[str]] = {
    "security/path_traversal": {"security/path_traversal", "security/directory_traversal"},
    "reliability/resource_leak": {"reliability/resource_leak", "reliability/unclosed_resource"},
    "security/code_injection": {"security/code_injection", "security/eval_injection", "security/rce"},
    "reliability/silent_failure": {"reliability/silent_failure", "reliability/empty_except"},
}


def is_category_match(finding_cat: str, gt_cat: str) -> bool:
    """
    正規カテゴリの完全一致、または明示した別名対応のみを機械的一致と判定する。
    namespaceのみの一致や説明文の部分文字列では一致としない。
    """
    f_norm = finding_cat.strip().lower()
    gt_norm = gt_cat.strip().lower()
    if f_norm == gt_norm:
        return True
    return f_norm in CATEGORY_ALIASES.get(gt_norm, set())


def load_manifest(manifest_path: Path) -> dict:
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_patch_summary(patch_path: Path) -> dict:
    if not patch_path.exists():
        raise FileNotFoundError(f"Patch file not found: {patch_path}")
    content = patch_path.read_text(encoding="utf-8")
    if not content.strip():
        raise ValueError(f"Patch file is empty: {patch_path}")

    lines = content.splitlines()
    files_changed = []
    additions = 0
    deletions = 0

    for line in lines:
        if line.startswith("+++ b/"):
            files_changed.append(line[6:])
        elif line.startswith("+") and not line.startswith("+++"):
            additions += 1
        elif line.startswith("-") and not line.startswith("---"):
            deletions += 1

    return {
        "file": patch_path.name,
        "targets": files_changed,
        "additions": additions,
        "deletions": deletions,
        "raw_patch": content,
    }


def build_ocr_simulation_payload(patch_info: dict, model_id: str = "mimo-v2.6-pro") -> dict:
    """
    OCR standalone + MiMo API (OpenAI互換) 形式のプロンプト/ペイロードを生成。
    重要: 正解データ (Ground Truth) や欠陥注釈はプロンプトに一切含めない。
    """
    system_instruction = (
        "You are an expert, objective code reviewer acting as a specialist line-by-line reviewer.\n"
        "Focus on Critical and Major bugs, security vulnerabilities (CWE), resource leaks, and silent failures.\n"
        "Do NOT nitpick style, comments, or formatting unless it impacts security or correctness.\n"
        "Output structured findings with file, line number, severity (CRITICAL, MAJOR, MEDIUM, LOW), and clear rationale."
    )

    user_content = (
        f"Review the following Git diff for repository security and reliability defects:\n\n"
        f"```diff\n{patch_info['raw_patch']}\n```"
    )

    estimated_prompt_tokens = (len(system_instruction) + len(user_content)) // 4

    return {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.1,
        "max_tokens": 1024,
        "estimated_prompt_tokens": estimated_prompt_tokens,
    }


def validate_reviewer_output(
    review_data: any,
    expected_sample_file: str | None = None,
    expected_target_file: str | None = None,
) -> list[str]:
    """
    Reviewerから受信したJSONデータの形式を厳格に検査する。
    1. 最上位は dict であること。
    2. is_mock は真偽値 True のみ（文字列 'true' や数値 1 は拒否）。
    3. schema_version・status は文字列型を確認した上で許可値と照合（配列・辞書でも例外を出さず拒否）。
    4. sample_file は採点対象パッチと一致すること。
    5. 各 finding は dict であり、file は対象ファイルと一致、line は正の整数（bool 除外）、
       severity・category は型確認後に定めた形式・値を検査。
    6. message・rationale は省略時は空文字として許容、存在時は文字列のみ許可（null・数値・配列・辞書は拒否）。
    7. execution_metadata は省略可能（省略時は unknown へ正規化）。存在するなら dict であること。
    """
    errors = []

    # 1. 最上位チェック
    if not isinstance(review_data, dict):
        return ["Reviewer output must be a JSON dictionary object"]

    # 2. is_mock チェック（真偽値 True のみ許可）
    is_mock = review_data.get("is_mock")
    if type(is_mock) is not bool or is_mock is not True:
        errors.append(
            f"Field 'is_mock' must be boolean true (got {type(is_mock).__name__}: {is_mock!r})"
        )

    # 3. schema_version チェック（型確認後に集合照合し、unhashable型でも例外を防いでエラー記録）
    schema_ver = review_data.get("schema_version")
    if not isinstance(schema_ver, str) or schema_ver not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append(
            f"Unsupported or invalid schema_version: {schema_ver!r} (supported: {sorted(SUPPORTED_SCHEMA_VERSIONS)})"
        )

    # 4. status チェック（型確認後に集合照合）
    status = review_data.get("status")
    if not isinstance(status, str) or status not in ALLOWED_REVIEW_STATUSES:
        errors.append(
            f"Reviewer status {status!r} is not a scorable success status (allowed: {sorted(ALLOWED_REVIEW_STATUSES)})"
        )

    # 5. sample_file チェック
    sample_file = review_data.get("sample_file")
    if not isinstance(sample_file, str) or not sample_file.strip():
        errors.append("Field 'sample_file' must be a non-empty string")
    elif expected_sample_file and sample_file != expected_sample_file:
        errors.append(
            f"sample_file mismatch: expected {expected_sample_file!r}, got {sample_file!r}"
        )

    # 6. execution_metadata チェック（省略可能、指定時は dict）
    if "execution_metadata" in review_data and review_data["execution_metadata"] is not None:
        if not isinstance(review_data["execution_metadata"], dict):
            errors.append("Field 'execution_metadata' must be a dictionary when provided")

    # 7. findings チェック
    findings = review_data.get("findings")
    if not isinstance(findings, list):
        errors.append("Field 'findings' must be a list of finding objects")
    else:
        for idx, f in enumerate(findings):
            if not isinstance(f, dict):
                errors.append(f"Finding at index {idx} must be a dictionary object")
                continue

            # 7.1 file チェック
            f_file = f.get("file")
            if not isinstance(f_file, str) or not f_file.strip():
                errors.append(f"Finding [{idx}] 'file' must be a non-empty string")
            elif expected_target_file and f_file != expected_target_file:
                errors.append(
                    f"Finding [{idx}] 'file' mismatch: expected {expected_target_file!r}, got {f_file!r}"
                )

            # 7.2 line チェック（bool を除く正の整数）
            f_line = f.get("line")
            if type(f_line) is not int or isinstance(f_line, bool) or f_line <= 0:
                errors.append(
                    f"Finding [{idx}] 'line' must be a positive integer excluding booleans (got {f_line!r})"
                )

            # 7.3 severity チェック（型確認後に集合照合）
            f_sev = f.get("severity")
            if not isinstance(f_sev, str) or f_sev not in ALLOWED_SEVERITIES:
                errors.append(
                    f"Finding [{idx}] 'severity' {f_sev!r} invalid (allowed: {sorted(ALLOWED_SEVERITIES)})"
                )

            # 7.4 category チェック
            f_cat = f.get("category")
            if not isinstance(f_cat, str) or not CATEGORY_PATTERN.match(f_cat):
                errors.append(
                    f"Finding [{idx}] 'category' {f_cat!r} invalid (must match pattern 'namespace/name')"
                )

            # 7.5 message・rationale チェック（省略時は許可、存在時は文字列のみ許可。null/数値/配列/辞書は拒否）
            for text_field in ("message", "rationale"):
                if text_field in f:
                    t_val = f[text_field]
                    if not isinstance(t_val, str):
                        errors.append(
                            f"Finding [{idx}] '{text_field}' must be a string when present (got {type(t_val).__name__}: {t_val!r})"
                        )

    return errors


def score_review_findings(sample_name: str, review_data: dict, sample_meta: dict) -> dict:
    """
    Reviewerの指摘とGround Truth（正解データ）を突合・採点する。
    不正入力が直接渡された場合は採点へ流さず ValueError で拒否する。
    正規カテゴリの完全一致または明示した別名対応のみを機械的一致とし、
    行番号一致でもカテゴリが異なる場合は説明文の部分文字列に関わらず「判定保留（人による確認要）」とする。
    execution_metadata は省略時 unknown へ正規化し、欠測を 0 にしない。
    """
    val_errors = validate_reviewer_output(review_data, expected_sample_file=sample_name)
    if val_errors:
        raise ValueError(f"Cannot score invalid reviewer output: {'; '.join(val_errors)}")

    gt_defects = sample_meta.get("ground_truth_defects", [])
    findings = review_data.get("findings", [])

    matched_records = []
    duplicate_records = []
    pending_records = []
    unmatched_records = []
    gt_matched_map: dict[str, list[dict]] = {d["id"]: [] for d in gt_defects}

    # 各指摘について、どの正解欠陥に該当するか判定
    for f in findings:
        f_line = f["line"]
        f_cat = f["category"].lower()
        # 省略時は空文字として正規化（validate_reviewer_output により存在時は str が保証済み）
        _f_message = f.get("message", "")
        _f_rationale = f.get("rationale", "")

        assigned_gt = None
        exact_gt_matches = [gt for gt in gt_defects if gt["target_line"] == f_line]

        if exact_gt_matches:
            target_gt = exact_gt_matches[0]
            gt_cat = target_gt["category"].lower()
            if is_category_match(f_cat, gt_cat):
                assigned_gt = target_gt
            else:
                # 行番号は一致しているが正規カテゴリ・別名に不一致 -> 説明文の部分文字列では正解にせず保留
                pending_records.append({
                    "finding": f,
                    "candidate_gt": target_gt["id"],
                    "reason": (
                        f"Line {f_line} matches but category '{f_cat}' is not an exact or aliased match "
                        f"for '{gt_cat}'; requires human confirmation"
                    ),
                })
                assigned_gt = "PENDING"
        else:
            near_gts = [gt for gt in gt_defects if abs(f_line - gt["target_line"]) <= 2]
            if near_gts:
                pending_records.append({
                    "finding": f,
                    "candidate_gt": near_gts[0]["id"],
                    "reason": f"Line {f_line} is near GT line {near_gts[0]['target_line']} (within ±2 lines); requires human confirmation",
                })
                assigned_gt = "PENDING"

        if assigned_gt == "PENDING":
            continue
        elif assigned_gt is not None:
            gt_id = assigned_gt["id"]
            if len(gt_matched_map[gt_id]) == 0:
                gt_matched_map[gt_id].append(f)
                matched_records.append({
                    "ground_truth_id": gt_id,
                    "target_line": assigned_gt["target_line"],
                    "finding": f,
                })
            else:
                gt_matched_map[gt_id].append(f)
                duplicate_records.append({
                    "ground_truth_id": gt_id,
                    "target_line": assigned_gt["target_line"],
                    "duplicate_finding": f,
                })
        else:
            unmatched_records.append(f)

    # 見逃し（MISSED）の算出
    missed_records = [
        gt for gt in gt_defects if len(gt_matched_map[gt["id"]]) == 0
    ]

    # メタデータからの usage / latency / cost 抽出（省略・未取得時は unknown へ正規化、欠測を 0 にしない）
    raw_meta = review_data.get("execution_metadata")
    if not isinstance(raw_meta, dict):
        raw_meta = {}

    def normalize_metric(val):
        return val if val is not None else "unknown"

    observed_execution = {
        "model_id": normalize_metric(raw_meta.get("model_id")),
        "latency_sec": normalize_metric(raw_meta.get("latency_sec")),
        "input_tokens": normalize_metric(raw_meta.get("input_tokens")),
        "output_tokens": normalize_metric(raw_meta.get("output_tokens")),
        "cost_usd": normalize_metric(raw_meta.get("cost_usd")),
    }

    return {
        "sample_file": sample_name,
        "is_mock": True,
        "total_ground_truth_defects": len(gt_defects),
        "total_reviewer_findings": len(findings),
        "metrics": {
            "matched_defects": len(matched_records),
            "duplicate_findings": len(duplicate_records),
            "missed_defects": len(missed_records),
            "pending_human_review": len(pending_records),
            "unmatched_findings": len(unmatched_records),
            "human_verification_required": len(pending_records) > 0 or len(findings) > 0,
        },
        "observed_execution": observed_execution,
        "details": {
            "matched": matched_records,
            "duplicates": duplicate_records,
            "missed": missed_records,
            "pending": pending_records,
            "unmatched": unmatched_records,
        },
    }


def evaluate_mock_reviews(fixtures_dir: Path) -> dict:
    """
    mock_reviews ディレクトリ配下の模擬結果を取り込み、厳格検査・採点・集計する。
    不正入力は検査エラーとして採点から除外する。
    """
    manifest_path = fixtures_dir / "synthetic_samples_manifest.json"
    manifest = load_manifest(manifest_path)
    mock_dir = fixtures_dir / "mock_reviews"

    mock_map = {
        "clean_refactor.patch": {
            "path": mock_dir / "mock_review_clean.json",
            "target_file": "app/service/data_processor.py",
        },
        "defect_seeded.patch": {
            "path": mock_dir / "mock_review_defect.json",
            "target_file": "app/service/file_handler.py",
        },
    }

    scoring_results = []
    errors = []

    for sample_name, spec in mock_map.items():
        mock_path = spec["path"]
        target_file = spec["target_file"]

        if not mock_path.exists():
            errors.append(f"Mock review file missing: {mock_path.name}")
            continue

        try:
            review_data = json.loads(mock_path.read_text(encoding="utf-8"))
            val_errors = validate_reviewer_output(
                review_data,
                expected_sample_file=sample_name,
                expected_target_file=target_file,
            )
            if val_errors:
                errors.extend([f"{mock_path.name}: {ve}" for ve in val_errors])
                continue

            sample_meta = manifest.get("samples", {}).get(sample_name, {})
            score = score_review_findings(sample_name, review_data, sample_meta)
            scoring_results.append(score)
        except Exception as e:
            errors.append(f"{mock_path.name} failed to process: {e}")

    passed = (len(errors) == 0) and (len(scoring_results) == len(mock_map))

    return {
        "evaluation_type": "OFFLINE_MOCK_SCORING",
        "mock_disclaimer": "This report evaluates MOCK fixtures only to verify scoring and ingestion algorithms. Does NOT measure real AI model quality.",
        "status": "PASSED" if passed else "FAILED",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "errors": errors,
        "scoring_results": scoring_results,
    }


def evaluate_dry_run(fixtures_dir: Path) -> dict:
    manifest_path = fixtures_dir / "synthetic_samples_manifest.json"
    manifest = load_manifest(manifest_path)

    results = []
    errors = []
    samples = manifest.get("samples", {})
    if not samples:
        errors.append("Manifest contains zero samples")

    for sample_name, meta in samples.items():
        sample_path = fixtures_dir / sample_name
        try:
            patch_info = parse_patch_summary(sample_path)
            payload = build_ocr_simulation_payload(patch_info)

            sample_eval = {
                "sample_file": sample_name,
                "sample_type": meta.get("type"),
                "target_files": patch_info["targets"],
                "additions": patch_info["additions"],
                "deletions": patch_info["deletions"],
                "ground_truth_expected_defects": meta.get("expected_defects_count", 0),
                "payload_ready": True,
                "ground_truth_excluded_from_input": True,
                "estimated_prompt_tokens": payload["estimated_prompt_tokens"],
                "live_api_called": False,
                "metrics": {
                    "actionable_findings": "PENDING_LIVE_EVAL",
                    "false_positives": "PENDING_LIVE_EVAL",
                    "missed_defects": "PENDING_LIVE_EVAL",
                    "latency_sec": 0.0,
                    "input_tokens": payload["estimated_prompt_tokens"],
                    "output_tokens": 0,
                    "actual_cost_usd": "UNKNOWN",
                },
            }
            results.append(sample_eval)
        except Exception as e:
            errors.append(f"Sample '{sample_name}' failed validation: {e}")

    passed = (len(errors) == 0) and (len(results) > 0)

    # 模擬結果の受入れ・採点も同時に実行
    mock_eval = evaluate_mock_reviews(fixtures_dir)

    return {
        "evaluation_phase": "P3_SYNTHETIC_PREPARATION_DRY_RUN",
        "ocr_tool_integration_status": "NOT_INTEGRATED (Input preparation and simulation only)",
        "api_authorized": False,
        "status": "PASSED" if (passed and mock_eval["status"] == "PASSED") else "FAILED",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "samples_evaluated": len(results),
        "errors": errors + mock_eval.get("errors", []),
        "results": results,
        "mock_evaluation": mock_eval,
        "unimplemented_items": [
            "Alibaba OCR fixed version pinning and CLI binary installation",
            "Standalone MiMo API live network connection",
            "Hardware-enforced API billing/token budget ceiling (requires external proxy/credential limits)",
        ],
        "execution_proposal": {
            "required_authorization": "User explicit approval required before live API invocation",
            "target_model": "mimo-v2.6-pro (or authorized OpenAI-compatible MiMo endpoint)",
            "bounds": {
                "max_calls": len(results),
                "max_input_tokens_per_call": 2048,
                "max_output_tokens_per_call": 1024,
                "timeout_sec": 30,
                "cost_ceiling_usd": 0.10,
            },
            "security_guards": [
                "Strictly synthetic patches only; zero private codebase exposure",
                "Ground truth metadata strictly excluded from reviewer input",
                "No API key values printed, logged, or committed",
                "Standalone review path separated from Codex delegation quota",
            ],
        },
    }


def main():
    parser = argparse.ArgumentParser(description="P3 Synthetic Samples, Input Preparation & Mock Scoring Runner")
    parser.add_argument("--authorize-live-call", action="store_true", help="Authorize actual MiMo API invocation (requires prior explicit approval)")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    parser.add_argument("--score-mock-only", action="store_true", help="Only run mock scoring verification")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    fixtures_dir = repo_root / "tests" / "fixtures" / "synthetic_samples"

    if args.authorize_live_call:
        print("[ABORTED] Live API calls are NOT authorized in this phase. Run in dry-run mode.", file=sys.stderr)
        sys.exit(1)

    if args.score_mock_only:
        mock_eval = evaluate_mock_reviews(fixtures_dir)
        if args.json:
            print(json.dumps(mock_eval, indent=2, ensure_ascii=False))
        else:
            print(f"=== P3 Mock Scoring Verification: {mock_eval['status']} ===")
            print(f"Note: {mock_eval['mock_disclaimer']}\n")
            for res in mock_eval["scoring_results"]:
                print(f"- Sample: {res['sample_file']} (GT: {res['total_ground_truth_defects']}, Findings: {res['total_reviewer_findings']})")
                m = res["metrics"]
                print(f"  Matched: {m['matched_defects']}, Duplicates: {m['duplicate_findings']}, Missed: {m['missed_defects']}")
                print(f"  Pending Human Review: {m['pending_human_review']}, Unmatched: {m['unmatched_findings']}")
                print(f"  Human Verification Required: {m['human_verification_required']}")
                print(f"  Usage: tokens={res['observed_execution']['input_tokens']}/{res['observed_execution']['output_tokens']}, cost={res['observed_execution']['cost_usd']}, latency={res['observed_execution']['latency_sec']}")
        sys.exit(0 if mock_eval["status"] == "PASSED" else 1)

    eval_result = evaluate_dry_run(fixtures_dir)

    if args.json:
        print(json.dumps(eval_result, indent=2, ensure_ascii=False))
    else:
        print("=== P3 Synthetic Samples & Input Preparation (Dry-run) ===")
        print(f"Status: {eval_result['status']}")
        print(f"OCR Tool Status: {eval_result['ocr_tool_integration_status']}")
        print(f"Timestamp: {eval_result['timestamp']}")
        print(f"Samples Prepared: {eval_result['samples_evaluated']}")
        if eval_result["errors"]:
            print("Errors:")
            for err in eval_result["errors"]:
                print(f"  - {err}")
        for res in eval_result["results"]:
            print(f"\n- Sample: {res['sample_file']} ({res['sample_type']})")
            print(f"  Target: {', '.join(res['target_files'])}")
            print(f"  Diff Size: +{res['additions']} / -{res['deletions']} lines")
            print(f"  Ground Truth Excluded From Input: {res['ground_truth_excluded_from_input']}")
            print(f"  Expected Defects (Ground Truth): {res['ground_truth_expected_defects']}")
            print(f"  Estimated Prompt Tokens: ~{res['estimated_prompt_tokens']}")
            print(f"  Live API Called: {res['live_api_called']}")

        print("\n=== Offline Mock Review Scoring Results (Simulated) ===")
        mock_eval = eval_result.get("mock_evaluation", {})
        print(f"Mock Scoring Status: {mock_eval.get('status')}")
        print(f"Note: {mock_eval.get('mock_disclaimer')}")
        for res in mock_eval.get("scoring_results", []):
            print(f"\n  * {res['sample_file']}:")
            m = res["metrics"]
            print(f"    - Ground Truth: {res['total_ground_truth_defects']}, Reviewer Findings: {res['total_reviewer_findings']}")
            print(f"    - Matched Defects:    {m['matched_defects']}")
            print(f"    - Duplicate Findings: {m['duplicate_findings']}")
            print(f"    - Missed Defects:     {m['missed_defects']}")
            print(f"    - Pending Human Review: {m['pending_human_review']}")
            print(f"    - Unmatched:          {m['unmatched_findings']}")
            print(f"    - Human Verification Required: {m['human_verification_required']}")
            print(f"    - Execution Metrics:  tokens={res['observed_execution']['input_tokens']}, cost={res['observed_execution']['cost_usd']}, latency={res['observed_execution']['latency_sec']}")

        print("\n--- Unimplemented Items (Explicitly Left for Future) ---")
        for item in eval_result["unimplemented_items"]:
            print(f"  - {item}")

        prop = eval_result["execution_proposal"]
        print("\n--- Live Test Execution Proposal (Waiting for Approval) ---")
        print(f"Model ID:        {prop['target_model']}")
        print(f"Max Calls:       {prop['bounds']['max_calls']}")
        print(f"Max In/Out:      {prop['bounds']['max_input_tokens_per_call']} / {prop['bounds']['max_output_tokens_per_call']} tokens")
        print(f"Cost Ceiling:    ${prop['bounds']['cost_ceiling_usd']} USD")
        print(f"Timeout:         {prop['bounds']['timeout_sec']}s")
        print("Security:        Synthetic patches only, Ground truth excluded, No secrets logged, Standalone path")

    sys.exit(0 if eval_result["status"] == "PASSED" else 1)


if __name__ == "__main__":
    main()
