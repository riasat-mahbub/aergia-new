"""Server-owned tailoring evaluation fixtures and readiness semantics."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256

import pytest

from app.scanner.ats_results import AtsFinding, AtsGuidance, AtsGuidanceSummary
from app.scanner.requirements import (
    Requirement,
    RequirementExtraction,
    RequirementImportance,
)
from app.scanner.results import (
    AnalysisStatus,
    EvidenceStatus,
    JobTextLocation,
    LexicalScoreSummary,
    LexicalTerm,
    LexicalVisibility,
    PDFCheck,
    PDFRecoveryStatus,
    ScoreStatus,
)
from app.scanner.service import ScannerService
from app.services.tailoring_evaluation import evaluate_tailoring


JOB = "Python"
REQUIREMENT_ID = "req-python"
TERM_ID = "term-python"
CANDIDATE = {
    "template_id": "generic-minimal",
    "sections": [
        {
            "id": "profile",
            "type": "profile",
            "enabled": True,
            "data": {"name": "Ada", "summary": "Platform engineer"},
        },
        {
            "id": "experience",
            "type": "experience",
            "enabled": True,
            "data": [
                {
                    "id": "experience-1",
                    "company": "Example Corp",
                    "position": "Engineer",
                    "start_date": "2020",
                    "current": True,
                    "description": "Built Python services.",
                }
            ],
        },
    ],
    "customizations": {},
}


def _extraction(*, importance: RequirementImportance = RequirementImportance.REQUIRED) -> RequirementExtraction:
    source_hash = sha256(JOB.encode()).hexdigest()
    requirement = Requirement.model_validate(
        {
            "id": REQUIREMENT_ID,
            "source": {
                "original_text": JOB,
                "source_start": 0,
                "source_end": len(JOB),
                "extraction_confidence": 1.0,
                "extractor_version": "test-extractor-v1",
            },
            "importance": importance,
            "importance_confidence": 1.0,
            "family": "technical_skill",
            "weight": 1.0,
            "expression": {
                "kind": "leaf",
                "id": "python-leaf",
                "concept": {"name": JOB, "confidence": 1.0},
                "expectation": {"kind": "familiarity", "confidence": 1.0},
                "confidence": 1.0,
            },
        }
    )
    return RequirementExtraction(
        status="evaluated",
        source_hash=source_hash,
        extractor_version="test-extractor-v1",
        requirements=[requirement],
    )


class _FixedExtractor:
    def __init__(self, extraction: RequirementExtraction):
        self.extraction = extraction

    def extract(self, _job_description: str) -> RequirementExtraction:
        return self.extraction


def _scan(
    extraction: RequirementExtraction,
    *,
    semantic_status: EvidenceStatus = EvidenceStatus.NOT_EVIDENCED,
    lexical_visibility: LexicalVisibility = LexicalVisibility.ABSENT,
    semantic_support: EvidenceStatus = EvidenceStatus.NOT_EVIDENCED,
    job_fit: float = 0.52,
    visibility_score: float = 0.4,
    quality_findings: list[object] | None = None,
    pdf_checks: list[PDFCheck] | None = None,
    pdf_status: PDFRecoveryStatus = PDFRecoveryStatus.PASS,
    ats_guidance: AtsGuidance | None = None,
) -> object:
    scanner = ScannerService(extractor=_FixedExtractor(extraction))
    result = scanner.scan(JOB, CANDIDATE)
    semantic_item = result.semantic.requirements[0].model_copy(
        update={
            "status": semantic_status,
            "expression": result.semantic.requirements[0].expression.model_copy(update={"status": semantic_status}),
        }
    )
    semantic_summary = result.semantic.summary
    assert semantic_summary is not None
    semantic_summary = semantic_summary.model_copy(update={"job_fit": job_fit})
    lexical_term = LexicalTerm(
        id=TERM_ID,
        term=JOB,
        variants=["py"],
        importance=extraction.requirements[0].importance,
        source_locations=[JobTextLocation(source_start=0, source_end=len(JOB))],
        visibility=lexical_visibility,
        semantic_support=semantic_support,
    )
    lexical_summary = LexicalScoreSummary(
        status=ScoreStatus.AVAILABLE,
        visibility_score=visibility_score,
        scorable_fraction=1.0,
        exact_count=int(lexical_visibility is LexicalVisibility.EXACT),
        normalized_count=int(lexical_visibility is LexicalVisibility.NORMALIZED),
        variant_count=int(lexical_visibility is LexicalVisibility.VARIANT),
        absent_count=int(lexical_visibility is LexicalVisibility.ABSENT),
        unverifiable_count=int(lexical_visibility is LexicalVisibility.UNVERIFIABLE),
    )
    pdf_summary = result.pdf_recovery.summary
    assert pdf_summary is not None
    pdf_summary = pdf_summary.model_copy(
        update={
            "status": ScoreStatus.AVAILABLE,
            "recovery_score": 0.99,
            "scorable_fraction": 1.0,
            "scored_check_count": max(1, len(pdf_checks or [])),
            "unavailable_check_count": 0,
        }
    )
    return result.model_copy(
        update={
            "semantic": result.semantic.model_copy(update={"requirements": [semantic_item], "summary": semantic_summary}),
            "lexical": result.lexical.model_copy(update={"terms": [lexical_term], "summary": lexical_summary}),
            "presentation_quality": result.presentation_quality.model_copy(
                update={"status": AnalysisStatus.EVALUATED, "findings": quality_findings or []}
            ),
            "pdf_recovery": result.pdf_recovery.model_copy(
                update={"status": pdf_status, "checks": pdf_checks or [], "summary": pdf_summary}
            ),
            "ats_guidance": ats_guidance,
        }
    )


def _clean_scan(
    extraction: RequirementExtraction,
    *,
    semantic_status: EvidenceStatus = EvidenceStatus.NOT_EVIDENCED,
    lexical_visibility: LexicalVisibility = LexicalVisibility.ABSENT,
    semantic_support: EvidenceStatus = EvidenceStatus.NOT_EVIDENCED,
    job_fit: float = 0.52,
    visibility_score: float = 0.4,
) -> object:
    return _scan(
        extraction,
        semantic_status=semantic_status,
        lexical_visibility=lexical_visibility,
        semantic_support=semantic_support,
        job_fit=job_fit,
        visibility_score=visibility_score,
    )


def test_low_job_fit_and_term_visibility_describe_genuine_gaps_without_a_gate() -> None:
    extraction = _extraction()
    scan = _clean_scan(extraction, job_fit=0.45, visibility_score=0.40)

    evaluation = evaluate_tailoring(extraction, scan, "a" * 64)

    assert evaluation.dimensions.job_fit.candidate == 0.45
    assert evaluation.dimensions.keywords.candidate == 0.40
    assert evaluation.blockers == []
    assert evaluation.non_actionable_gaps
    assert evaluation.readiness.status == "ready_with_review"
    assert evaluation.readiness.submission_allowed is True


def test_supported_semantics_with_absent_employer_wording_are_a_recommendation() -> None:
    extraction = _extraction()
    scan = _clean_scan(
        extraction,
        semantic_status=EvidenceStatus.SUPPORTED,
        lexical_visibility=LexicalVisibility.ABSENT,
        semantic_support=EvidenceStatus.SUPPORTED,
    )

    evaluation = evaluate_tailoring(extraction, scan, "b" * 64)

    assert any(item.id == "keyword-opportunity-term-python" for item in evaluation.recommendations)
    assert evaluation.blockers == []
    assert evaluation.readiness.submission_allowed is True


def test_reasonable_inference_is_reviewable_but_not_blocked_by_not_evidenced() -> None:
    extraction = _extraction()
    scan = _clean_scan(extraction)
    note = {
        "claim": "Jest familiarity",
        "basis": ["React/TypeScript experience", "documented unit testing"],
        "confidence": "reasonable",
        "review_recommended": True,
    }

    evaluation = evaluate_tailoring(extraction, scan, "c" * 64, inference_notes=[note])

    assert evaluation.blockers == []
    assert any(item.category == "inference" for item in evaluation.review_items)
    assert evaluation.inference_notes[0].claim == "Jest familiarity"
    assert evaluation.readiness.submission_allowed is True


def test_explicit_user_correction_overrides_a_tool_inference() -> None:
    extraction = _extraction()
    scan = _clean_scan(extraction)
    candidate = deepcopy(CANDIDATE)
    candidate["sections"][0]["data"]["summary"] = "Jest testing"

    blocked = evaluate_tailoring(
        extraction,
        scan,
        "d" * 64,
        current_candidate=candidate,
        user_instructions="I used Vitest, not Jest.",
    )
    allowed_candidate = deepcopy(CANDIDATE)
    allowed_candidate["sections"][0]["data"]["summary"] = "Vitest testing"
    allowed = evaluate_tailoring(
        extraction,
        scan,
        "e" * 64,
        current_candidate=allowed_candidate,
        user_instructions="I used Vitest, not Jest.",
    )

    assert any(item.category == "user_constraint" for item in blocked.blockers)
    assert blocked.readiness.submission_allowed is False
    assert not any(item.category == "user_constraint" for item in allowed.blockers)


def test_high_risk_new_employer_is_blocked_without_banning_reframing() -> None:
    extraction = _extraction()
    scan = _clean_scan(extraction)
    source = deepcopy(CANDIDATE)
    candidate = deepcopy(CANDIDATE)
    candidate["sections"][1]["data"][0]["company"] = "Completely Different Inc."

    evaluation = evaluate_tailoring(
        extraction,
        scan,
        "f" * 64,
        current_candidate=candidate,
        source_cv=source,
    )

    assert any(item.category == "fabrication" for item in evaluation.blockers)
    assert evaluation.readiness.status == "blocked"


def test_source_regression_is_a_contextual_tradeoff_and_required_regression_is_prioritized() -> None:
    extraction = _extraction(importance=RequirementImportance.PREFERRED)
    source_scan = _clean_scan(extraction, semantic_status=EvidenceStatus.SUPPORTED, lexical_visibility=LexicalVisibility.EXACT)
    candidate_scan = _clean_scan(extraction)

    peripheral = evaluate_tailoring(extraction, candidate_scan, "1" * 64, source_scan=source_scan)

    assert peripheral.blockers == []
    assert peripheral.regressions
    assert peripheral.recommendations
    assert peripheral.readiness.submission_allowed is True

    required_extraction = _extraction()
    required_source = _clean_scan(required_extraction, semantic_status=EvidenceStatus.SUPPORTED)
    required_candidate = _clean_scan(required_extraction)
    central = evaluate_tailoring(required_extraction, required_candidate, "2" * 64, source_scan=required_source)

    assert central.blockers == []
    assert central.readiness.status == "revise"
    assert central.recommendations


def test_critical_pdf_failure_blocks_but_noncritical_link_failure_does_not() -> None:
    extraction = _extraction()
    critical = _scan(
        extraction,
        pdf_status=PDFRecoveryStatus.FAIL,
        pdf_checks=[PDFCheck(code="text_retention", status=PDFRecoveryStatus.FAIL, explanation="Text was lost.")],
    )
    noncritical = _scan(
        extraction,
        pdf_status=PDFRecoveryStatus.FAIL,
        pdf_checks=[PDFCheck(code="link_recovery", status=PDFRecoveryStatus.FAIL, explanation="One link was not recovered.")],
    )

    blocked = evaluate_tailoring(extraction, critical, "3" * 64)
    reviewable = evaluate_tailoring(extraction, noncritical, "4" * 64)

    assert any(item.category == "pdf_recovery" for item in blocked.blockers)
    assert blocked.readiness.submission_allowed is False
    assert reviewable.blockers == []
    assert reviewable.readiness.submission_allowed is True


def test_ats_informational_vendor_advice_is_not_a_blocker() -> None:
    extraction = _extraction()
    guidance = AtsGuidance(
        common_findings=[
            AtsFinding(
                id="workday-layout",
                rule_id="layout",
                title="Workday layout note",
                category="parsing",
                scope="platform_specific",
                severity="info",
                explanation="Workday generally recommends simpler layouts.",
            )
        ],
        summary=AtsGuidanceSummary(
            platforms_checked=1,
            common_pass_count=0,
            common_warning_count=0,
            recommendation_count=0,
            informational_count=1,
        ),
    )
    scan = _scan(extraction, ats_guidance=guidance)

    evaluation = evaluate_tailoring(extraction, scan, "5" * 64)

    assert evaluation.blockers == []
    assert any(item.category == "ats" for item in evaluation.review_items)
    assert evaluation.readiness.submission_allowed is True


def test_source_and_previous_pass_deltas_use_requirement_and_term_identity() -> None:
    extraction = _extraction()
    source = _clean_scan(extraction, semantic_status=EvidenceStatus.PARTIAL, lexical_visibility=LexicalVisibility.VARIANT)
    previous = _clean_scan(extraction, semantic_status=EvidenceStatus.PARTIAL, lexical_visibility=LexicalVisibility.VARIANT)
    candidate = _clean_scan(extraction, semantic_status=EvidenceStatus.SUPPORTED, lexical_visibility=LexicalVisibility.NORMALIZED)

    evaluation = evaluate_tailoring(
        extraction,
        candidate,
        "6" * 64,
        source_scan=source,
        previous_candidate_scan=previous,
        previous_candidate_hash="7" * 64,
    )

    assert evaluation.source_comparison.requirement_transitions[0].classification == "improved"
    assert evaluation.source_comparison.keyword_transitions[0].classification == "improved"
    assert evaluation.previous_pass_comparison.available is True
    assert {change.classification for change in evaluation.previous_pass_comparison.changes} >= {"fixed", "improved"}


def test_evaluation_rejects_scans_that_do_not_share_frozen_requirements() -> None:
    extraction = _extraction()
    scan = _clean_scan(extraction)
    other = _extraction(importance=RequirementImportance.PREFERRED)
    mismatched = scan.model_copy(update={"requirement_extraction": other})

    with pytest.raises(ValueError, match="frozen requirement extraction"):
        evaluate_tailoring(extraction, mismatched, "8" * 64)
