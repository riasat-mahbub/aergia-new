#!/usr/bin/env python3
"""Score GLiNER candidate discovery against a source-unit oracle."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _key(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9+#./]+", value.casefold()))


def _nonspace_coverage(span: dict[str, Any], source_text: str, unit_start: int, unit_end: int) -> float:
    left = max(span["start"], unit_start)
    right = min(span["end"], unit_end)
    if right <= left:
        return 0.0
    target = source_text[unit_start:unit_end]
    matched = source_text[left:right]
    denominator = sum(not char.isspace() for char in target)
    numerator = sum(not char.isspace() for char in matched)
    return numerator / denominator if denominator else 0.0


def _metrics(gold: list[dict[str, Any]], predicted: list[dict[str, Any]]) -> dict[str, Any]:
    gold_by_text = {_key(row["source_text"]): row for row in gold}
    pred_by_text = {_key(row["source"]["original_text"]): row for row in predicted}
    gold_keys = set(gold_by_text)
    pred_keys = set(pred_by_text)
    matched = gold_keys & pred_keys
    duplicates = sum(count - 1 for count in Counter(_key(row["source"]["original_text"]) for row in predicted).values() if count > 1)
    by_difficulty = {}
    for difficulty in sorted({row.get("difficulty", "unrated") for row in gold}):
        bucket = [row for row in gold if row.get("difficulty", "unrated") == difficulty]
        bucket_keys = {_key(row["source_text"]) for row in bucket}
        by_difficulty[difficulty] = {
            "gold_units": len(bucket),
            "discovered": len(bucket_keys & pred_keys),
            "recall": round(len(bucket_keys & pred_keys) / len(bucket_keys), 4) if bucket_keys else None,
        }
    return {
        "gold_units": len(gold),
        "predicted_units": len(predicted),
        "exact_source_unit_recall": round(len(matched) / len(gold_keys), 4) if gold_keys else None,
        "exact_source_unit_precision": round(len(matched) / len(pred_keys), 4) if pred_keys else None,
        "matched_units": len(matched),
        "missed_gold_ids": [gold_by_text[key]["id"] for key in sorted(gold_keys - pred_keys)],
        "extra_prediction_texts": [pred_by_text[key]["source"]["original_text"] for key in sorted(pred_keys - gold_keys)],
        "duplicate_prediction_count": duplicates,
        "recall_by_difficulty": by_difficulty,
        "importance_accuracy_on_matches": round(
            sum(gold_by_text[key]["importance"] == pred_by_text[key]["importance"] for key in matched) / len(matched), 4
        ) if matched else None,
        "family_accuracy_on_matches": round(
            sum(gold_by_text[key]["family"] == pred_by_text[key]["family"] for key in matched) / len(matched), 4
        ) if matched else None,
    }


def _structure_checks(checks: list[dict[str, Any]], gold: list[dict[str, Any]], predicted: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gold_by_id = {row["id"]: row for row in gold}
    predicted_by_text = {_key(row["source"]["original_text"]): row for row in predicted}
    results = []
    for check in checks:
        expected = gold_by_id[check["requirement_id"]]
        actual = predicted_by_text.get(_key(expected["source_text"]))
        entry: dict[str, Any] = {"requirement_id": check["requirement_id"], "found": actual is not None}
        if actual is None:
            results.append(entry)
            continue

        expression = actual["expression"]
        concepts: list[str] = []
        nodes: list[dict[str, Any]] = []
        constraints: list[dict[str, Any]] = []

        def visit(node: Any) -> None:
            if not isinstance(node, dict):
                return
            if isinstance(node.get("kind"), str):
                nodes.append(node)
            concept = node.get("concept")
            if isinstance(concept, dict) and isinstance(concept.get("name"), str):
                concepts.append(concept["name"])
            if isinstance(node.get("constraints"), list):
                constraints.extend(item for item in node["constraints"] if isinstance(item, dict))
            for child in node.get("children", []):
                visit(child)

        visit(expression)
        actual_terms = " ".join(_key(item) for item in concepts)
        if "root_kind" in check:
            entry["root_kind"] = expression.get("kind")
            entry["root_kind_match"] = expression.get("kind") == check["root_kind"]
        if "nested_any_min_children" in check:
            entry["nested_any_min_children"] = check["nested_any_min_children"]
            entry["nested_any_present"] = any(
                node is not expression
                and node.get("kind") == "any"
                and len(node.get("children", [])) >= check["nested_any_min_children"]
                for node in nodes
            )
        if "concept_terms" in check:
            found = [term for term in check["concept_terms"] if _key(term) in actual_terms]
            entry["concept_terms_found"] = found
            entry["concept_terms_missing"] = [term for term in check["concept_terms"] if term not in found]
            entry["concept_term_recall"] = round(len(found) / len(check["concept_terms"]), 4)
        if "experience_duration" in check:
            expected_duration = check["experience_duration"]
            duration_matches = []
            for constraint in constraints:
                if constraint.get("kind") != "experience_duration":
                    continue
                sources = constraint.get("allowed_evidence_sources", [])
                valid = (
                    constraint.get("min_years") == expected_duration["min_years"]
                    and constraint.get("max_years") == expected_duration["max_years"]
                    and constraint.get("approximate") is expected_duration["approximate"]
                    and set(sources) == set(expected_duration["allowed_evidence_sources"])
                )
                duration_matches.append(valid)
            entry["duration_constraint_count"] = len(duration_matches)
            entry["duration_constraint_match_count"] = sum(duration_matches)
            entry["duration_constraint_present"] = any(duration_matches)
            entry["duplicate_duration_constraints"] = max(0, len(duration_matches) - 1)
        results.append(entry)
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--oracle", required=True, type=Path)
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument(
        "--corpus",
        type=Path,
        default=Path(__file__).resolve().parent / "corpus/real-jds-v1.jsonl",
    )
    args = parser.parse_args()

    oracle = json.loads(args.oracle.read_text(encoding="utf-8"))
    prediction = next((row for row in _read_jsonl(args.predictions) if row["case_id"] == oracle["case_id"]), None)
    if prediction is None:
        raise SystemExit(f"No prediction for oracle case {oracle['case_id']}")

    corpus_record = next((row for row in _read_jsonl(args.corpus) if row["case_id"] == oracle["case_id"]), None)
    if corpus_record is None:
        raise SystemExit(f"No corpus record for oracle case {oracle['case_id']}")
    source = corpus_record["text"]
    if corpus_record["sha256"] != oracle["source_sha256"]:
        raise SystemExit("Oracle source hash does not match the frozen corpus")
    if prediction["source_sha256"] != oracle["source_sha256"]:
        raise SystemExit("Prediction source hash does not match the frozen corpus")
    gold = oracle["requirements"]
    raw = prediction["raw_spans"]
    spans_for_discovery = [span for span in raw if span["label"] == "candidate_requirement"]
    discovery_hits = 0
    cue_hits = 0
    for requirement in gold:
        start = source.find(requirement["source_text"])
        if start < 0:
            raise SystemExit(f"Gold source text does not occur in frozen source: {requirement['id']}")
        end = start + len(requirement["source_text"])
        if any(_nonspace_coverage(span, source, start, end) > 0.0 for span in raw):
            cue_hits += 1
        if any(_nonspace_coverage(span, source, start, end) >= 0.5 for span in spans_for_discovery):
            discovery_hits += 1

    final = prediction["requirements"].get("requirements", [])
    result = {
        "model_run": args.predictions.parent.name,
        "case_id": oracle["case_id"],
        "oracle_audit_status": oracle["audit_status"],
        "raw_model_candidate_requirement": {
            "span_count": len(spans_for_discovery),
            "source_unit_recall_at_half_coverage": round(discovery_hits / len(gold), 4) if gold else None,
            "covered_gold_units": discovery_hits,
            "total_gold_units": len(gold),
            "any_label_overlap_cue_units": cue_hits,
        },
        "aergia_final": _metrics(gold, final),
        "structured_interpretation_checks": _structure_checks(oracle.get("structure_checks", []), gold, final),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
