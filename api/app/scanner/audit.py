"""Aggregate persisted scanner results without rerunning any analysis."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from statistics import mean, median
from typing import Any


_REQUIREMENT_STATUSES = ("supported", "partial", "not_evidenced", "conflicting", "unverifiable")
_LEXICAL_VISIBILITIES = ("exact", "normalized", "variant", "absent")
_PDF_STATUSES = ("pass", "warning", "fail", "unavailable")
_VERSION_FIELDS = (
    "extractor_version",
    "matcher_version",
    "lexical_version",
    "quality_version",
    "pdf_analysis_version",
    "semantic_score_version",
    "lexical_score_version",
    "pdf_score_version",
    "classification_warning_version",
    "ats_guidance_version",
)
_MAX_INTERESTING_APPLICATIONS = 5
_WARNING_OFFSET_SUFFIX = re.compile(r":\d+$")


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _path(value: object, *keys: str) -> object:
    current: object = value
    for key in keys:
        current = _mapping(current).get(key)
    return current


def _numeric_stats(values: Sequence[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "median": None, "mean": None, "max": None}
    return {
        "min": min(values),
        "median": float(median(values)),
        "mean": float(mean(values)),
        "max": max(values),
    }


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _interesting(
    rows: Sequence[dict[str, Any]],
    *,
    field: str,
    reverse: bool,
    value_name: str,
) -> list[dict[str, Any]]:
    values = [row for row in rows if row.get(value_name) is not None]
    values.sort(key=lambda row: (row[value_name], row["application_id"]), reverse=reverse)
    return [
        {"application_id": row["application_id"], field: row[value_name]}
        for row in values[:_MAX_INTERESTING_APPLICATIONS]
    ]


def build_scanner_audit(
    records: Sequence[Mapping[str, Any]],
    *,
    total_applications: int | None = None,
) -> dict[str, Any]:
    """Build counts, distributions, and review IDs from audit records.

    Each record has ``application_id``, ``scanner_result``, and a freshness
    object containing ``current`` and ``reasons``. No source CV/JD fields are
    read or copied into the returned report.
    """

    stored_results = 0
    current_rows: list[dict[str, Any]] = []
    stale_count = 0
    stale_reasons: Counter[str] = Counter()
    versions: dict[str, Counter[str]] = {field: Counter() for field in _VERSION_FIELDS}

    for record in records:
        application_id = str(record.get("application_id", ""))
        result = record.get("scanner_result")
        if result is None:
            continue
        stored_results += 1
        result_mapping = _mapping(result)
        for field in _VERSION_FIELDS:
            value = _path(result_mapping, "versions", field)
            if isinstance(value, str) and value:
                versions[field][value] += 1

        freshness = _mapping(record.get("freshness"))
        reasons = freshness.get("reasons")
        if not freshness.get("current", False):
            stale_count += 1
            if isinstance(reasons, Sequence) and not isinstance(reasons, (str, bytes)):
                stale_reasons.update(str(reason) for reason in reasons)
            continue

        summary = _mapping(_path(result_mapping, "semantic", "summary"))
        lexical_summary = _mapping(_path(result_mapping, "lexical", "summary"))
        requirement_evaluations = _path(result_mapping, "semantic", "requirements")
        evaluation_counts: Counter[str] = Counter()
        if isinstance(requirement_evaluations, Sequence) and not isinstance(requirement_evaluations, (str, bytes)):
            for evaluation in requirement_evaluations:
                status = _path(evaluation, "status")
                if isinstance(status, str) and status in _REQUIREMENT_STATUSES:
                    evaluation_counts[status] += 1

        lexical_terms = _path(result_mapping, "lexical", "terms")
        lexical_counts: Counter[str] = Counter()
        if isinstance(lexical_terms, Sequence) and not isinstance(lexical_terms, (str, bytes)):
            for term in lexical_terms:
                visibility = _path(term, "visibility")
                if isinstance(visibility, str) and visibility in _LEXICAL_VISIBILITIES:
                    lexical_counts[visibility] += 1

        warnings = _path(result_mapping, "requirement_extraction", "warnings")
        warning_values = (
            [
                _WARNING_OFFSET_SUFFIX.sub("", warning)
                for warning in warnings
                if isinstance(warning, str)
            ]
            if isinstance(warnings, Sequence) and not isinstance(warnings, (str, bytes))
            else []
        )
        job_fit = _number(summary.get("job_fit"))
        classified_fraction = _number(summary.get("classified_fraction"))
        evidence_scorable_fraction = _number(summary.get("evidence_scorable_fraction"))
        partial_count = _number(summary.get("partial_requirement_count", summary.get("partial_count")))
        not_evidenced_count = _number(
            summary.get("not_evidenced_requirement_count", summary.get("not_evidenced_count"))
        )
        conflicting_count = _number(summary.get("conflicting_requirement_count", summary.get("conflicting_count")))
        current_rows.append(
            {
                "application_id": application_id,
                "job_fit": job_fit,
                "classified_fraction": classified_fraction,
                "evidence_scorable_fraction": evidence_scorable_fraction,
                "partial_count": partial_count if partial_count is not None else 0,
                "not_evidenced_count": not_evidenced_count if not_evidenced_count is not None else 0,
                "conflicting_count": conflicting_count if conflicting_count is not None else 0,
                "unverifiable_component_count": _number(summary.get("unverifiable_component_count")) or 0,
                "required_constraint_conflicts": _number(summary.get("required_constraint_conflicts")) or 0,
                "visibility_score": _number(lexical_summary.get("visibility_score")),
                "requirement_counts": evaluation_counts,
                "lexical_counts": lexical_counts,
                "warnings": warning_values,
                "pdf_status": _path(result_mapping, "pdf_recovery", "status"),
            }
        )

    requirement_counts: Counter[str] = Counter()
    lexical_counts: Counter[str] = Counter()
    warning_counts: Counter[str] = Counter()
    pdf_counts: Counter[str] = Counter()
    for row in current_rows:
        requirement_counts.update(row["requirement_counts"])
        lexical_counts.update(row["lexical_counts"])
        warning_counts.update(row["warnings"])
        if row["pdf_status"] in _PDF_STATUSES:
            pdf_counts[row["pdf_status"]] += 1

    job_fit_values = [row["job_fit"] for row in current_rows if row["job_fit"] is not None]
    classified_values = [row["classified_fraction"] for row in current_rows if row["classified_fraction"] is not None]
    evidence_values = [row["evidence_scorable_fraction"] for row in current_rows if row["evidence_scorable_fraction"] is not None]
    visibility_values = [row["visibility_score"] for row in current_rows if row["visibility_score"] is not None]

    interesting = {
        "lowest_classification_coverage": _interesting(
            current_rows,
            field="classified_fraction",
            reverse=False,
            value_name="classified_fraction",
        ),
        "highest_job_fit": _interesting(
            current_rows,
            field="job_fit",
            reverse=True,
            value_name="job_fit",
        ),
        "lowest_job_fit": _interesting(
            current_rows,
            field="job_fit",
            reverse=False,
            value_name="job_fit",
        ),
        "highest_partial_count": _interesting(
            current_rows,
            field="partial_count",
            reverse=True,
            value_name="partial_count",
        ),
        "highest_not_evidenced_count": _interesting(
            current_rows,
            field="not_evidenced_count",
            reverse=True,
            value_name="not_evidenced_count",
        ),
        "applications_with_conflicts": _interesting(
            [row for row in current_rows if row["conflicting_count"] > 0],
            field="conflicting_count",
            reverse=True,
            value_name="conflicting_count",
        ),
        "applications_with_extraction_warnings": [
            {"application_id": row["application_id"], "warning_count": len(row["warnings"])}
            for row in sorted(
                (row for row in current_rows if row["warnings"]),
                key=lambda row: (-len(row["warnings"]), row["application_id"]),
            )[:_MAX_INTERESTING_APPLICATIONS]
        ],
    }

    total = len(records) if total_applications is None else total_applications
    return {
        "aggregate_scope": "current_scanner_results",
        "applications": {
            "total": total,
            "with_scanner_result": stored_results,
            "current_scanner_results": len(current_rows),
            "stale_scanner_results": stale_count,
            "without_scanner_result": max(0, total - stored_results),
        },
        "scanner_versions": {field: dict(sorted(counter.items())) for field, counter in versions.items()},
        "job_fit": _numeric_stats(job_fit_values),
        "classified_fraction": _numeric_stats(classified_values),
        "evidence_scorable_fraction": _numeric_stats(evidence_values),
        "requirement_counts": {status: requirement_counts[status] for status in _REQUIREMENT_STATUSES},
        "unverifiable_component_count": sum(row["unverifiable_component_count"] for row in current_rows),
        "required_constraint_conflicts": sum(row["required_constraint_conflicts"] for row in current_rows),
        "lexical": {
            "visibility_score": _numeric_stats(visibility_values),
            "term_counts": {visibility: lexical_counts[visibility] for visibility in _LEXICAL_VISIBILITIES},
        },
        "extraction_warning_frequencies": dict(sorted(warning_counts.items())),
        "pdf_status_counts": {status: pdf_counts[status] for status in _PDF_STATUSES},
        "freshness_reason_frequencies": dict(sorted(stale_reasons.items())),
        "interesting_application_ids": interesting,
    }


def _format_stats(stats: Mapping[str, Any], *, percentage: bool = True) -> str:
    values = (stats.get("min"), stats.get("median"), stats.get("mean"), stats.get("max"))
    if all(value is None for value in values):
        return "n/a"
    rendered = ["n/a" if value is None else f"{value * 100:.1f}%" if percentage else f"{value:.2f}" for value in values]
    return " / ".join(rendered)


def format_scanner_audit(report: Mapping[str, Any]) -> str:
    """Render a compact, content-free review table for terminal output."""

    applications = _mapping(report.get("applications"))
    lexical = _mapping(report.get("lexical"))
    lines = [
        "SCANNER SHADOW AUDIT",
        "Metric                                      Min / Median / Mean / Max",
        f"Applications total                        {applications.get('total', 0)}",
        f"Scanner results current / stale / missing {applications.get('current_scanner_results', 0)} / {applications.get('stale_scanner_results', 0)} / {applications.get('without_scanner_result', 0)}",
        f"Job Fit                                    {_format_stats(_mapping(report.get('job_fit')))}",
        f"Classified fraction                       {_format_stats(_mapping(report.get('classified_fraction')))}",
        f"Evidence scorable fraction                {_format_stats(_mapping(report.get('evidence_scorable_fraction')))}",
        f"Term visibility                           {_format_stats(_mapping(lexical.get('visibility_score')))}",
        "Requirement counts                       " + ", ".join(f"{key}={value}" for key, value in _mapping(report.get("requirement_counts")).items()),
        f"Unverifiable components / constraint conflicts {report.get('unverifiable_component_count', 0)} / {report.get('required_constraint_conflicts', 0)}",
        "Lexical terms                             " + ", ".join(f"{key}={value}" for key, value in _mapping(lexical.get("term_counts")).items()),
        "PDF status                                " + ", ".join(f"{key}={value}" for key, value in _mapping(report.get("pdf_status_counts")).items()),
    ]
    for field, values in _mapping(report.get("scanner_versions")).items():
        rendered_versions = ", ".join(f"{version} ({count})" for version, count in values.items()) or "none"
        lines.append(f"Version {field:34} {rendered_versions}")
    warnings = _mapping(report.get("extraction_warning_frequencies"))
    lines.append(
        "Extraction warning frequencies             "
        + (", ".join(f"{warning}={count}" for warning, count in warnings.items()) or "none")
    )
    stale_reasons = _mapping(report.get("freshness_reason_frequencies"))
    lines.append(
        "Staleness reasons                          "
        + (", ".join(f"{reason}={count}" for reason, count in stale_reasons.items()) or "none")
    )
    for name, values in _mapping(report.get("interesting_application_ids")).items():
        rendered_ids = ", ".join(str(item.get("application_id")) for item in values) if values else "none"
        lines.append(f"{name.replace('_', ' '):43} {rendered_ids}")
    return "\n".join(lines)


__all__ = ["build_scanner_audit", "format_scanner_audit"]
