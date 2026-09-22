"""Pure server-side evaluation for tailoring protocol v5.

The scanner owns deterministic facts.  This module only aggregates those
facts into bounded readiness states and contextual deltas; it never extracts a
new requirement or writes a candidate.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any

from app.http_schemas.tailoring_evaluation import (
    TAILORING_EVALUATION_VERSION,
    TailoringDimensions,
    TailoringEvaluation,
    TailoringFindingDimension,
    TailoringInferenceNote,
    TailoringIssue,
    TailoringKeywordTransition,
    TailoringNumericDimension,
    TailoringPassChange,
    TailoringPreviousPassComparison,
    TailoringReadiness,
    TailoringRequirementTransition,
    TailoringSourceComparison,
)
from app.scanner.matching import flatten_cv_text
from app.scanner.requirements import RequirementExtraction, RequirementImportance
from app.scanner.results import (
    EvidenceStatus,
    FindingSeverity,
    LexicalVisibility,
    PDFRecoveryStatus,
    ScanResult,
)


_CRITICAL_PDF_CHECKS = frozenset({"text_retention", "reading_order", "contact_recovery"})
_SAFE_SEMANTIC_IMPROVEMENTS = frozenset(
    {
        (EvidenceStatus.NOT_EVIDENCED, EvidenceStatus.PARTIAL),
        (EvidenceStatus.NOT_EVIDENCED, EvidenceStatus.SUPPORTED),
        (EvidenceStatus.PARTIAL, EvidenceStatus.SUPPORTED),
    }
)
_SAFE_SEMANTIC_REGRESSIONS = frozenset(
    {
        (EvidenceStatus.SUPPORTED, EvidenceStatus.PARTIAL),
        (EvidenceStatus.SUPPORTED, EvidenceStatus.NOT_EVIDENCED),
        (EvidenceStatus.PARTIAL, EvidenceStatus.NOT_EVIDENCED),
    }
)
_SAFE_KEYWORD_IMPROVEMENTS = frozenset(
    {
        (LexicalVisibility.ABSENT, LexicalVisibility.VARIANT),
        (LexicalVisibility.ABSENT, LexicalVisibility.NORMALIZED),
        (LexicalVisibility.ABSENT, LexicalVisibility.EXACT),
        (LexicalVisibility.VARIANT, LexicalVisibility.NORMALIZED),
        (LexicalVisibility.VARIANT, LexicalVisibility.EXACT),
        (LexicalVisibility.NORMALIZED, LexicalVisibility.EXACT),
    }
)
_SAFE_KEYWORD_REGRESSIONS = frozenset(
    {
        (LexicalVisibility.EXACT, LexicalVisibility.ABSENT),
        (LexicalVisibility.NORMALIZED, LexicalVisibility.ABSENT),
        (LexicalVisibility.VARIANT, LexicalVisibility.ABSENT),
    }
)


def _value(obj: object, key: str, default: object = None) -> object:
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _dump(obj: object) -> object:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")  # type: ignore[union-attr]
    if hasattr(obj, "sections"):
        return {
            "sections": getattr(obj, "sections", []),
            "template_id": getattr(obj, "template_id", None),
            "customizations": getattr(obj, "customizations", {}),
        }
    return obj


def _enum_value(value: object) -> str | None:
    if value is None:
        return None
    return str(getattr(value, "value", value))


def _candidate_text(candidate: object) -> str:
    parts: list[str] = []
    try:
        parts.extend(field.text for field in flatten_cv_text(candidate) if field.text.strip())
    except (TypeError, ValueError, AttributeError):
        pass
    try:
        parts.append(json.dumps(_dump(candidate), ensure_ascii=False, default=str))
    except (TypeError, ValueError):
        parts.append(str(candidate))
    return "\n".join(parts)


def _contains_term(text: str, term: str) -> bool:
    normalized = " ".join(term.strip().split())
    if not normalized:
        return False
    pattern = r"(?<!\w)" + r"\s+".join(re.escape(part) for part in normalized.split()) + r"(?!\w)"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def _user_forbidden_terms(instructions: str | None) -> list[tuple[str, str]]:
    if not instructions or not instructions.strip():
        return []
    forbidden: list[tuple[str, str]] = []
    instruction_text = instructions.strip()
    prohibition = re.compile(
        r"\b(?:do\s+not|don't|dont)\s+(?:claim|include|add|infer|say|mention|use)\s+([^.!?;\n]{1,100})",
        re.IGNORECASE,
    )
    for match in prohibition.finditer(instruction_text):
        term = match.group(1).strip(" \t,:")
        if term:
            forbidden.append((term, "The user's explicit instruction prohibits this claim."))

    correction = re.compile(
        r"\b(?:i\s+)?(?:used|use|prefer|have)\s+([^,.;\n]{1,80})\s*,?\s+not\s+([^.!?;\n]{1,80})",
        re.IGNORECASE,
    )
    for match in correction.finditer(instruction_text):
        term = match.group(2).strip(" \t,:")
        if term:
            forbidden.append((term, "The user's correction identifies this claim as inaccurate."))
    unique: list[tuple[str, str]] = []
    seen: set[str] = set()
    for term, reason in forbidden:
        key = term.casefold()
        if key not in seen:
            unique.append((term, reason))
            seen.add(key)
    return unique[:20]


_EMPLOYER_FIELDS = ("company", "company_name", "employer", "organization", "organisation")
_JOB_TITLE_FIELDS = ("position", "job_title", "title", "role")
_INSTITUTION_FIELDS = ("institution", "school", "university", "college")
_DEGREE_FIELDS = ("degree", "qualification")
_CERTIFICATION_FIELDS = ("certification", "certificate", "name", "title")
_DATE_FIELDS = ("start_date", "end_date", "date", "issued_date", "completion_date", "year")


def _normalize_fact(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.casefold().split())
    return normalized or None


def _add_fact_values(target: set[str], row: Mapping[str, Any], fields: Sequence[str]) -> None:
    for field_name in fields:
        value = _normalize_fact(row.get(field_name))
        if value:
            target.add(value)


@dataclass(frozen=True)
class AuthoritativeFactIndex:
    """Facts that the tailoring evaluator may treat as supplied evidence.

    The index is deliberately built from values passed by the service layer.
    It has no database or session dependency, which keeps high-risk fact
    validation reusable without making the pure evaluator reach into storage.
    """

    employers: frozenset[str] = field(default_factory=frozenset)
    job_titles: frozenset[str] = field(default_factory=frozenset)
    institutions: frozenset[str] = field(default_factory=frozenset)
    degrees: frozenset[str] = field(default_factory=frozenset)
    certifications: frozenset[str] = field(default_factory=frozenset)
    dates: frozenset[str] = field(default_factory=frozenset)


def build_authoritative_fact_index(
    *,
    source_cv: object | None = None,
    library: Sequence[object] = (),
    user_confirmed_facts: Sequence[Mapping[str, Any]] = (),
) -> AuthoritativeFactIndex:
    """Index high-risk facts from all authoritative supplied evidence.

    ``library`` is expected to be the serialized, frozen session evidence
    supplied by the service layer.  Accepting generic mappings/objects keeps
    this helper usable in pure tests and leaves room for additional evidence
    sources without repeating source-CV-only checks.
    """

    facts: dict[str, set[str]] = {
        "employers": set(),
        "job_titles": set(),
        "institutions": set(),
        "degrees": set(),
        "certifications": set(),
        "dates": set(),
    }

    def collect_row(row: Mapping[str, Any], kind: str | None = None) -> None:
        _add_fact_values(facts["employers"], row, _EMPLOYER_FIELDS)
        _add_fact_values(facts["job_titles"], row, _JOB_TITLE_FIELDS)
        _add_fact_values(facts["dates"], row, _DATE_FIELDS)
        if kind in {None, "education"}:
            _add_fact_values(facts["institutions"], row, _INSTITUTION_FIELDS)
            _add_fact_values(facts["degrees"], row, _DEGREE_FIELDS)
        if kind in {None, "certification"}:
            _add_fact_values(facts["certifications"], row, _CERTIFICATION_FIELDS)

    source = _dump(source_cv) if source_cv is not None else None
    sections = _value(source, "sections", []) if source is not None else []
    if isinstance(sections, Sequence) and not isinstance(sections, (str, bytes, bytearray)):
        for section in sections:
            section_type = str(_value(section, "type", ""))
            data = _value(section, "data", [])
            if isinstance(data, Mapping):
                collect_row(data, section_type)
            elif isinstance(data, Sequence) and not isinstance(data, (str, bytes, bytearray)):
                for row in data:
                    if isinstance(row, Mapping):
                        collect_row(row, section_type)

    for entry in library:
        kind = str(_value(entry, "kind", "")) or None
        payload = _value(entry, "payload", [])
        if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
            for row in payload:
                if isinstance(row, Mapping):
                    collect_row(row, kind)

    for row in user_confirmed_facts:
        collect_row(row)

    return AuthoritativeFactIndex(**{key: frozenset(value) for key, value in facts.items()})


def _employers(document: object) -> set[str]:
    return set(build_authoritative_fact_index(source_cv=document).employers)


def _requirement_label(requirement: object) -> str:
    source = _value(_value(requirement, "source"), "original_text")
    if isinstance(source, str) and source.strip():
        return source.strip()
    concept = _value(_value(_value(requirement, "expression"), "concept"), "name")
    return str(concept or _value(requirement, "id"))


def _semantic_map(scan: ScanResult | None) -> dict[str, object]:
    if scan is None:
        return {}
    return {item.requirement_id: item for item in scan.semantic.requirements}


def _lexical_map(scan: ScanResult | None) -> dict[str, object]:
    if scan is None:
        return {}
    return {item.id: item for item in scan.lexical.terms}


def _classify_semantic(source: EvidenceStatus, candidate: EvidenceStatus) -> str:
    if source is candidate:
        return "unchanged"
    if (source, candidate) in _SAFE_SEMANTIC_IMPROVEMENTS:
        return "improved"
    if (source, candidate) in _SAFE_SEMANTIC_REGRESSIONS:
        return "regressed"
    return "changed_needs_review"


def _classify_keyword(source: LexicalVisibility, candidate: LexicalVisibility) -> str:
    if source is candidate:
        return "unchanged"
    if (source, candidate) in _SAFE_KEYWORD_IMPROVEMENTS:
        return "improved"
    if (source, candidate) in _SAFE_KEYWORD_REGRESSIONS:
        return "regressed"
    return "changed_needs_review"


def _summary_score(scan: ScanResult | None, branch: str) -> float | None:
    if scan is None:
        return None
    summary = _value(_value(scan, branch), "summary")
    score_name = "job_fit" if branch == "semantic" else "visibility_score" if branch == "lexical" else "recovery_score"
    score = _value(summary, score_name)
    return float(score) if isinstance(score, (int, float)) and not isinstance(score, bool) else None


def _ats_findings(scan: ScanResult | None) -> list[object]:
    if scan is None or scan.ats_guidance is None:
        return []
    guidance = scan.ats_guidance
    findings: list[object] = [*guidance.common_findings, *guidance.platform_sensitive_findings]
    for platform in guidance.platforms.values():
        findings.extend(platform.findings)
        findings.extend(platform.tips)
    return findings


def _count_findings(findings: Sequence[object], *, include_pass: bool = False) -> TailoringFindingDimension:
    actionable = [item for item in findings if include_pass or _enum_value(_value(item, "severity")) != "pass"]
    counts = {severity: 0 for severity in ("error", "warning", "info")}
    for item in actionable:
        severity = _enum_value(_value(item, "severity"))
        if severity in counts:
            counts[severity] += 1
    return TailoringFindingDimension(
        candidate_count=len(actionable),
        candidate_error_count=counts["error"],
        candidate_warning_count=counts["warning"],
        candidate_info_count=counts["info"],
    )


def _dimension_counts(
    source_findings: Sequence[object],
    candidate_findings: Sequence[object],
    *,
    ats: bool = False,
) -> TailoringFindingDimension:
    source = _count_findings(source_findings, include_pass=ats)
    candidate = _count_findings(candidate_findings, include_pass=ats)
    return candidate.model_copy(update={"source_count": source.candidate_count})


def _issue(
    *,
    issue_id: str,
    kind: str,
    category: str,
    message: str,
    detail: str | None = None,
    priority: str = "normal",
    requirement_id: str | None = None,
    term_id: str | None = None,
    code: str | None = None,
    importance: RequirementImportance | None = None,
) -> TailoringIssue:
    return TailoringIssue(
        id=issue_id[:180],
        kind=kind,  # type: ignore[arg-type]
        category=category,  # type: ignore[arg-type]
        message=message[:2_000],
        detail=detail[:2_000] if detail else None,
        priority=priority,  # type: ignore[arg-type]
        requirement_id=requirement_id,
        term_id=term_id,
        code=code,
        importance=importance,
    )


def _add_issue(bucket: list[TailoringIssue], value: TailoringIssue) -> None:
    if any(item.id == value.id for item in bucket):
        return
    if len(bucket) < 100:
        bucket.append(value)


def _transition_changes(
    previous: ScanResult,
    current: ScanResult,
    requirements: Mapping[str, object],
) -> list[TailoringPassChange]:
    changes: list[TailoringPassChange] = []
    prior_semantic = _semantic_map(previous)
    current_semantic = _semantic_map(current)
    for requirement_id in sorted(set(prior_semantic) | set(current_semantic)):
        before = _value(prior_semantic.get(requirement_id), "status")
        after = _value(current_semantic.get(requirement_id), "status")
        if before is None or after is None or before is after:
            continue
        classification = _classify_semantic(before, after)
        if classification == "unchanged":
            continue
        requirement = requirements.get(requirement_id)
        label = _requirement_label(requirement) if requirement is not None else requirement_id
        if classification == "improved":
            kind = "fixed" if after is EvidenceStatus.SUPPORTED else "improved"
            message = f"{label}: {_enum_value(before)} → {_enum_value(after)}"
        elif classification == "regressed":
            kind = "regressed"
            message = f"{label}: {_enum_value(before)} → {_enum_value(after)}"
        else:
            kind = "improved" if _enum_value(after) in {"supported", "partial"} else "regressed"
            message = f"{label}: {_enum_value(before)} → {_enum_value(after)} needs review"
        changes.append(
            TailoringPassChange(
                id=f"pass-semantic-{requirement_id}",
                area="semantic",
                classification=kind,  # type: ignore[arg-type]
                message=message,
                requirement_id=requirement_id,
            )
        )

    prior_lexical = _lexical_map(previous)
    current_lexical = _lexical_map(current)
    for term_id in sorted(set(prior_lexical) | set(current_lexical)):
        before = _value(prior_lexical.get(term_id), "visibility")
        after = _value(current_lexical.get(term_id), "visibility")
        if before is None or after is None or before is after:
            continue
        classification = _classify_keyword(before, after)
        if classification == "unchanged":
            continue
        term = str(_value(current_lexical.get(term_id), "term") or _value(prior_lexical.get(term_id), "term") or term_id)
        kind = "fixed" if classification == "improved" and after is LexicalVisibility.EXACT else classification
        changes.append(
            TailoringPassChange(
                id=f"pass-lexical-{term_id}",
                area="lexical",
                classification=kind,  # type: ignore[arg-type]
                message=f"{term}: {_enum_value(before)} → {_enum_value(after)}",
                term_id=term_id,
            )
        )

    prior_quality = {str(_value(item, "code")) for item in previous.presentation_quality.findings}
    current_quality = {str(_value(item, "code")) for item in current.presentation_quality.findings}
    for code in sorted(prior_quality - current_quality):
        changes.append(
            TailoringPassChange(
                id=f"pass-quality-fixed-{code}",
                area="resume_quality",
                classification="fixed",
                message=f"Resume Quality finding fixed: {code}",
            )
        )
    for code in sorted(current_quality - prior_quality):
        changes.append(
            TailoringPassChange(
                id=f"pass-quality-introduced-{code}",
                area="resume_quality",
                classification="introduced",
                message=f"Resume Quality finding introduced: {code}",
            )
        )

    prior_pdf = {
        str(_value(item, "code"))
        for item in previous.pdf_recovery.checks
        if _enum_value(_value(item, "status")) in {"fail", "warning"}
    }
    current_pdf = {
        str(_value(item, "code"))
        for item in current.pdf_recovery.checks
        if _enum_value(_value(item, "status")) in {"fail", "warning"}
    }
    for code in sorted(prior_pdf - current_pdf):
        changes.append(
            TailoringPassChange(
                id=f"pass-pdf-fixed-{code}",
                area="pdf_recovery",
                classification="fixed",
                message=f"PDF recovery finding fixed: {code}",
            )
        )
    for code in sorted(current_pdf - prior_pdf):
        changes.append(
            TailoringPassChange(
                id=f"pass-pdf-introduced-{code}",
                area="pdf_recovery",
                classification="introduced",
                message=f"PDF recovery finding introduced: {code}",
            )
        )
    return changes[:200]


def evaluate_tailoring(
    requirements: RequirementExtraction,
    candidate_scan: ScanResult,
    candidate_hash: str,
    *,
    source_scan: ScanResult | None = None,
    previous_candidate_scan: ScanResult | None = None,
    previous_candidate_hash: str | None = None,
    previous_evaluation: TailoringEvaluation | None = None,
    current_candidate: object | None = None,
    source_cv: object | None = None,
    library: Sequence[object] = (),
    user_confirmed_facts: Sequence[Mapping[str, Any]] = (),
    render_warnings: Sequence[str] = (),
    inference_notes: Sequence[TailoringInferenceNote] = (),
    user_instructions: str | None = None,
    pass_number: int = 1,
) -> TailoringEvaluation:
    """Aggregate scanner facts into a bounded, issue-driven evaluation.

    ``requirements`` is expected to be the session's frozen extraction.  The
    function deliberately accepts it as an argument and never calls an
    extractor.
    """

    if candidate_scan.requirement_extraction != requirements:
        raise ValueError("candidate scan does not use the frozen requirement extraction")
    if source_scan is not None and source_scan.requirement_extraction != requirements:
        raise ValueError("source scan does not use the frozen requirement extraction")
    if previous_candidate_scan is not None and previous_candidate_scan.requirement_extraction != requirements:
        raise ValueError("previous candidate scan does not use the frozen requirement extraction")

    requirement_by_id = {item.id: item for item in requirements.requirements}
    improvements: list[TailoringIssue] = []
    regressions: list[TailoringIssue] = []
    blockers: list[TailoringIssue] = []
    review_items: list[TailoringIssue] = []
    recommendations: list[TailoringIssue] = []
    non_actionable_gaps: list[TailoringIssue] = []
    revise_needed = False

    source_semantic = _semantic_map(source_scan)
    candidate_semantic = _semantic_map(candidate_scan)
    requirement_transitions: list[TailoringRequirementTransition] = []
    for requirement_id, requirement in requirement_by_id.items():
        source_status = _value(source_semantic.get(requirement_id), "status")
        candidate_status = _value(candidate_semantic.get(requirement_id), "status")
        if source_status is not None and candidate_status is not None:
            classification = _classify_semantic(source_status, candidate_status)
            requirement_transitions.append(
                TailoringRequirementTransition(
                    requirement_id=requirement_id,
                    importance=requirement.importance,
                    source_status=source_status,
                    candidate_status=candidate_status,
                    classification=classification,  # type: ignore[arg-type]
                    label=_requirement_label(requirement),
                )
            )
            if classification == "improved":
                _add_issue(
                    improvements,
                    _issue(
                        issue_id=f"semantic-improved-{requirement_id}",
                        kind="review",
                        category="semantic",
                        message=f"{_requirement_label(requirement)}: {_enum_value(source_status)} → {_enum_value(candidate_status)}",
                        requirement_id=requirement_id,
                        importance=requirement.importance,
                    ),
                )
            elif classification == "regressed":
                regression = _issue(
                    issue_id=f"semantic-regressed-{requirement_id}",
                    kind="review",
                    category="comparison",
                    message=f"{_requirement_label(requirement)}: {_enum_value(source_status)} → {_enum_value(candidate_status)}",
                    detail="This is a source trade-off to review, not an automatic instruction to restore the source wording.",
                    priority="high" if requirement.importance is RequirementImportance.REQUIRED else "normal",
                    requirement_id=requirement_id,
                    importance=requirement.importance,
                )
                _add_issue(regressions, regression)
                _add_issue(
                    recommendations,
                    regression.model_copy(
                        update={
                            "id": f"restore-recommendation-{requirement_id}",
                            "kind": "recommendation",
                            "category": "comparison",
                            "message": f"Review whether {_requirement_label(requirement)} should be restored; strong source evidence was omitted.",
                        }
                    ),
                )
                if requirement.importance is RequirementImportance.REQUIRED:
                    revise_needed = True
            elif classification == "changed_needs_review":
                _add_issue(
                    review_items,
                    _issue(
                        issue_id=f"semantic-changed-{requirement_id}",
                        kind="review",
                        category="semantic",
                        message=f"{_requirement_label(requirement)} changed from {_enum_value(source_status)} to {_enum_value(candidate_status)}; review the interpretation.",
                        priority="high" if candidate_status is EvidenceStatus.CONFLICTING else "normal",
                        requirement_id=requirement_id,
                        importance=requirement.importance,
                    ),
                )

        if candidate_status is EvidenceStatus.NOT_EVIDENCED:
            if source_status in {EvidenceStatus.SUPPORTED, EvidenceStatus.PARTIAL}:
                # The transition above already carries the regression.  Keep
                # the action contextual rather than calling the gap a defect.
                pass
            elif source_status in {EvidenceStatus.CONFLICTING, EvidenceStatus.UNVERIFIABLE}:
                _add_issue(
                    review_items,
                    _issue(
                        issue_id=f"semantic-gap-review-{requirement_id}",
                        kind="review",
                        category="semantic",
                        message=f"{_requirement_label(requirement)} remains unresolved by the scanner; review the supplied evidence before changing the claim.",
                        requirement_id=requirement_id,
                        importance=requirement.importance,
                    ),
                )
            else:
                _add_issue(
                    non_actionable_gaps,
                    _issue(
                        issue_id=f"semantic-gap-{requirement_id}",
                        kind="non_actionable_gap",
                        category="semantic",
                        message=f"Genuine qualification gap: {_requirement_label(requirement)} has no supplied candidate evidence.",
                        detail="Do not keep rewriting the CV to fill this gap unless additional accurate evidence becomes available.",
                        priority="normal",
                        requirement_id=requirement_id,
                        importance=requirement.importance,
                    ),
                )
        elif candidate_status is EvidenceStatus.CONFLICTING:
            _add_issue(
                review_items,
                _issue(
                    issue_id=f"semantic-conflict-{requirement_id}",
                    kind="review",
                    category="semantic",
                    message=f"Scanner found conflicting evidence for {_requirement_label(requirement)}; inspect the claim and constraints.",
                    priority="high" if requirement.importance is RequirementImportance.REQUIRED else "normal",
                    requirement_id=requirement_id,
                    importance=requirement.importance,
                ),
            )
        elif candidate_status is EvidenceStatus.UNVERIFIABLE:
            _add_issue(
                review_items,
                _issue(
                    issue_id=f"semantic-unverifiable-{requirement_id}",
                    kind="review",
                    category="semantic",
                    message=f"The scanner could not verify {_requirement_label(requirement)}; keep the claim appropriately scoped.",
                    requirement_id=requirement_id,
                    importance=requirement.importance,
                ),
            )

    source_lexical = _lexical_map(source_scan)
    candidate_lexical = _lexical_map(candidate_scan)
    keyword_transitions: list[TailoringKeywordTransition] = []
    for term_id in sorted(set(source_lexical) | set(candidate_lexical)):
        candidate_term = candidate_lexical.get(term_id)
        source_term = source_lexical.get(term_id)
        source_visibility = _value(source_term, "visibility") if source_term is not None else None
        candidate_visibility = _value(candidate_term, "visibility") if candidate_term is not None else None
        semantic_support = (
            _value(candidate_term, "semantic_support")
            if candidate_term is not None
            else _value(source_term, "semantic_support")
        )
        if source_visibility is not None:
            classification = (
                _classify_keyword(source_visibility, candidate_visibility)
                if candidate_visibility is not None
                else "changed_needs_review"
            )
            keyword_transitions.append(
                TailoringKeywordTransition(
                    term_id=term_id,
                    term=str(_value(candidate_term, "term") or _value(source_term, "term") or term_id),
                    source_visibility=source_visibility,
                    candidate_visibility=candidate_visibility,
                    semantic_support=semantic_support,
                    classification=classification,  # type: ignore[arg-type]
                )
            )
            term_label = str(_value(candidate_term, "term") or _value(source_term, "term") or term_id)
            if classification == "improved":
                _add_issue(
                    improvements,
                    _issue(
                        issue_id=f"keyword-improved-{term_id}",
                        kind="review",
                        category="lexical",
                        message=f"{term_label}: {_enum_value(source_visibility)} → {_enum_value(candidate_visibility)}",
                        term_id=term_id,
                    ),
                )
            elif classification == "regressed":
                _add_issue(
                    regressions,
                    _issue(
                        issue_id=f"keyword-regressed-{term_id}",
                        kind="review",
                        category="comparison",
                        message=f"Lost employer wording: {term_label} {_enum_value(source_visibility)} → {_enum_value(candidate_visibility)}",
                        detail="Review this wording trade-off in context; do not restore it blindly.",
                        priority="high" if _value(candidate_term or source_term, "importance") is RequirementImportance.REQUIRED else "normal",
                        term_id=term_id,
                    ),
                )
            elif classification == "changed_needs_review":
                _add_issue(
                    review_items,
                    _issue(
                        issue_id=f"keyword-changed-{term_id}",
                        kind="review",
                        category="lexical",
                        message=f"{term_label} changed from {_enum_value(source_visibility)} to {_enum_value(candidate_visibility)}; review the wording.",
                        term_id=term_id,
                    ),
                )

        if candidate_term is not None and candidate_visibility is LexicalVisibility.ABSENT and not bool(_value(candidate_term, "illustrative_example", False)):
            if semantic_support in {EvidenceStatus.SUPPORTED, EvidenceStatus.PARTIAL}:
                _add_issue(
                    recommendations,
                    _issue(
                        issue_id=f"keyword-opportunity-{term_id}",
                        kind="recommendation",
                        category="lexical",
                        message=f"Consider using the employer's terminology '{_value(candidate_term, 'term')}' where it is accurate and natural.",
                        detail="The scanner found semantic support even though the literal term is absent.",
                        term_id=term_id,
                    ),
                )
            elif semantic_support is EvidenceStatus.NOT_EVIDENCED:
                _add_issue(
                    non_actionable_gaps,
                    _issue(
                        issue_id=f"keyword-gap-{term_id}",
                        kind="non_actionable_gap",
                        category="lexical",
                        message=f"Genuine wording/qualification gap: {_value(candidate_term, 'term')}",
                        detail="The scanner found no candidate evidence; do not add this term merely to raise visibility.",
                        term_id=term_id,
                    ),
                )

    candidate_quality = list(candidate_scan.presentation_quality.findings)
    source_quality = list(source_scan.presentation_quality.findings) if source_scan is not None else []
    for finding in candidate_quality:
        severity = _enum_value(finding.severity)
        location = finding.location.field_path if finding.location is not None else None
        if severity == FindingSeverity.ERROR.value:
            _add_issue(
                blockers,
                _issue(
                    issue_id=f"quality-error-{finding.code}-{location or 'document'}",
                    kind="blocker",
                    category="resume_quality",
                    message=finding.explanation,
                    code=finding.code,
                    priority="high",
                ),
            )
        elif severity == FindingSeverity.WARNING.value:
            _add_issue(
                review_items,
                _issue(
                    issue_id=f"quality-warning-{finding.code}-{location or 'document'}",
                    kind="review",
                    category="resume_quality",
                    message=finding.explanation,
                    code=finding.code,
                ),
            )
            revise_needed = True
        else:
            _add_issue(
                recommendations,
                _issue(
                    issue_id=f"quality-info-{finding.code}-{location or 'document'}",
                    kind="recommendation",
                    category="resume_quality",
                    message=finding.explanation,
                    code=finding.code,
                    priority="low",
                ),
            )

    candidate_pdf_checks = list(candidate_scan.pdf_recovery.checks)
    for check in candidate_pdf_checks:
        status = _enum_value(check.status)
        if status == PDFRecoveryStatus.FAIL.value and check.code in _CRITICAL_PDF_CHECKS:
            _add_issue(
                blockers,
                _issue(
                    issue_id=f"pdf-critical-{check.code}",
                    kind="blocker",
                    category="pdf_recovery",
                    message=check.explanation or f"Critical PDF recovery failure: {check.code}",
                    detail="Aergia could not reliably recover a critical part of the rendered candidate.",
                    priority="high",
                    code=check.code,
                ),
            )
        elif status in {PDFRecoveryStatus.FAIL.value, PDFRecoveryStatus.WARNING.value}:
            _add_issue(
                review_items,
                _issue(
                    issue_id=f"pdf-review-{check.code}",
                    kind="review",
                    category="pdf_recovery",
                    message=check.explanation or f"PDF recovery needs review: {check.code}",
                    code=check.code,
                ),
            )
        elif status == PDFRecoveryStatus.UNAVAILABLE.value:
            _add_issue(
                review_items,
                _issue(
                    issue_id=f"pdf-unavailable-{check.code}",
                    kind="review",
                    category="pdf_recovery",
                    message=check.explanation or "PDF recovery was unavailable for this candidate.",
                    code=check.code,
                ),
            )

    for finding in _ats_findings(candidate_scan):
        severity = _enum_value(_value(finding, "severity"))
        finding_id = str(_value(finding, "id") or "ats-finding")
        if severity == "pass":
            continue
        # PDF findings are projections of the observed PDF checks and would
        # otherwise duplicate their blocker/review classification.
        if finding_id.startswith("pdf-"):
            continue
        message = str(_value(finding, "action") or _value(finding, "explanation") or "ATS guidance needs review.")
        detail = _value(finding, "explanation")
        if severity == "recommendation":
            _add_issue(
                recommendations,
                _issue(
                    issue_id=f"ats-recommendation-{finding_id}",
                    kind="recommendation",
                    category="ats",
                    message=message,
                    detail=str(detail) if detail else None,
                    code=finding_id,
                ),
            )
        elif severity == "warning":
            _add_issue(
                review_items,
                _issue(
                    issue_id=f"ats-warning-{finding_id}",
                    kind="review",
                    category="ats",
                    message=message,
                    detail=str(detail) if detail else None,
                    priority="high" if _value(finding, "category") in {"parsing", "headings"} else "normal",
                    code=finding_id,
                ),
            )
            revise_needed = True
        else:
            _add_issue(
                review_items,
                _issue(
                    issue_id=f"ats-info-{finding_id}",
                    kind="review",
                    category="ats",
                    message=message,
                    detail=str(detail) if detail else None,
                    priority="low",
                    code=finding_id,
                ),
            )

    warning_list = [str(item).strip() for item in render_warnings if str(item).strip()]
    for index, warning in enumerate(warning_list[:50]):
        _add_issue(
            review_items,
            _issue(
                issue_id=f"render-warning-{index}",
                kind="review",
                category="render",
                message=warning,
            ),
        )

    normalized_inference_notes = [
        item if isinstance(item, TailoringInferenceNote) else TailoringInferenceNote.model_validate(item)
        for item in inference_notes
    ][:20]
    for index, note in enumerate(normalized_inference_notes):
        if note.review_recommended or note.confidence in {"reasonable", "speculative"}:
            _add_issue(
                review_items,
                _issue(
                    issue_id=f"inference-{index}-{sha256(note.claim.encode('utf-8')).hexdigest()[:12]}",
                    kind="review",
                    category="inference",
                    message=f"Inferred — verify: {note.claim}",
                    detail="Basis: " + "; ".join(note.basis),
                    priority="high" if note.confidence == "speculative" else "normal",
                ),
            )

    candidate_text = _candidate_text(current_candidate) if current_candidate is not None else ""
    for index, (term, reason) in enumerate(_user_forbidden_terms(user_instructions)):
        if _contains_term(candidate_text, term):
            _add_issue(
                blockers,
                _issue(
                    issue_id=f"user-constraint-{index}",
                    kind="blocker",
                    category="user_constraint",
                    message=f"Explicit user instruction violated: '{term}' appears in the candidate.",
                    detail=reason,
                    priority="high",
                ),
            )

    authoritative_facts = build_authoritative_fact_index(
        source_cv=source_cv,
        library=library,
        user_confirmed_facts=user_confirmed_facts,
    )
    candidate_employers = _employers(current_candidate) if current_candidate is not None else set()
    for employer in sorted(candidate_employers - authoritative_facts.employers):
        _add_issue(
            blockers,
            _issue(
                issue_id=f"fabricated-employer-{re.sub(r'[^a-z0-9]+', '-', employer).strip('-')[:120]}",
                kind="blocker",
                category="fabrication",
                message=f"Candidate employer '{employer}' is not present in the supplied authoritative evidence.",
                detail="Employer identity is a high-risk factual claim; add it only when authoritative evidence supports it.",
                priority="high",
            ),
        )

    source_comparison = TailoringSourceComparison(
        available=source_scan is not None,
        requirement_transitions=requirement_transitions,
        keyword_transitions=keyword_transitions,
    )

    previous_comparison = TailoringPreviousPassComparison(
        available=previous_candidate_scan is not None,
        previous_candidate_hash=previous_candidate_hash,
        candidate_hash=candidate_hash,
        changes=(
            _transition_changes(previous_candidate_scan, candidate_scan, requirement_by_id)
            if previous_candidate_scan is not None
            else []
        ),
        job_fit_delta=(
            _summary_score(candidate_scan, "semantic") - _summary_score(previous_candidate_scan, "semantic")
            if _summary_score(candidate_scan, "semantic") is not None and _summary_score(previous_candidate_scan, "semantic") is not None
            else None
        ),
        term_visibility_delta=(
            _summary_score(candidate_scan, "lexical") - _summary_score(previous_candidate_scan, "lexical")
            if _summary_score(candidate_scan, "lexical") is not None and _summary_score(previous_candidate_scan, "lexical") is not None
            else None
        ),
    )

    source_quality_counts = _count_findings(source_quality)
    candidate_quality_counts = _count_findings(candidate_quality)
    source_ats = _ats_findings(source_scan)
    candidate_ats = _ats_findings(candidate_scan)
    dimensions = TailoringDimensions(
        job_fit=TailoringNumericDimension(
            source=_summary_score(source_scan, "semantic"),
            candidate=_summary_score(candidate_scan, "semantic"),
        ),
        keywords=TailoringNumericDimension(
            source=_summary_score(source_scan, "lexical"),
            candidate=_summary_score(candidate_scan, "lexical"),
        ),
        ats=_dimension_counts(source_ats, candidate_ats, ats=True),
        resume_quality=candidate_quality_counts.model_copy(update={"source_count": source_quality_counts.candidate_count}),
        pdf_recovery=TailoringNumericDimension(
            source=_summary_score(source_scan, "pdf_recovery"),
            candidate=_summary_score(candidate_scan, "pdf_recovery"),
        ),
    )

    if blockers:
        readiness = TailoringReadiness(
            status="blocked",
            submission_allowed=False,
            reasons=[item.message for item in blockers[:20]],
        )
    elif revise_needed:
        readiness = TailoringReadiness(
            status="revise",
            submission_allowed=False,
            reasons=[
                "Concrete fixable issues remain; make a reasonable revision if it improves the candidate.",
                *[item.message for item in review_items[:5]],
                *[item.message for item in recommendations[:5]],
            ][:20],
        )
    elif review_items or recommendations or non_actionable_gaps or normalized_inference_notes:
        readiness = TailoringReadiness(
            status="ready_with_review",
            submission_allowed=True,
            reasons=[
                "The candidate is mechanically sound; review the surfaced inferences, recommendations, and genuine gaps.",
                *[item.message for item in review_items[:5]],
                *[item.message for item in non_actionable_gaps[:5]],
            ][:20],
        )
    else:
        readiness = TailoringReadiness(
            status="ready",
            submission_allowed=True,
            reasons=["No meaningful server-owned issue remains."],
        )

    return TailoringEvaluation(
        version=TAILORING_EVALUATION_VERSION,
        candidate_hash=candidate_hash,
        pass_number=max(1, min(5, pass_number)),
        source_comparison=source_comparison,
        previous_pass_comparison=previous_comparison,
        dimensions=dimensions,
        improvements=improvements,
        regressions=regressions,
        blockers=blockers,
        review_items=review_items,
        recommendations=recommendations,
        non_actionable_gaps=non_actionable_gaps,
        inference_notes=normalized_inference_notes,
        render_warnings=warning_list,
        readiness=readiness,
    )


__all__ = ["AuthoritativeFactIndex", "build_authoritative_fact_index", "evaluate_tailoring"]
