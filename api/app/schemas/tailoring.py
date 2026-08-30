"""HTTP and protocol schemas for local-agent tailoring."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


PROTOCOL_VERSION = 1


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TailoringCodeExchange(_StrictModel):
    protocol_version: Literal[PROTOCOL_VERSION]
    code: str = Field(min_length=16, max_length=128)

    @field_validator("code")
    @classmethod
    def trim_code(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("code must not be blank")
        return value


class TailoringSessionCreateResponse(_StrictModel):
    protocol_version: Literal[PROTOCOL_VERSION] = PROTOCOL_VERSION
    session_id: str
    application_id: str
    cv_id: str
    code: str
    expires_at: datetime


class TailoringExchangeResponse(_StrictModel):
    protocol_version: Literal[PROTOCOL_VERSION] = PROTOCOL_VERSION
    session_id: str
    expires_at: datetime
    capability: str


class TailoringJob(_StrictModel):
    company: str
    role: str
    job_url: str | None = None
    description: str


class TailoringCV(_StrictModel):
    id: str
    title: str
    sections: list | dict


class TailoringLibraryEntry(_StrictModel):
    id: str
    kind: str
    payload: list[dict]


class TailoringEvidencePacket(_StrictModel):
    protocol_version: Literal[PROTOCOL_VERSION] = PROTOCOL_VERSION
    session_id: str
    application_id: str
    cv_id: str
    expires_at: datetime
    job: TailoringJob
    cv: TailoringCV
    profile: dict
    library: list[TailoringLibraryEntry] = Field(max_length=100)
    requirements: list[dict] = Field(max_length=100)


class ReplaceDescriptionChange(_StrictModel):
    operation: Literal["replace_description"]
    section_id: str = Field(min_length=1, max_length=128)
    entry_id: str = Field(min_length=1, max_length=128)
    value: str = Field(min_length=1, max_length=20_000)
    reason: str | None = Field(default=None, max_length=2_000)

    @field_validator("section_id", "entry_id", "value")
    @classmethod
    def trim_required_values(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value


class ReportGapChange(_StrictModel):
    operation: Literal["report_gap"]
    requirement: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=1, max_length=2_000)

    @field_validator("requirement", "reason")
    @classmethod
    def trim_gap_values(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value


TailoringChange = Annotated[
    ReplaceDescriptionChange | ReportGapChange,
    Field(discriminator="operation"),
]


class TailoringPatch(_StrictModel):
    protocol_version: Literal[PROTOCOL_VERSION]
    changes: list[TailoringChange] = Field(min_length=1, max_length=20)


class TailoringReportedGap(_StrictModel):
    requirement: str
    reason: str


class TailoringSubmitResponse(_StrictModel):
    protocol_version: Literal[PROTOCOL_VERSION] = PROTOCOL_VERSION
    session_id: str
    application_id: str
    cv_id: str
    applied_operations: list[str]
    gaps: list[TailoringReportedGap]
    relevance: dict


__all__ = [
    "PROTOCOL_VERSION",
    "ReportGapChange",
    "ReplaceDescriptionChange",
    "TailoringChange",
    "TailoringCodeExchange",
    "TailoringCV",
    "TailoringEvidencePacket",
    "TailoringExchangeResponse",
    "TailoringJob",
    "TailoringLibraryEntry",
    "TailoringPatch",
    "TailoringReportedGap",
    "TailoringSessionCreateResponse",
    "TailoringSubmitResponse",
]
