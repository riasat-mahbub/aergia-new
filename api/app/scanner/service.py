"""Composition root for the independent scanner analyses."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import date, datetime, timezone
from typing import Protocol

from app.scanner.analysis_links import link_lexical_semantic_support
from app.scanner.extraction import ScannerRequirementExtractor
from app.scanner.lexical import analyze_lexical_visibility
from app.scanner.matching import evaluate_semantic_coverage
from app.scanner.pdf_recovery import PDF_ANALYSIS_VERSION, analyze_pdf_recovery
from app.scanner.quality import QUALITY_VERSION, analyze_presentation_quality
from app.scanner.requirements import RequirementExtraction
from app.scanner.results import (
    AnalysisStatus,
    ScanInputFingerprints,
    ScanResult,
    SemanticAnalysis,
    ScannerVersions,
)
from app.scanner.scoring import (
    LEXICAL_SCORE_VERSION,
    PDF_SCORE_VERSION,
    SEMANTIC_SCORE_VERSION,
    score_lexical_analysis,
    score_pdf_recovery,
    score_semantic_analysis,
)
from app.services.requirement_extractor import RequirementExtractionError

MATCHER_VERSION = "requirement-match-v3"
LEXICAL_VERSION = "ats-lexical-v4"


class RequirementExtractor(Protocol):
    def extract(self, job_description: str) -> RequirementExtraction: ...


def _canonical_json(value: object) -> bytes:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")  # type: ignore[union-attr]
    elif hasattr(value, "sections"):
        value = {
            "sections": getattr(value, "sections"),
            "template_id": getattr(value, "template_id", None),
            "customizations": getattr(value, "customizations", None),
        }
    elif isinstance(value, Mapping):
        value = dict(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def fingerprint_scan_inputs(
    job_description: str,
    cv: object,
    *,
    pdf_bytes: bytes | None = None,
) -> ScanInputFingerprints:
    """Return stable fingerprints for the inputs consumed by scanner branches."""

    if not job_description or not job_description.strip():
        raise ValueError("job_description must not be blank")
    if cv is None:
        raise ValueError("cv must be provided")
    return ScanInputFingerprints(
        job_description_sha256=_sha256(job_description.encode("utf-8")),
        cv_content_sha256=_sha256(_canonical_json(cv)),
        pdf_sha256=_sha256(pdf_bytes) if pdf_bytes else None,
    )


class ScannerService:
    """Run requirement, semantic, lexical, presentation, and PDF analyses."""

    def __init__(self, extractor: RequirementExtractor | None = None) -> None:
        self.extractor = extractor or ScannerRequirementExtractor()

    def scan(
        self,
        job_description: str,
        cv: object,
        *,
        pdf_bytes: bytes | None = None,
        as_of: date | None = None,
    ) -> ScanResult:
        if not job_description or not job_description.strip():
            raise ValueError("job_description must not be blank")
        if cv is None:
            raise ValueError("cv must be provided")

        try:
            extraction = self.extractor.extract(job_description)
            semantic = evaluate_semantic_coverage(extraction.requirements, cv, as_of=as_of)
        except RequirementExtractionError:
            extractor_version = str(
                getattr(self.extractor, "extractor_version", "gliner2.5-structured-v3")
            )
            extraction = RequirementExtraction(
                status="failed",
                source_hash=_sha256(job_description.encode("utf-8")),
                extractor_version=extractor_version,
                warnings=["requirement_extraction_failed"],
            )
            semantic = SemanticAnalysis(status=AnalysisStatus.FAILED)
        lexical = analyze_lexical_visibility(job_description, cv)
        presentation = analyze_presentation_quality(cv)
        pdf_recovery = analyze_pdf_recovery(pdf_bytes, cv)
        semantic = semantic.model_copy(
            update={
                "summary": score_semantic_analysis(semantic, extraction.requirements),
            }
        )
        lexical = link_lexical_semantic_support(lexical, extraction.requirements, semantic)
        lexical = lexical.model_copy(update={"summary": score_lexical_analysis(lexical)})
        pdf_recovery = pdf_recovery.model_copy(
            update={"summary": score_pdf_recovery(pdf_recovery)}
        )
        return ScanResult(
            created_at=datetime.now(timezone.utc),
            input_fingerprints=fingerprint_scan_inputs(job_description, cv, pdf_bytes=pdf_bytes),
            versions=ScannerVersions(
                extractor_version=extraction.extractor_version,
                matcher_version=MATCHER_VERSION,
                lexical_version=LEXICAL_VERSION,
                quality_version=QUALITY_VERSION,
                pdf_analysis_version=PDF_ANALYSIS_VERSION,
                semantic_score_version=SEMANTIC_SCORE_VERSION,
                lexical_score_version=LEXICAL_SCORE_VERSION,
                pdf_score_version=PDF_SCORE_VERSION,
            ),
            requirement_extraction=extraction,
            semantic=semantic,
            lexical=lexical,
            presentation_quality=presentation,
            pdf_recovery=pdf_recovery,
        )


__all__ = ["LEXICAL_VERSION", "MATCHER_VERSION", "ScannerService", "fingerprint_scan_inputs"]
