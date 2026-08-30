"""Run the standalone GLiNER2.5 requirement-extraction spike.

Run from ``api/`` with the optional local-model dependencies installed:

    python -m scripts.gliner2_spike --repeat 3

The default mode evaluates GLiNER2.5-small-v1 and compares it with the former
deterministic requirement-v2 parser.  ``--mode hybrid`` additionally emits a
comparison-only merge of semantic candidates and requirement-v2.  Neither
mode is imported by or wired into the production request path.
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

try:
    from scripts.gliner2_spike_lib import (
        ExtractionResult,
        Gliner2RequirementExtractor,
        Requirement,
        compare_requirement_sets,
        existing_v2_requirements,
        merge_requirement_sets,
    )
except ModuleNotFoundError:  # Allow ``python api/scripts/gliner2_spike.py`` as well.
    from gliner2_spike_lib import (  # type: ignore[no-redef]
        ExtractionResult,
        Gliner2RequirementExtractor,
        Requirement,
        compare_requirement_sets,
        existing_v2_requirements,
        merge_requirement_sets,
    )


DEFAULT_FIXTURES = Path(__file__).resolve().with_name("gliner2_jobs.json")


def _read_fixture_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"fixture root must be a list: {path}")
    raw_cases = [dict(case) for case in payload]
    by_id = {str(case["id"]): case for case in raw_cases}
    cases: list[dict[str, Any]] = []
    for case in raw_cases:
        if "repeat_case" in case:
            base = by_id.get(str(case["repeat_case"]))
            if base is None:
                raise ValueError(f"unknown repeat_case {case['repeat_case']!r}")
            repeats = int(case.get("repeats", 1))
            if repeats < 1:
                raise ValueError(f"repeats must be positive: {case['id']}")
            case["text"] = "\n".join(str(base["text"]) for _ in range(repeats))
        if not isinstance(case.get("text"), str) or not case["text"].strip():
            raise ValueError(f"fixture case has no text: {case.get('id')!r}")
        case.setdefault("expected", [])
        case.setdefault("forbidden", [])
        case.setdefault("evaluate", True)
        cases.append(case)
    return cases


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


def _read_limit(path: str) -> str | int | None:
    try:
        value = Path(path).read_text(encoding="ascii").strip()
    except (FileNotFoundError, OSError):
        return None
    if value == "max":
        return value
    try:
        return int(value)
    except ValueError:
        return value


def _runtime_info() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "cgroup_memory_max": _read_limit("/sys/fs/cgroup/memory.max"),
        "cgroup_cpu_max": _read_limit("/sys/fs/cgroup/cpu.max"),
    }


def _timed(call: Any) -> tuple[Any, dict[str, Any]]:
    rss_before = _current_rss_bytes()
    peak_before = _peak_rss_bytes()
    cpu_before = _cpu_seconds()
    started = time.perf_counter()
    value = call()
    elapsed = time.perf_counter() - started
    cpu = _cpu_seconds() - cpu_before
    rss_after = _current_rss_bytes()
    peak_after = _peak_rss_bytes()
    return value, {
        "wall_seconds": elapsed,
        "cpu_seconds": cpu,
        "cpu_utilization_percent": (cpu / elapsed * 100.0) if elapsed else 0.0,
        "rss_before_bytes": rss_before,
        "rss_after_bytes": rss_after,
        "peak_rss_bytes": peak_after,
        "peak_rss_delta_bytes": peak_after - peak_before,
    }


def _normalise(value: str) -> str:
    return " ".join(value.casefold().split())


def _anchor_range(source: str, anchor: str) -> tuple[int, int] | None:
    folded = source.casefold()
    start = folded.find(anchor.casefold())
    return (start, start + len(anchor)) if start >= 0 else None


def _range_overlap(left: tuple[int, int], right: tuple[int, int]) -> int:
    return max(0, min(left[1], right[1]) - max(left[0], right[0]))


def _prediction_matches_gold(source: str, expected: dict[str, Any], prediction: Requirement) -> int:
    anchor = str(expected.get("anchor", ""))
    anchor_range = _anchor_range(source, anchor)
    if not anchor_range:
        return 0
    if _normalise(anchor) in _normalise(prediction.source_text):
        return 3
    if prediction.source_start is not None and prediction.source_end is not None:
        overlap = _range_overlap(anchor_range, (prediction.source_start, prediction.source_end))
        if overlap:
            expected_concepts = {_normalise(str(value)) for value in expected.get("concepts", [])}
            prediction_concepts = {_normalise(value) for value in prediction.concepts}
            if expected_concepts & prediction_concepts:
                return 2
    expected_concepts = {_normalise(str(value)) for value in expected.get("concepts", [])}
    prediction_concepts = {_normalise(value) for value in prediction.concepts}
    return 1 if expected_concepts & prediction_concepts else 0


def _constraint_matches(expected: dict[str, Any], prediction: Requirement) -> bool:
    wanted = expected.get("constraint")
    if not wanted:
        return True
    if not isinstance(wanted, dict):
        return False
    for constraint in prediction.constraints:
        if constraint.kind != wanted.get("kind"):
            continue
        if "value" not in wanted or wanted["value"] is None:
            return True
        if constraint.value == wanted["value"]:
            return True
    return False


def evaluate_case(case: dict[str, Any], result: ExtractionResult) -> dict[str, Any]:
    """Evaluate the small gold fixture without pretending it is a benchmark corpus."""

    source = str(case["text"])
    expected = [item for item in case.get("expected", []) if isinstance(item, dict)]
    predictions = list(result.requirements)
    scores = [
        [_prediction_matches_gold(source, item, prediction) for prediction in predictions]
        for item in expected
    ]
    matched_expected: set[int] = set()
    matched_predictions: set[int] = set()
    pairs: list[tuple[int, int]] = []
    ranked = sorted(
        (
            (score, expected_index, prediction_index)
            for expected_index, row in enumerate(scores)
            for prediction_index, score in enumerate(row)
            if score
        ),
        reverse=True,
    )
    for _score, expected_index, prediction_index in ranked:
        if expected_index in matched_expected or prediction_index in matched_predictions:
            continue
        matched_expected.add(expected_index)
        matched_predictions.add(prediction_index)
        pairs.append((expected_index, prediction_index))

    missing = [expected[index] for index in range(len(expected)) if index not in matched_expected]
    invented = [predictions[index].as_dict() for index in range(len(predictions)) if index not in matched_predictions]
    importance_correct = sum(
        predictions[prediction_index].importance.value == expected[expected_index].get("importance")
        for expected_index, prediction_index in pairs
        if expected[expected_index].get("importance")
    )
    importance_total = sum(1 for expected_index, _ in pairs if expected[expected_index].get("importance"))
    constraint_correct = sum(
        _constraint_matches(expected[expected_index], predictions[prediction_index])
        for expected_index, prediction_index in pairs
        if expected[expected_index].get("constraint")
    )
    constraint_total = sum(1 for expected_index, _ in pairs if expected[expected_index].get("constraint"))

    false_required: list[dict[str, Any]] = []
    for forbidden in case.get("forbidden", []):
        if not isinstance(forbidden, dict):
            continue
        anchor = str(forbidden.get("anchor", ""))
        anchor_range = _anchor_range(source, anchor)
        if not anchor_range:
            continue
        for prediction in predictions:
            if prediction.importance.value != "required":
                continue
            if anchor.casefold() in prediction.source_text.casefold() or (
                prediction.source_start is not None
                and prediction.source_end is not None
                and _range_overlap(anchor_range, (prediction.source_start, prediction.source_end))
            ):
                false_required.append(
                    {"anchor": anchor, "prediction": prediction.as_dict()}
                )

    split_count = sum(
        sum(1 for score in row if score) > 1
        for row in scores
    )
    merge_count = sum(
        sum(1 for row in scores if row[prediction_index]) > 1
        for prediction_index in range(len(predictions))
    )
    return {
        "gold_count": len(expected),
        "predicted_count": len(predictions),
        "matched_count": len(pairs),
        "precision": len(pairs) / len(predictions) if predictions else 0.0,
        "recall": len(pairs) / len(expected) if expected else 0.0,
        "importance_accuracy": importance_correct / importance_total if importance_total else None,
        "constraint_accuracy": constraint_correct / constraint_total if constraint_total else None,
        "false_required_count": len(false_required),
        "false_required": false_required,
        "split_count": split_count,
        "merge_count": merge_count,
        "missing": missing,
        "invented": invented,
    }


def _aggregate_evaluation(evaluations: list[dict[str, Any]]) -> dict[str, Any]:
    gold = sum(int(item["gold_count"]) for item in evaluations)
    predicted = sum(int(item["predicted_count"]) for item in evaluations)
    matched = sum(int(item["matched_count"]) for item in evaluations)
    importance_values = [item["importance_accuracy"] for item in evaluations if item["importance_accuracy"] is not None]
    constraint_values = [item["constraint_accuracy"] for item in evaluations if item["constraint_accuracy"] is not None]
    return {
        "cases": len(evaluations),
        "gold_count": gold,
        "predicted_count": predicted,
        "matched_count": matched,
        "precision": matched / predicted if predicted else 0.0,
        "recall": matched / gold if gold else 0.0,
        "importance_accuracy": sum(importance_values) / len(importance_values) if importance_values else None,
        "constraint_accuracy": sum(constraint_values) / len(constraint_values) if constraint_values else None,
        "false_required_count": sum(int(item["false_required_count"]) for item in evaluations),
        "split_count": sum(int(item["split_count"]) for item in evaluations),
        "merge_count": sum(int(item["merge_count"]) for item in evaluations),
    }


def _result_payload(result: ExtractionResult) -> dict[str, Any]:
    return result.as_dict()


def _baseline_case(case: dict[str, Any]) -> tuple[ExtractionResult | None, str | None]:
    try:
        return existing_v2_requirements(str(case["text"]), role=str(case.get("role", ""))), None
    except Exception as exc:  # The report should identify fixture-specific baseline failures.
        return None, f"{type(exc).__name__}: {exc}"


def _run_baseline(cases: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    case_reports: list[dict[str, Any]] = []
    evaluations: list[dict[str, Any]] = []
    for case in cases:
        result, error = _baseline_case(case)
        report: dict[str, Any] = {"id": case["id"], "word_count": len(re.findall(r"\S+", case["text"]))}
        if error:
            report["error"] = error
        elif result:
            report["result"] = _result_payload(result)
            if case.get("evaluate", True):
                evaluation = evaluate_case(case, result)
                report["evaluation"] = evaluation
                evaluations.append(evaluation)
        case_reports.append(report)
    return {"mode": mode, "cases": case_reports, "quality": _aggregate_evaluation(evaluations)}


def _run_model(cases: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    extractor = Gliner2RequirementExtractor(
        model_name=args.model,
        revision=args.revision,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    _model, load_metrics = _timed(extractor.load)
    baseline_results: dict[str, ExtractionResult] = {}
    baseline_errors: dict[str, str] = {}
    for case in cases:
        baseline, error = _baseline_case(case)
        if baseline:
            baseline_results[str(case["id"])] = baseline
        if error:
            baseline_errors[str(case["id"])] = error

    if args.warmup:
        for case in cases[: args.warmup_cases]:
            for _ in range(args.warmup):
                extractor.extract(str(case["text"]))

    case_reports: list[dict[str, Any]] = []
    evaluations: list[dict[str, Any]] = []
    hybrid_evaluations: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    for case in cases:
        case_id = str(case["id"])
        for iteration in range(args.repeat):
            result, metrics = _timed(lambda case=case: extractor.extract(str(case["text"])))
            samples.append(
                {
                    "case_id": case_id,
                    "iteration": iteration,
                    "word_count": len(re.findall(r"\S+", case["text"])),
                    "inference_path": result.inference_path,
                    "requirement_count": len(result.requirements),
                    **metrics,
                }
            )
            if iteration:
                continue
            report: dict[str, Any] = {
                "id": case_id,
                "word_count": len(re.findall(r"\S+", case["text"])),
                "result": _result_payload(result),
            }
            if case_id in baseline_results:
                baseline = baseline_results[case_id]
                report["comparison"] = compare_requirement_sets(baseline.requirements, result.requirements)
                if args.mode == "hybrid":
                    hybrid = merge_requirement_sets(result, baseline)
                    report["hybrid_result"] = _result_payload(hybrid)
                    if case.get("evaluate", True):
                        hybrid_evaluation = evaluate_case(case, hybrid)
                        report["hybrid_evaluation"] = hybrid_evaluation
                        hybrid_evaluations.append(hybrid_evaluation)
            elif case_id in baseline_errors:
                report["baseline_error"] = baseline_errors[case_id]
            if case.get("evaluate", True):
                evaluation = evaluate_case(case, result)
                report["evaluation"] = evaluation
                evaluations.append(evaluation)
            case_reports.append(report)

    report: dict[str, Any] = {
        "model": args.model,
        "model_revision": args.revision or "default",
        "mode": args.mode,
        "gliner2_version": _gliner2_version(),
        "load": load_metrics,
        "samples": samples,
        "cases": case_reports,
        "quality": _aggregate_evaluation(evaluations),
    }
    if hybrid_evaluations:
        report["hybrid_quality"] = _aggregate_evaluation(hybrid_evaluations)
    return report


def _gliner2_version() -> str | None:
    try:
        import gliner2
    except ImportError:
        return None
    return str(getattr(gliner2, "__version__", "unknown"))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument("--model", default=os.environ.get("GLINER2_MODEL", "fastino/gliner2.5-small-v1"))
    parser.add_argument("--revision", default=os.environ.get("GLINER2_MODEL_REVISION") or None)
    parser.add_argument("--mode", choices=("model", "hybrid", "baseline"), default="model")
    parser.add_argument("--repeat", type=int, default=2, help="model extraction samples per case")
    parser.add_argument("--warmup", type=int, default=0, help="unrecorded warmup calls per selected case")
    parser.add_argument("--warmup-cases", type=int, default=1)
    parser.add_argument("--chunk-size", type=int, default=384)
    parser.add_argument("--chunk-overlap", type=int, default=64)
    parser.add_argument("--case", action="append", dest="case_ids", help="run only this fixture id; repeatable")
    parser.add_argument("--output", type=Path, help="write JSON report to this path as well as stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.repeat < 1:
        raise SystemExit("--repeat must be positive")
    if args.chunk_size <= args.chunk_overlap:
        raise SystemExit("--chunk-size must be greater than --chunk-overlap")
    cases = _read_fixture_cases(args.fixtures)
    if args.case_ids:
        selected = set(args.case_ids)
        cases = [case for case in cases if str(case["id"]) in selected]
        missing = selected - {str(case["id"]) for case in cases}
        if missing:
            raise SystemExit(f"unknown fixture case(s): {', '.join(sorted(missing))}")
    if not cases:
        raise SystemExit("no fixture cases selected")

    if args.mode == "baseline":
        report: dict[str, Any] = {
            "runtime": _runtime_info(),
            "fixture": str(args.fixtures),
            "baseline": _run_baseline(cases, args.mode),
        }
    else:
        report = {
            "runtime": _runtime_info(),
            "fixture": str(args.fixtures),
            "model_run": _run_model(cases, args),
        }
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
