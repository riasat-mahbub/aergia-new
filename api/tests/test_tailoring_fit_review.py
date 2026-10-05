"""Binding validation for advisory protocol-v10 fit-review reports."""

import pytest
from pydantic import ValidationError

from app.http_schemas.tailoring_fit_review import (
    FitReviewCompleted,
    FitReviewSkippedExplicitly,
    FitReviewUnavailable,
)
from app.services.tailoring_fit_review import (
    FitReviewBindingError,
    validate_fit_review_binding,
)


_EVALUATION_ID = "evaluation_0123456789abcdef"
_CANDIDATE_HASH = "a" * 64
_PDF_SHA256 = "b" * 64


def _report(status: str = "completed") -> dict:
    binding = {
        "version": "fit-review-v1",
        "evaluation_id": _EVALUATION_ID,
        "candidate_hash": _CANDIDATE_HASH,
        "pdf_sha256": _PDF_SHA256,
    }
    if status == "completed":
        return binding | {
            "status": "completed",
            "mode": "fresh_agent",
            "verdict": "generic",
            "rationale": "The PDF lists relevant tools without tying them to the role's main work.",
            "strong_connections": ["Python API experience"],
            "weak_or_missing_connections": ["Production support ownership"],
            "recommended_changes": ["Connect the API example to a listed responsibility."],
        }
    return binding | {"status": status, "reason": "Independent PDF inspection was unavailable."}


def _selected_binding() -> dict[str, str]:
    return {
        "selected_evaluation_id": _EVALUATION_ID,
        "selected_candidate_hash": _CANDIDATE_HASH,
        "selected_pdf_sha256": _PDF_SHA256,
    }


@pytest.mark.parametrize(
    ("status", "expected_type"),
    [
        ("completed", FitReviewCompleted),
        ("unavailable", FitReviewUnavailable),
        ("skipped_explicitly", FitReviewSkippedExplicitly),
    ],
)
def test_accepts_every_advisory_status_when_all_ledger_bindings_match(status: str, expected_type: type):
    parsed = validate_fit_review_binding(_report(status), **_selected_binding())

    assert isinstance(parsed, expected_type)
    if status == "completed":
        assert parsed.verdict == "generic"


def test_missing_report_is_advisory_not_run():
    assert validate_fit_review_binding(None, **_selected_binding()) is None


@pytest.mark.parametrize(
    ("binding_name", "replacement"),
    [
        ("evaluation_id", "evaluation_fedcba9876543210"),
        ("candidate_hash", "c" * 64),
        ("pdf_sha256", "d" * 64),
    ],
)
def test_rejects_a_report_bound_to_another_evaluation_or_artifact(binding_name: str, replacement: str):
    report = _report() | {binding_name: replacement}

    with pytest.raises(FitReviewBindingError) as exc_info:
        validate_fit_review_binding(report, **_selected_binding())

    assert exc_info.value.code == "evaluation_mismatch"
    assert str(exc_info.value) == "Fit review does not match the selected immutable preview"


@pytest.mark.parametrize(
    ("selected_field", "replacement"),
    [
        ("selected_evaluation_id", "bad-id"),
        ("selected_candidate_hash", "not-a-hash"),
        ("selected_pdf_sha256", "not-a-hash"),
    ],
)
def test_rejects_an_invalid_selected_ledger_binding(selected_field: str, replacement: str):
    selected = _selected_binding() | {selected_field: replacement}

    with pytest.raises(FitReviewBindingError):
        validate_fit_review_binding(_report(), **selected)


def test_keeps_frozen_dto_shape_errors_distinct_from_binding_conflicts():
    report = _report() | {"unexpected_source_id": "source-secret"}

    with pytest.raises(ValidationError):
        validate_fit_review_binding(report, **_selected_binding())
