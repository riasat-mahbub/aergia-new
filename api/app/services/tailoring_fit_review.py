"""Binding checks for advisory protocol-v10 fit-review reports.

The HTTP DTO owns the report's closed shape and bounds. This module checks
that a valid report describes the selected immutable evaluation ledger row;
it does not score, reinterpret, or gate a review verdict.
"""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from pydantic import TypeAdapter

from app.http_schemas.tailoring_fit_review import FitReviewReport


_FIT_REVIEW_ADAPTER = TypeAdapter(FitReviewReport)
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_EVALUATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,128}$")


class FitReviewBindingError(ValueError):
    """A shaped fit-review report does not bind to the selected preview."""

    code = "evaluation_mismatch"


def validate_fit_review_binding(
    report: FitReviewReport | Mapping[str, Any] | None,
    *,
    selected_evaluation_id: str,
    selected_candidate_hash: str,
    selected_pdf_sha256: str,
) -> FitReviewReport | None:
    """Validate an optional report against its selected immutable preview.

    ``None`` is the advisory ``Not run`` case. A non-null value is first
    validated by the frozen P00 DTO; its three bindings must then exactly
    match the selected evaluation row. Shape errors remain Pydantic
    ``ValidationError`` instances, while binding mismatches raise
    ``FitReviewBindingError`` (HTTP conflict code ``evaluation_mismatch``).
    """

    if report is None:
        return None

    parsed = _FIT_REVIEW_ADAPTER.validate_python(report)
    if (
        _EVALUATION_ID_PATTERN.fullmatch(selected_evaluation_id) is None
        or _SHA256_PATTERN.fullmatch(selected_candidate_hash) is None
        or _SHA256_PATTERN.fullmatch(selected_pdf_sha256) is None
        or parsed.evaluation_id != selected_evaluation_id
        or parsed.candidate_hash != selected_candidate_hash
        or parsed.pdf_sha256 != selected_pdf_sha256
    ):
        raise FitReviewBindingError("Fit review does not match the selected immutable preview")
    return parsed


__all__ = ["FitReviewBindingError", "validate_fit_review_binding"]
