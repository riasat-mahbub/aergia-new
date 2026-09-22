"""Version and input diagnostics for persisted scanner results."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal, TypedDict

from app.scanner.extraction import configured_scanner_extractor_version
from app.scanner.pdf_recovery import PDF_ANALYSIS_VERSION
from app.scanner.ats_guidance import ATS_GUIDANCE_VERSION
from app.scanner.quality import QUALITY_VERSION
from app.scanner.scoring import (
    CLASSIFICATION_WARNING_VERSION,
    LEXICAL_SCORE_VERSION,
    PDF_SCORE_VERSION,
    SEMANTIC_SCORE_VERSION,
)
from app.scanner.service import LEXICAL_VERSION, MATCHER_VERSION, fingerprint_scan_inputs


class ScannerFreshness(TypedDict):
    current: bool
    reasons: list[str]


ApplicationScannerStatus = Literal["current", "stale", "not_scanned", "needs_rescan"]


_VERSION_REASON_NAMES = (
    ("extractor_version", "extractor_version_changed"),
    ("matcher_version", "matcher_version_changed"),
    ("lexical_version", "lexical_version_changed"),
    ("quality_version", "quality_version_changed"),
    ("pdf_analysis_version", "pdf_version_changed"),
    ("semantic_score_version", "semantic_score_version_changed"),
    ("lexical_score_version", "lexical_score_version_changed"),
    ("pdf_score_version", "pdf_score_version_changed"),
    ("classification_warning_version", "classification_warning_version_changed"),
    ("ats_guidance_version", "ats_guidance_version_changed"),
)


def scanner_result_freshness(
    result: object,
    job_description: str | None,
    cv: object | None,
    *,
    extractor_version: str | None = None,
    pdf_bytes: bytes | None = None,
    render_manifest: object | None = None,
) -> ScannerFreshness:
    """Explain whether a stored result matches current inputs and subsystem versions.

    This performs only canonical JSON fingerprinting and version comparison. It
    never runs the extractor, semantic matcher, PDF renderer, or PDF parser.
    """

    if result is None:
        return {"current": False, "reasons": ["missing_result"]}
    if not isinstance(result, Mapping) or result.get("schema_version") != "scanner-v1":
        return {"current": False, "reasons": ["malformed_result"]}

    fingerprints = result.get("input_fingerprints")
    versions = result.get("versions")
    if not isinstance(fingerprints, Mapping) or not isinstance(versions, Mapping):
        return {"current": False, "reasons": ["malformed_result"]}

    reasons: list[str] = []
    if not isinstance(job_description, str) or not job_description.strip():
        reasons.append("job_changed")
    if cv is None:
        reasons.append("cv_changed")

    if isinstance(job_description, str) and job_description.strip() and cv is not None:
        try:
            current = fingerprint_scan_inputs(
                job_description,
                cv,
                pdf_bytes=pdf_bytes,
                render_manifest=render_manifest,
            )
        except (TypeError, ValueError):
            reasons.append("malformed_result")
        else:
            if fingerprints.get("job_description_sha256") != current.job_description_sha256:
                reasons.append("job_changed")
            if fingerprints.get("cv_content_sha256") != current.cv_content_sha256:
                reasons.append("cv_changed")
            if pdf_bytes is not None or render_manifest is not None:
                stored_render_input = fingerprints.get("render_input_sha256")
                if stored_render_input is None:
                    # Results created before render-input provenance was
                    # introduced cannot prove that their PDF branch used the
                    # current renderer/template inputs.
                    reasons.append("render_input_missing")
                elif stored_render_input != current.render_input_sha256:
                    reasons.append("render_input_changed")
            if pdf_bytes is not None and fingerprints.get("pdf_sha256") != current.pdf_sha256:
                reasons.append("pdf_changed")

    expected_versions = {
        "matcher_version": MATCHER_VERSION,
        "lexical_version": LEXICAL_VERSION,
        "quality_version": QUALITY_VERSION,
        "pdf_analysis_version": PDF_ANALYSIS_VERSION,
        "semantic_score_version": SEMANTIC_SCORE_VERSION,
        "lexical_score_version": LEXICAL_SCORE_VERSION,
        "pdf_score_version": PDF_SCORE_VERSION,
        "classification_warning_version": CLASSIFICATION_WARNING_VERSION,
        "ats_guidance_version": ATS_GUIDANCE_VERSION,
    }
    if extractor_version is not None:
        expected_versions["extractor_version"] = extractor_version

    for name, reason in _VERSION_REASON_NAMES:
        expected = expected_versions.get(name)
        if expected is not None and versions.get(name) != expected:
            # Pre-ATS scanner-v1 rows predate the guidance branch. They remain
            # readable and are refreshed by the explicit ATS backfill, while
            # results that already carry the branch are checked normally.
            if name == "ats_guidance_version" and "ats_guidance_version" not in versions and result.get("ats_guidance") is None:
                continue
            reasons.append(reason)

    return {"current": not reasons, "reasons": reasons}


def configured_extractor_version() -> str | None:
    """Return the current model+normalizer identity without loading inference."""

    return configured_scanner_extractor_version()


def application_scanner_status(
    result: object,
    job_description: str | None,
    cv: object | None,
    *,
    rescan_required: bool = False,
    extractor_version: str | None = None,
    pdf_bytes: bytes | None = None,
    render_manifest: object | None = None,
) -> ApplicationScannerStatus:
    """Return the user-facing scanner lifecycle state for an application."""

    if result is None:
        return "needs_rescan" if rescan_required else "not_scanned"
    freshness = scanner_result_freshness(
        result,
        job_description,
        cv,
        extractor_version=extractor_version,
        pdf_bytes=pdf_bytes,
        render_manifest=render_manifest,
    )
    return "current" if freshness["current"] else "stale"


__all__ = [
    "ApplicationScannerStatus",
    "ScannerFreshness",
    "application_scanner_status",
    "configured_extractor_version",
    "scanner_result_freshness",
]
