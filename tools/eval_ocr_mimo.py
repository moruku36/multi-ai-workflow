#!/usr/bin/env python3
"""
tools/eval_ocr_mimo.py

P3 Alibaba Open Code Review (OCR) + MiMo API 単独評価用ツール。
デフォルトは完全オフライン (dry-run) で動作し、外部APIを一切呼び出さない。
合成パッチのパース、OCRプロンプト構築、Ground Truthとの突合フレームワークを提供する。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


def load_manifest(manifest_path: Path) -> dict:
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_patch_summary(patch_path: Path) -> dict:
    content = patch_path.read_text(encoding="utf-8")
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
    Alibaba OCR standalone + MiMo API (OpenAI互換) 形式のプロンプト/ペイロードを生成。
    実際の通信は行わず、ペイロードの正当性・トークン見積もり用。
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

    # 簡易トークン概算（英数字約4文字=1トークン換算の参考値、実環境保証ではない）
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


def evaluate_dry_run(fixtures_dir: Path) -> dict:
    manifest_path = fixtures_dir / "synthetic_samples_manifest.json"
    manifest = load_manifest(manifest_path)

    results = []
    for sample_name, meta in manifest.get("samples", {}).items():
        sample_path = fixtures_dir / sample_name
        if not sample_path.exists():
            continue

        patch_info = parse_patch_summary(sample_path)
        payload = build_ocr_simulation_payload(patch_info)

        # dry-run 評価記録
        sample_eval = {
            "sample_file": sample_name,
            "sample_type": meta.get("type"),
            "target_files": patch_info["targets"],
            "additions": patch_info["additions"],
            "deletions": patch_info["deletions"],
            "ground_truth_expected_defects": meta.get("expected_defects_count", 0),
            "payload_ready": True,
            "estimated_prompt_tokens": payload["estimated_prompt_tokens"],
            "live_api_called": False,
            "simulated_findings": [],
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

    return {
        "evaluation_phase": "P3_STANDALONE_EVALUATION_DRY_RUN",
        "api_authorized": False,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "samples_evaluated": len(results),
        "results": results,
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
                "No live private repository code sent; only synthetic patches used",
                "No API key values printed, logged, or committed",
                "Standalone review path separated from Codex delegation quota",
            ],
        },
    }


def main():
    parser = argparse.ArgumentParser(description="P3 OCR + MiMo Evaluation Runner (Dry-run by default)")
    parser.add_argument("--authorize-live-call", action="store_true", help="Authorize actual MiMo API invocation (requires prior explicit approval)")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    fixtures_dir = repo_root / "tests" / "fixtures" / "synthetic_samples"

    if args.authorize_live_call:
        print("[ABORTED] Live API calls are NOT authorized in this phase. Run in dry-run mode.", file=sys.stderr)
        sys.exit(1)

    eval_result = evaluate_dry_run(fixtures_dir)

    if args.json:
        print(json.dumps(eval_result, indent=2, ensure_ascii=False))
    else:
        print("=== P3 Alibaba OCR + MiMo API Evaluation Setup (Dry-run) ===")
        print(f"Timestamp: {eval_result['timestamp']}")
        print(f"Samples Prepared: {eval_result['samples_evaluated']}")
        for res in eval_result["results"]:
            print(f"\n- Sample: {res['sample_file']} ({res['sample_type']})")
            print(f"  Target: {', '.join(res['target_files'])}")
            print(f"  Diff Size: +{res['additions']} / -{res['deletions']} lines")
            print(f"  Expected Defects (Ground Truth): {res['ground_truth_expected_defects']}")
            print(f"  Estimated Prompt Tokens: ~{res['estimated_prompt_tokens']}")
            print(f"  Live API Called: {res['live_api_called']}")

        prop = eval_result["execution_proposal"]
        print("\n--- Live Test Execution Proposal (Waiting for Approval) ---")
        print(f"Model ID:        {prop['target_model']}")
        print(f"Max Calls:       {prop['bounds']['max_calls']}")
        print(f"Max In/Out:      {prop['bounds']['max_input_tokens_per_call']} / {prop['bounds']['max_output_tokens_per_call']} tokens")
        print(f"Cost Ceiling:    ${prop['bounds']['cost_ceiling_usd']} USD")
        print(f"Timeout:         {prop['bounds']['timeout_sec']}s")
        print("Security:        Synthetic patches only, No secrets logged, Standalone path")

    sys.exit(0)


if __name__ == "__main__":
    main()
