#!/usr/bin/env python3
"""Offline human adjudication of a completed live synthetic-review receipt."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re

import ocr_mimo_connection as connection
import ocr_mimo_review as review

MAX_FILE_BYTES = 1048576
PATCHES = {"clean": "clean_refactor.patch", "defect": "defect_seeded.patch"}


def require(condition):
    if not condition:
        raise ValueError("invalid or mismatched adjudication evidence")


def read_json(path):
    with path.open("rb") as stream:
        raw = stream.read(MAX_FILE_BYTES + 1)
    require(len(raw) <= MAX_FILE_BYTES)
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def fixture_context():
    manifest, digest = read_json(review.FIXTURES / "synthetic_samples_manifest.json")
    # Bind to the source pairs as well as GT, without sending either anywhere.
    sources = {}
    for sample, target in review.SAMPLES.items():
        for stage in ("before", "after"):
            raw = (review.FIXTURES / "sources" / sample / stage / target).read_bytes()
            sources[f"{sample}/{stage}"] = hashlib.sha256(raw).hexdigest()
    return manifest, {"manifest_sha256": digest, "source_sha256": sources}


def prepare(receipt_path):
    data, receipt_hash = read_json(receipt_path)
    require(isinstance(data, dict))
    require(data.get("schema_version") == "1.0" and data.get("mode") == "live"
            and data.get("status") == "LIVE_REVIEW_COMPLETED"
            and data.get("review_quality_accepted") is False
            and data.get("requested_model") == connection.MODEL
            and data.get("ocr_version") == connection.VERSION
            and data.get("ocr_source_commit") == connection.SOURCE_COMMIT
            and data.get("binary_sha256") in connection.BINARY_HASHES)
    attempts, completed = data.get("http_attempts"), data.get("completed_responses")
    require(type(attempts) is int and type(completed) is int
            and 2 <= completed == attempts <= review.MAX_CALLS)
    require(data.get("limits") == {
        "http_attempts_total": review.MAX_CALLS, "request_bytes": review.MAX_BYTES,
        "output_tokens_per_request": review.MAX_OUTPUT,
        "request_timeout_seconds": connection.REQUEST_TIMEOUT})
    results = data.get("results")
    require(isinstance(results, list) and len(results) == 2)
    require(all(isinstance(r, dict) for r in results))
    require([r.get("sample") for r in results] == list(review.SAMPLES))
    manifest, fixtures = fixture_context()
    samples = []
    for result in results:
        sample = result["sample"]
        target = review.SAMPLES[sample]
        require(result.get("status") == "REVIEW_COMPLETED"
                and type(result.get("cli_exit_code")) is int and result["cli_exit_code"] == 0)
        require(isinstance(result.get("diff_sha256"), str)
                and re.fullmatch("[0-9a-f]{64}", result["diff_sha256"]) is not None)
        findings = result.get("findings")
        require(isinstance(findings, list) and len(findings) <= 100
                and type(result.get("findings_count")) is int
                and result["findings_count"] == len(findings)
                and all(isinstance(f, dict) for f in findings))
        line_count = len((review.FIXTURES / "sources" / sample / "after" / target)
                         .read_text().splitlines())
        # Reuse current-run output validation; preserve original coarse categories.
        review.ingest({"status": "complete", "llm": {"model": connection.MODEL},
                       "summary": {"files_reviewed": 1}, "comments": findings},
                      target, line_count)
        gt = manifest["samples"][PATCHES[sample]].get("ground_truth_defects", [])
        samples.append({
            "sample": sample, "target": target, "diff_sha256": result["diff_sha256"],
            "ground_truth": gt,
            "findings": [{"id": f"{sample}:{i}", "finding": finding,
                          "decision": "pending", "ground_truth_ids": [], "rationale": ""}
                         for i, finding in enumerate(findings, 1)],
        })
    return {"schema_version": "1.0", "receipt_sha256": receipt_hash,
            "fixtures": fixtures, "samples": samples,
            "human_review_completed": False, "completion_rationale": ""}


def summarize(receipt_path, packet):
    expected = prepare(receipt_path)
    require(isinstance(packet, dict) and set(packet) == set(expected))
    require(type(packet["human_review_completed"]) is bool
            and isinstance(packet["completion_rationale"], str)
            and len(packet["completion_rationale"]) <= 4000)
    require(isinstance(packet["samples"], list) and len(packet["samples"]) == 2)
    # Only decision/rationale fields may change. Everything else is rebound.
    immutable = json.loads(json.dumps(packet))
    pending = 0
    metrics = []
    for actual, baseline, frozen in zip(packet["samples"], expected["samples"],
                                        immutable["samples"]):
        require(isinstance(actual, dict) and set(actual) == set(baseline))
        require(isinstance(actual["findings"], list)
                and len(actual["findings"]) == len(baseline["findings"]))
        counts = {gt["id"]: 0 for gt in baseline["ground_truth"]}
        false_positives = other_valid = sample_pending = 0
        for finding, original, locked in zip(actual["findings"], baseline["findings"],
                                              frozen["findings"]):
            require(isinstance(finding, dict) and set(finding) == set(original))
            decision, ids, rationale = (finding["decision"], finding["ground_truth_ids"],
                                        finding["rationale"])
            require(decision in ("pending", "confirmed", "false_positive", "other_valid"))
            require(isinstance(ids, list) and all(isinstance(i, str) for i in ids)
                    and len(ids) == len(set(ids)) and all(i in counts for i in ids))
            require(isinstance(rationale, str) and len(rationale) <= 4000)
            require(bool(ids) == (decision == "confirmed"))
            require(decision == "pending" or bool(rationale.strip()))
            if decision == "pending":
                sample_pending += 1
            elif decision == "confirmed":
                for gt_id in ids:
                    counts[gt_id] += 1
            elif decision == "false_positive":
                false_positives += 1
            else:
                other_valid += 1
            for key in ("decision", "ground_truth_ids", "rationale"):
                locked[key] = original[key]
        pending += sample_pending
        metrics.append({"sample": baseline["sample"],
                        "confirmed_defects": [k for k, v in counts.items() if v],
                        "unconfirmed_defects": [k for k, v in counts.items() if not v],
                        "duplicate_defect_links": sum(max(0, v - 1) for v in counts.values()),
                        "false_positive_findings": false_positives,
                        "other_valid_findings": other_valid,
                        "pending_findings": sample_pending})
    immutable["human_review_completed"] = False
    immutable["completion_rationale"] = ""
    require(immutable == expected)
    complete = packet["human_review_completed"] and pending == 0
    require(not packet["human_review_completed"] or bool(packet["completion_rationale"].strip()))
    for metric in metrics:
        metric["missed_defects"] = (metric["unconfirmed_defects"] if complete
                                    else "PENDING_HUMAN_REVIEW")
    return {"schema_version": "1.0",
            "status": "HUMAN_ADJUDICATED" if complete else "PENDING_HUMAN_REVIEW",
            "receipt_sha256": expected["receipt_sha256"],
            "decision_sha256": hashlib.sha256(json.dumps(
                packet, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
            "evidence_origin": "operator_supplied_receipt_not_authenticated",
            "external_requests": 0, "review_quality_accepted": False,
            "fine_category_matches": "NOT_SCORED",
            "cost_acceptance": "NOT_EVALUATED", "metrics": metrics}


def write_private(path, data):
    # Exclusive destination; no arbitrary model content on stdout.
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600),
                   "w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--decisions", type=Path, help="omit to prepare a new decision packet")
    parser.add_argument("--output", required=True, type=Path, help="new private file")
    args = parser.parse_args()
    try:
        if args.decisions:
            packet, _ = read_json(args.decisions)
            report = summarize(args.receipt, packet)
        else:
            report = prepare(args.receipt)
        write_private(args.output, report)
        print(json.dumps({"status": report.get("status", "DECISIONS_PREPARED"),
                          "external_requests": 0, "review_quality_accepted": False}))
        return 0
    except (ValueError, OSError, KeyError, TypeError, AttributeError):
        print('{"status":"REJECTED","external_requests":0,"review_quality_accepted":false}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
