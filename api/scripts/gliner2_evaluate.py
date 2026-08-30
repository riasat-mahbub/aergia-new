"""Evaluate the production GLiNER2.5-small extractor on annotated postings.

The fixture file is intentionally supplied by the operator so real job
descriptions and annotations do not need to be committed to the repository.
Each case has ``id``, ``text``, optional ``role``, ``expected`` annotations,
and optional ``forbidden`` anchors. An expected item may contain ``anchor``,
``importance``, ``concepts``, and ``constraint`` (with ``kind`` and optional
``value``).
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import resource
import sys
import time
from pathlib import Path
from typing import Any

from app.services.relevance import extract_requirements_v2
from app.services.requirement_extractor import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_GLINER2_REVISION,
    ExtractionResult,
    Gliner2RequirementExtractor,
    Requirement,
)


def _normalise(value: str) -> str:
    return " ".join(value.casefold().split())


def _word_count(value: str) -> int:
    return len(re.findall(r"\S+", value))


def _current_rss_bytes() -> int | None:
    try:
        pages = int(Path("/proc/self/statm").read_text(encoding="ascii").split()[1])
        return pages * os.sysconf("SC_PAGE_SIZE")
    except (FileNotFoundError, IndexError, OSError, ValueError):
        return None


def _peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def _cpu_seconds() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return float(usage.ru_utime + usage.ru_stime)


def _timed(call: Any) -> tuple[Any, dict[str, Any]]:
    rss_before = _current_rss_bytes()
    peak_before = _peak_rss_bytes()
    cpu_before = _cpu_seconds()
    started = time.perf_counter()
    value = call()
    elapsed = time.perf_counter() - started
    cpu = _cpu_seconds() - cpu_before
    peak_after = _peak_rss_bytes()
    return value, {
        "wall_seconds": round(elapsed, 4),
        "cpu_seconds": round(cpu, 4),
        "cpu_utilization_percent": round(cpu / elapsed * 100.0, 2) if elapsed else 0.0,
        "rss_before_bytes": rss_before,
        "rss_after_bytes": _current_rss_bytes(),
        "peak_rss_bytes": peak_after,
        "peak_rss_delta_bytes": peak_after - peak_before,
    }


def _requirement_payload(requirement: Requirement) -> dict[str, Any]:
    return {
        "id": requirement.id,
        "source_text": requirement.source_text,
        "source_start": requirement.source_start,
        "source_end": requirement.source_end,
        "type": requirement.type,
        "importance": requirement.importance.value,
        "concepts": list(requirement.concepts),
        "constraints": [
            {"kind": item.kind, "value": item.value, "source_text": item.source_text}
            for item in requirement.constraints
        ],
        "confidence": requirement.confidence,
    }


def _span_overlap(source: str, anchor: str, requirement: Requirement) -> int:
    anchor_start = source.casefold().find(anchor.casefold())
    if anchor_start < 0 or requirement.source_start is None or requirement.source_end is None:
        return 0
    anchor_end = anchor_start + len(anchor)
    return max(0, min(anchor_end, requirement.source_end) - max(anchor_start, requirement.source_start))


def _match_score(source: str, expected: dict[str, Any], requirement: Requirement) -> int:
    anchor = str(expected.get("anchor", "")).strip()
    if not anchor:
        return 0
    score = 0
    if anchor.casefold() in requirement.source_text.casefold():
        score = max(score, 3)
    if _span_overlap(source, anchor, requirement):
        score = max(score, 2)
    expected_concepts = {_normalise(str(value)) for value in expected.get("concepts", [])}
    predicted_concepts = {_normalise(value) for value in requirement.concepts}
    if expected_concepts & predicted_concepts:
        score = max(score, 1)
    return score


def _constraint_matches(expected: dict[str, Any], requirement: Requirement) -> bool:
    wanted = expected.get("constraint")
    if not wanted:
        return True
    if not isinstance(wanted, dict):
        return False
    for constraint in requirement.constraints:
        if constraint.kind != wanted.get("kind"):
            continue
        if "value" not in wanted or wanted["value"] is None:
            return True
        if constraint.value == wanted["value"]:
            return True
    return False


def _evaluate_case(case: dict[str, Any], result: ExtractionResult) -> dict[str, Any]:
    source = str(case["text"])
    expected = [item for item in case.get("expected", []) if isinstance(item, dict)]
    predicted = list(result.requirements)
    scores = [
        [_match_score(source, item, requirement) for requirement in predicted]
        for item in expected
    ]
    matched_expected: set[int] = set()
    matched_predicted: set[int] = set()
    pairs: list[tuple[int, int]] = []
    ranked = sorted(
        (
            (score, expected_index, predicted_index)
            for expected_index, row in enumerate(scores)
            for predicted_index, score in enumerate(row)
            if score
        ),
        reverse=True,
    )
    for _score, expected_index, predicted_index in ranked:
        if expected_index in matched_expected or predicted_index in matched_predicted:
            continue
        matched_expected.add(expected_index)
        matched_predicted.add(predicted_index)
        pairs.append((expected_index, predicted_index))

    false_required: list[dict[str, Any]] = []
    for raw_forbidden in case.get("forbidden", []):
        forbidden = raw_forbidden if isinstance(raw_forbidden, dict) else {"anchor": raw_forbidden}
        anchor = str(forbidden.get("anchor", "")).strip()
        for requirement in predicted:
            if requirement.importance.value != "required":
                continue
            if anchor.casefold() in requirement.source_text.casefold() or _span_overlap(source, anchor, requirement):
                false_required.append({"anchor": anchor, "prediction": _requirement_payload(requirement)})

    importance_pairs = [(expected[index], predicted[predicted_index]) for index, predicted_index in pairs if expected[index].get("importance")]
    constraint_pairs = [(expected[index], predicted[predicted_index]) for index, predicted_index in pairs if expected[index].get("constraint")]
    split_count = sum(sum(score > 0 for score in row) > 1 for row in scores)
    merge_count = sum(
        sum(scores[expected_index][predicted_index] > 0 for expected_index in range(len(expected))) > 1
        for predicted_index in range(len(predicted))
    )
    return {
        "gold_count": len(expected),
        "predicted_count": len(predicted),
        "matched_count": len(pairs),
        "precision": len(pairs) / len(predicted) if predicted else 0.0,
        "recall": len(pairs) / len(expected) if expected else 0.0,
        "importance_accuracy": (
            sum(item[1].importance.value == item[0]["importance"] for item in importance_pairs) / len(importance_pairs)
            if importance_pairs
            else None
        ),
        "constraint_accuracy": (
            sum(_constraint_matches(item[0], item[1]) for item in constraint_pairs) / len(constraint_pairs)
            if constraint_pairs
            else None
        ),
        "false_required_count": len(false_required),
        "false_required": false_required,
        "split_count": split_count,
        "merge_count": merge_count,
        "missing": [expected[index] for index in range(len(expected)) if index not in matched_expected],
        "invented": [
            _requirement_payload(predicted[index])
            for index in range(len(predicted))
            if index not in matched_predicted
        ],
    }


def _aggregate(evaluations: list[dict[str, Any]]) -> dict[str, Any]:
    gold = sum(item["gold_count"] for item in evaluations)
    predicted = sum(item["predicted_count"] for item in evaluations)
    matched = sum(item["matched_count"] for item in evaluations)
    importance = [item["importance_accuracy"] for item in evaluations if item["importance_accuracy"] is not None]
    constraints = [item["constraint_accuracy"] for item in evaluations if item["constraint_accuracy"] is not None]
    return {
        "cases": len(evaluations),
        "gold_count": gold,
        "predicted_count": predicted,
        "matched_count": matched,
        "precision": matched / predicted if predicted else 0.0,
        "recall": matched / gold if gold else 0.0,
        "importance_accuracy": sum(importance) / len(importance) if importance else None,
        "constraint_accuracy": sum(constraints) / len(constraints) if constraints else None,
        "false_required_count": sum(item["false_required_count"] for item in evaluations),
        "split_count": sum(item["split_count"] for item in evaluations),
        "merge_count": sum(item["merge_count"] for item in evaluations),
    }


def _baseline(case: dict[str, Any]) -> dict[str, Any]:
    try:
        requirements = extract_requirements_v2(str(case.get("role", "")), str(case["text"]))
    except Exception as exc:  # noqa: BLE001 - comparison report records fixture failures
        return {"error": f"{type(exc).__name__}: {exc}"}
    return {
        "requirements": [
            {
                "text": item.text,
                "canonical": item.canonical,
                "type": item.type,
                "required": item.required,
                "constraint": item.constraint,
            }
            for item in requirements
        ]
    }


def _read_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("fixture root must be a list")
    raw_cases = [dict(raw) for raw in payload if isinstance(raw, dict)]
    by_id = {str(case.get("id")): case for case in raw_cases}
    cases = []
    for raw in raw_cases:
        if "repeat_case" in raw:
            base = by_id.get(str(raw["repeat_case"]))
            repeats = int(raw.get("repeats", 1))
            if base is None or not isinstance(base.get("text"), str) or repeats < 1:
                raise ValueError(f"invalid repeat case: {raw.get('id')!r}")
            raw["text"] = "\n".join(base["text"] for _ in range(repeats))
        if not raw.get("id") or not isinstance(raw.get("text"), str) or not raw["text"].strip():
            raise ValueError("each fixture case requires id and text")
        case = dict(raw)
        case.setdefault("expected", [])
        case.setdefault("forbidden", [])
        cases.append(case)
    return cases


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixtures", type=Path)
    parser.add_argument("--revision", default=os.environ.get("GLINER2_MODEL_REVISION") or DEFAULT_GLINER2_REVISION)
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--chunk-overlap", type=int, default=DEFAULT_CHUNK_OVERLAP)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--case", action="append", dest="case_ids", help="run only this case; repeatable")
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.repeat < 1 or args.chunk_size <= args.chunk_overlap:
        raise SystemExit("repeat must be positive and chunk-size must exceed chunk-overlap")
    cases = _read_cases(args.fixtures)
    if args.case_ids:
        selected = set(args.case_ids)
        cases = [case for case in cases if str(case["id"]) in selected]
        missing = selected - {str(case["id"]) for case in cases}
        if missing:
            raise SystemExit(f"unknown case(s): {', '.join(sorted(missing))}")
    if not cases:
        raise SystemExit("no cases selected")
    extractor = Gliner2RequirementExtractor(
        revision=args.revision,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    _model, load_metrics = _timed(extractor.load)
    reports: list[dict[str, Any]] = []
    evaluations: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    for case in cases:
        result, metrics = _timed(lambda case=case: extractor.extract_result(str(case.get("role", "")), case["text"]))
        sample = {
            "id": case["id"],
            "word_count": _word_count(case["text"]),
            "inference_path": result.inference_path,
            "requirement_count": len(result.requirements),
            **metrics,
        }
        samples.append(sample)
        for _ in range(args.repeat - 1):
            _, warm_metrics = _timed(
                lambda case=case: extractor.extract_result(str(case.get("role", "")), case["text"])
            )
            samples.append({"id": case["id"], "warm": True, **warm_metrics})
        evaluation = _evaluate_case(case, result)
        evaluations.append(evaluation)
        reports.append(
            {
                "id": case["id"],
                "result": {
                    "extractor": result.extractor,
                    "extractor_version": result.extractor_version,
                    "source_hash": result.source_hash,
                    "inference_path": result.inference_path,
                    "requirements": [_requirement_payload(item) for item in result.requirements],
                },
                "evaluation": evaluation,
                "baseline": _baseline(case),
            }
        )
    report = {
        "runtime": {"python": platform.python_version(), "platform": platform.platform(), "cpu_count": os.cpu_count()},
        "model": "fastino/gliner2.5-small-v1",
        "model_revision": args.revision,
        "fixture": str(args.fixtures),
        "load": load_metrics,
        "samples": samples,
        "quality": _aggregate(evaluations),
        "cases": reports,
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
