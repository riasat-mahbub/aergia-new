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
    CLASSIFICATION_WARNING_VERSION,
    LEXICAL_SCORE_VERSION,
    PDF_SCORE_VERSION,
    SEMANTIC_SCORE_VERSION,
    score_lexical_analysis,
    score_pdf_recovery,
    score_semantic_analysis,
)
from app.services.requirement_extractor import RequirementExtractionError

MATCHER_VERSION = "requirement-match-v4"
LEXICAL_VERSION = "ats-lexical-v5"
# Bump when renderer code changes in a way that can alter PDF output while
# the canonical CV payload and template manifest remain unchanged.
PDF_RENDERER_VERSION = "aergia-pdf-render-v1"


class RequirementExtractor(Protocol):
    def extract(self, job_description: str) -> RequirementExtraction: ...


def canonicalize_scanner_cv(value: object) -> dict[str, object]:
    """Return the document payload consumed by scanner branches.

    CV ORM objects and tailoring candidates expose different metadata (IDs,
    revisions, descriptions, and lifecycle fields).  Scanner fingerprints
    must describe the document itself, so only the renderer inputs are kept.
    """

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
    if not isinstance(value, Mapping):
        raise TypeError("cv must be a CV mapping or object")
    def strip_none(item: object) -> object:
        if isinstance(item, Mapping):
            return {key: strip_none(child) for key, child in item.items() if child is not None}
        if isinstance(item, list):
            return [strip_none(child) for child in item]
        return item

    return {
        "sections": strip_none(value.get("sections") or []),
        "template_id": value.get("template_id"),
        "customizations": strip_none(value.get("customizations") or {}),
    }


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        canonicalize_scanner_cv(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def scanner_versions_for_extraction(extraction: RequirementExtraction) -> ScannerVersions:
    """Build the complete scanner version set for a frozen extraction."""

    return ScannerVersions(
        extractor_version=extraction.extractor_version,
        matcher_version=MATCHER_VERSION,
        lexical_version=LEXICAL_VERSION,
        quality_version=QUALITY_VERSION,
        pdf_analysis_version=PDF_ANALYSIS_VERSION,
        semantic_score_version=SEMANTIC_SCORE_VERSION,
        lexical_score_version=LEXICAL_SCORE_VERSION,
        pdf_score_version=PDF_SCORE_VERSION,
        classification_warning_version=CLASSIFICATION_WARNING_VERSION,
    )


def fingerprint_scan_inputs(
    job_description: str,
    cv: object,
    *,
    pdf_bytes: bytes | None = None,
    render_manifest: object | None = None,
) -> ScanInputFingerprints:
    """Return stable fingerprints for the inputs consumed by scanner branches."""

    if not job_description or not job_description.strip():
        raise ValueError("job_description must not be blank")
    if cv is None:
        raise ValueError("cv must be provided")
    render_input = {
        "cv": canonicalize_scanner_cv(cv),
        "manifest": render_manifest,
        "renderer_version": PDF_RENDERER_VERSION,
    }
    render_bytes = json.dumps(
        render_input,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return ScanInputFingerprints(
        job_description_sha256=_sha256(job_description.encode("utf-8")),
        cv_content_sha256=_sha256(_canonical_json(cv)),
        pdf_sha256=_sha256(pdf_bytes) if pdf_bytes else None,
        render_input_sha256=_sha256(render_bytes),
    )


class ScannerService:
    """Run requirement, semantic, lexical, presentation, and PDF analyses."""

    def __init__(self, extractor: RequirementExtractor | None = None) -> None:
        self.extractor = extractor or ScannerRequirementExtractor()

    def extract_requirements(self, job_description: str) -> RequirementExtraction:
        """Extract one versioned requirement interpretation for a job."""

        if not job_description or not job_description.strip():
            raise ValueError("job_description must not be blank")
        try:
            return self.extractor.extract(job_description)
        except RequirementExtractionError:
            extractor_version = str(
                getattr(self.extractor, "extractor_version", "gliner2.5-structured-v3")
            )
            return RequirementExtraction(
                status="failed",
                source_hash=_sha256(job_description.encode("utf-8")),
                extractor_version=extractor_version,
                warnings=["requirement_extraction_failed"],
            )

    def scan(
        self,
        job_description: str,
        cv: object,
        *,
        pdf_bytes: bytes | None = None,
        render_manifest: object | None = None,
        as_of: date | None = None,
    ) -> ScanResult:
        if not job_description or not job_description.strip():
            raise ValueError("job_description must not be blank")
        if cv is None:
            raise ValueError("cv must be provided")

        extraction = self.extract_requirements(job_description)
        return self.scan_with_extraction(
            job_description,
            cv,
            extraction,
            pdf_bytes=pdf_bytes,
            render_manifest=render_manifest,
            as_of=as_of,
        )

    def scan_with_extraction(
        self,
        job_description: str,
        cv: object,
        extraction: RequirementExtraction,
        *,
        pdf_bytes: bytes | None = None,
        render_manifest: object | None = None,
        as_of: date | None = None,
    ) -> ScanResult:
        """Evaluate a CV against an already-frozen requirement extraction.

        Tailoring sessions use this method so every preview and submission in
        one session shares the same model interpretation of the job.  The
        method deliberately does not call the extractor.
        """

        if not job_description or not job_description.strip():
            raise ValueError("job_description must not be blank")
        if cv is None:
            raise ValueError("cv must be provided")
        if not isinstance(extraction, RequirementExtraction):
            extraction = RequirementExtraction.model_validate(extraction)
        expected_source_hash = _sha256(job_description.encode("utf-8"))
        if extraction.source_hash != expected_source_hash:
            raise ValueError("requirement extraction does not match job description")

        if extraction.status == "failed":
            semantic = SemanticAnalysis(status=AnalysisStatus.FAILED)
        else:
            semantic = evaluate_semantic_coverage(extraction.requirements, cv, as_of=as_of)
        lexical = analyze_lexical_visibility(
            job_description,
            cv,
            requirements=extraction.requirements,
        )
        presentation = analyze_presentation_quality(cv)
        pdf_recovery = analyze_pdf_recovery(pdf_bytes, cv, render_manifest=render_manifest)
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
            input_fingerprints=fingerprint_scan_inputs(
                job_description,
                cv,
                pdf_bytes=pdf_bytes,
                render_manifest=render_manifest,
            ),
            versions=scanner_versions_for_extraction(extraction),
            requirement_extraction=extraction,
            semantic=semantic,
            lexical=lexical,
            presentation_quality=presentation,
            pdf_recovery=pdf_recovery,
        )


__all__ = [
    "LEXICAL_VERSION",
    "MATCHER_VERSION",
    "PDF_RENDERER_VERSION",
    "ScannerService",
    "canonicalize_scanner_cv",
    "fingerprint_scan_inputs",
    "scanner_versions_for_extraction",
]
