"""Advisory independent PDF fit-review report for tailoring protocol v10."""

from __future__ import annotations

from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, field_validator


_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_EVALUATION_ID_PATTERN = r"^[A-Za-z0-9_-]{16,128}$"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _FitReviewBinding(_StrictModel):
    version: Literal["fit-review-v1"] = "fit-review-v1"
    evaluation_id: str = Field(min_length=16, max_length=128, pattern=_EVALUATION_ID_PATTERN)
    candidate_hash: str = Field(min_length=64, max_length=64, pattern=_SHA256_PATTERN)
    pdf_sha256: str = Field(min_length=64, max_length=64, pattern=_SHA256_PATTERN)


_Finding = Annotated[str, Field(min_length=1, max_length=500)]


class FitReviewCompleted(_FitReviewBinding):
    """A finished review of one selected, immutable preview PDF."""

    status: Literal["completed"]
    mode: Literal["fresh_agent", "manual_external"]
    verdict: Literal["tailored", "partially_tailored", "generic"]
    rationale: str = Field(min_length=1, max_length=1_200)
    strong_connections: list[_Finding] = Field(max_length=5)
    weak_or_missing_connections: list[_Finding] = Field(max_length=5)
    recommended_changes: list[_Finding] = Field(max_length=3)

    @field_validator("rationale")
    @classmethod
    def rationale_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("rationale must not be blank")
        return value


class FitReviewUnavailable(_FitReviewBinding):
    """A review could not be performed; this does not imply a positive result."""

    status: Literal["unavailable"]
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason")
    @classmethod
    def reason_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("reason must not be blank")
        return value


class FitReviewSkippedExplicitly(_FitReviewBinding):
    """An explicit instruction skipped this advisory review."""

    status: Literal["skipped_explicitly"]
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason")
    @classmethod
    def reason_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("reason must not be blank")
        return value


FitReviewReport: TypeAlias = Annotated[
    FitReviewCompleted | FitReviewUnavailable | FitReviewSkippedExplicitly,
    Field(discriminator="status"),
]


__all__ = [
    "FitReviewCompleted",
    "FitReviewReport",
    "FitReviewSkippedExplicitly",
    "FitReviewUnavailable",
]
