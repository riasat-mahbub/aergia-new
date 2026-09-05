"""HTTP and protocol schemas for local-agent tailoring."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.safe_url import normalize_http_url, normalize_url
from app.document_schema.models import SectionInstanceStyle, is_color_ref


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
    session_url: str = Field(min_length=1, max_length=2048)
    prompt: str = Field(min_length=1, max_length=5000)
    status: Literal["created"] = "created"
    expires_at: datetime


class TailoringExchangeResponse(_StrictModel):
    protocol_version: Literal[PROTOCOL_VERSION] = PROTOCOL_VERSION
    session_id: str
    expires_at: datetime
    capability: str


class TailoringReportedGap(_StrictModel):
    requirement: str
    reason: str


TailoringSessionState = Literal[
    "created",
    "exchanged",
    "submitted",
    "applied",
    "failed",
    "expired",
    "cancelled",
    "stale",
]


class TailoringSessionStatusResponse(_StrictModel):
    protocol_version: Literal[PROTOCOL_VERSION] = PROTOCOL_VERSION
    session_id: str
    application_id: str
    cv_id: str
    status: TailoringSessionState
    expires_at: datetime
    created_at: datetime
    exchanged_at: datetime | None = None
    submitted_at: datetime | None = None
    updated_at: datetime
    attempts: int = Field(ge=0)
    reported_gaps: list[TailoringReportedGap] = Field(default_factory=list, max_length=50)
    result: dict | None = None


class TailoringJob(_StrictModel):
    company: str
    role: str
    job_url: str | None = None
    description: str


class TailoringCV(_StrictModel):
    id: str
    title: str
    sections: list | dict


class TailoringSection(_StrictModel):
    """A complete section proposed by an auditable structural operation."""

    id: str = Field(min_length=1, max_length=128)
    type: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)
    enabled: bool = True
    data: list | dict = Field(default_factory=dict, max_length=100)
    style: SectionInstanceStyle | None = None

    @field_validator("id", "type", "title")
    @classmethod
    def trim_required_values(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("section values must not be blank")
        return value


class TailoringLibraryEntry(_StrictModel):
    id: str
    kind: str
    content_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    payload: list[dict]


class TailoringEvidencePacket(_StrictModel):
    """The source evidence and the empty document the agent must compose.

    ``cv`` remains the linked CV so existing content can be cited when useful,
    but it is not the write target. New sessions also include ``target_cv``:
    a fresh, server-owned section scaffold populated only with profile data.
    The successful submission creates a new persistent CV from that scaffold.
    ``target_cv`` is optional at the schema boundary so older fixture packets
    and older agents remain readable; the server always emits it.
    """

    protocol_version: Literal[PROTOCOL_VERSION] = PROTOCOL_VERSION
    session_id: str
    application_id: str
    cv_id: str
    expires_at: datetime
    base_revision: int = Field(ge=1)
    base_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    requirements_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    profile_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    supported_operations: list[str] = Field(min_length=1, max_length=32)
    job: TailoringJob
    cv: TailoringCV
    target_cv: TailoringCV | None = None
    profile: dict
    protected_facts: dict
    library: list[TailoringLibraryEntry] = Field(max_length=100)
    requirements: list[dict] = Field(max_length=100)


class TailoringEvidenceRef(_StrictModel):
    """A source location the local agent used for a prose change.

    CV and Library references are resolved against the exchanged snapshot.
    ``field_path="*"`` cites the complete source row, which is useful when a
    structural section replacement reuses several factual fields at once.
    Web references are citations supplied by the local agent: the server
    validates their URL and bounded citation fields, but does not fetch an
    untrusted page during a CV write.
    """

    source: Literal["cv", "library", "web"]
    field_path: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=r"^(?:\*|[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*)$",
    )
    section_id: str | None = Field(default=None, min_length=1, max_length=128)
    entry_id: str | None = Field(default=None, min_length=1, max_length=128)
    library_entry_id: str | None = Field(default=None, min_length=1, max_length=128)
    source_row_id: str | None = Field(default=None, min_length=1, max_length=128)
    source_hash: str | None = Field(
        default=None, min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$"
    )
    url: str | None = Field(default=None, max_length=2_048)
    title: str | None = Field(default=None, max_length=255)
    excerpt: str | None = Field(default=None, max_length=4_000)

    @field_validator("url", mode="before")
    @classmethod
    def validate_citation_url(cls, value: object) -> str | None:
        if value is None:
            return None
        normalized = normalize_http_url(value)
        if not normalized:
            raise ValueError("web citation url must be a safe HTTP(S) URL")
        return normalized

    @field_validator("title", "excerpt", mode="before")
    @classmethod
    def trim_citation_text(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @model_validator(mode="after")
    def validate_source_shape(self) -> "TailoringEvidenceRef":
        if self.source == "cv":
            if self.section_id is None or self.field_path is None:
                raise ValueError("CV evidence requires section_id and field_path")
            if any((self.library_entry_id, self.source_row_id, self.source_hash, self.url, self.title, self.excerpt)):
                raise ValueError("CV evidence cannot include Library or web citation fields")
        elif self.source == "library":
            if self.field_path is None:
                raise ValueError("Library evidence requires field_path")
            if not all((self.library_entry_id, self.source_row_id, self.source_hash)):
                raise ValueError("Library evidence requires entry, row, and source hash")
            if any((self.section_id, self.entry_id, self.url, self.title, self.excerpt)):
                raise ValueError("Library evidence cannot include CV or web citation fields")
        else:
            if not all((self.url, self.title, self.excerpt)):
                raise ValueError("Web evidence requires url, title, and excerpt")
            if any(
                (
                    self.field_path,
                    self.section_id,
                    self.entry_id,
                    self.library_entry_id,
                    self.source_row_id,
                    self.source_hash,
                )
            ):
                raise ValueError("Web evidence cannot include CV or Library identifiers")
        return self


class TailoringTextStyle(_StrictModel):
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strike: bool = False
    color: str | None = None
    link: str | None = None
    font_size: Literal["xs", "small", "normal", "large", "xl"] | None = None

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str | None) -> str | None:
        if value is not None and not is_color_ref(value):
            raise ValueError("color must be a hex literal or palette reference")
        return value

    @field_validator("link", mode="before")
    @classmethod
    def validate_link(cls, value: object) -> str | None:
        if value is None:
            return None
        normalized = normalize_url(value)
        if not normalized:
            raise ValueError("link must be a safe URL")
        return normalized


class TailoringRichTextItem(_StrictModel):
    id: str = Field(min_length=1, max_length=128)
    text: str = Field(max_length=20_000)
    style: TailoringTextStyle | None = None


class TailoringRichTextBlock(_StrictModel):
    id: str = Field(min_length=1, max_length=128)
    type: Literal["paragraph", "bullet_list", "numbered_list"] = "paragraph"
    items: list[TailoringRichTextItem] = Field(min_length=1, max_length=100)


class ReplaceDescriptionChange(_StrictModel):
    """Legacy Phase 1 operation retained for the fixed protocol smoke test."""

    operation: Literal["replace_description"]
    section_id: str = Field(min_length=1, max_length=128)
    entry_id: str = Field(min_length=1, max_length=128)
    value: str = Field(min_length=1, max_length=20_000)
    reason: str | None = Field(default=None, max_length=2_000)
    evidence: list[TailoringEvidenceRef] = Field(default_factory=list, max_length=20)

    @field_validator("section_id", "entry_id", "value")
    @classmethod
    def trim_required_values(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value


class ReplaceRichTextChange(_StrictModel):
    """Phase 1 prose replacement used by the installed tailoring skill."""

    operation: Literal["replace_rich_text"]
    section_id: str = Field(min_length=1, max_length=128)
    entry_id: str | None = Field(default=None, min_length=1, max_length=128)
    field: Literal["description", "summary"]
    value: str = Field(min_length=1, max_length=20_000)
    evidence: list[TailoringEvidenceRef] = Field(default_factory=list, max_length=20)
    reason: str | None = Field(default=None, max_length=2_000)

    @field_validator("section_id", "field", "value")
    @classmethod
    def trim_required_values(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value


class RewriteRichTextChange(_StrictModel):
    operation: Literal["rewrite_rich_text"]
    section_id: str = Field(min_length=1, max_length=128)
    entry_id: str | None = Field(default=None, min_length=1, max_length=128)
    field: Literal["description", "summary"]
    value: list[TailoringRichTextBlock] = Field(min_length=1, max_length=100)
    evidence: list[TailoringEvidenceRef] = Field(min_length=1, max_length=20)
    reason: str | None = Field(default=None, max_length=2_000)


class RemoveBulletChange(_StrictModel):
    operation: Literal["remove_bullet"]
    section_id: str = Field(min_length=1, max_length=128)
    entry_id: str | None = Field(default=None, min_length=1, max_length=128)
    field: Literal["description", "summary"]
    block_id: str = Field(min_length=1, max_length=128)
    item_id: str = Field(min_length=1, max_length=128)
    reason: str | None = Field(default=None, max_length=2_000)


class ReorderBulletsChange(_StrictModel):
    operation: Literal["reorder_bullets"]
    section_id: str = Field(min_length=1, max_length=128)
    entry_id: str | None = Field(default=None, min_length=1, max_length=128)
    field: Literal["description", "summary"]
    block_id: str = Field(min_length=1, max_length=128)
    item_ids: list[str] = Field(min_length=1, max_length=100)
    reason: str | None = Field(default=None, max_length=2_000)

    @field_validator("item_ids")
    @classmethod
    def validate_item_ids(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("item_ids must not contain blank values")
        if len(set(normalized)) != len(normalized):
            raise ValueError("item_ids must be unique")
        return normalized


class RemoveEntryChange(_StrictModel):
    operation: Literal["remove_entry"]
    section_id: str = Field(min_length=1, max_length=128)
    entry_id: str = Field(min_length=1, max_length=128)
    reason: str | None = Field(default=None, max_length=2_000)


class ReorderEntriesChange(_StrictModel):
    operation: Literal["reorder_entries"]
    section_id: str = Field(min_length=1, max_length=128)
    entry_ids: list[str] = Field(min_length=1, max_length=100)
    reason: str | None = Field(default=None, max_length=2_000)

    @field_validator("entry_ids")
    @classmethod
    def validate_entry_ids(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("entry_ids must not contain blank values")
        if len(set(normalized)) != len(normalized):
            raise ValueError("entry_ids must be unique")
        return normalized


class AddLibraryEntryChange(_StrictModel):
    operation: Literal["add_library_entry"]
    section_id: str = Field(min_length=1, max_length=128)
    # Optional so older agents can keep using server-generated IDs. Supplying
    # one lets a later prose operation in the same patch target the copied row.
    entry_id: str | None = Field(default=None, min_length=1, max_length=128)
    library_entry_id: str = Field(min_length=1, max_length=128)
    source_row_id: str = Field(min_length=1, max_length=128)
    evidence: list[TailoringEvidenceRef] = Field(min_length=1, max_length=20)
    reason: str | None = Field(default=None, max_length=2_000)


class CreateSectionChange(_StrictModel):
    operation: Literal["create_section"]
    section: TailoringSection
    reason: str = Field(min_length=1, max_length=2_000)
    evidence: list[TailoringEvidenceRef] = Field(min_length=1, max_length=20)

    @field_validator("reason")
    @classmethod
    def trim_reason(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("reason must not be blank")
        return value


class ReplaceSectionChange(_StrictModel):
    operation: Literal["replace_section"]
    section_id: str = Field(min_length=1, max_length=128)
    section: TailoringSection
    reason: str = Field(min_length=1, max_length=2_000)
    evidence: list[TailoringEvidenceRef] = Field(min_length=1, max_length=20)

    @field_validator("reason")
    @classmethod
    def trim_reason(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("reason must not be blank")
        return value

    @model_validator(mode="after")
    def section_id_matches_replacement(self) -> "ReplaceSectionChange":
        if self.section.id != self.section_id:
            raise ValueError("replacement section id must match section_id")
        return self


class RemoveSectionChange(_StrictModel):
    operation: Literal["remove_section"]
    section_id: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=2_000)
    evidence: list[TailoringEvidenceRef] = Field(min_length=1, max_length=20)

    @field_validator("reason")
    @classmethod
    def trim_reason(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("reason must not be blank")
        return value


class ReorderSectionsChange(_StrictModel):
    operation: Literal["reorder_sections"]
    section_ids: list[str] = Field(min_length=1, max_length=32)
    reason: str = Field(min_length=1, max_length=2_000)
    evidence: list[TailoringEvidenceRef] = Field(min_length=1, max_length=20)

    @field_validator("reason")
    @classmethod
    def trim_reason(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("reason must not be blank")
        return value

    @field_validator("section_ids")
    @classmethod
    def validate_section_ids(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("section_ids must not contain blank values")
        if len(set(normalized)) != len(normalized):
            raise ValueError("section_ids must be unique")
        return normalized


class ReportGapChange(_StrictModel):
    operation: Literal["report_gap"]
    requirement_id: str | None = Field(default=None, min_length=1, max_length=128)
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
    ReplaceDescriptionChange
    | ReplaceRichTextChange
    | RewriteRichTextChange
    | RemoveBulletChange
    | ReorderBulletsChange
    | RemoveEntryChange
    | ReorderEntriesChange
    | AddLibraryEntryChange
    | CreateSectionChange
    | ReplaceSectionChange
    | RemoveSectionChange
    | ReorderSectionsChange
    | ReportGapChange,
    Field(discriminator="operation"),
]


class TailoringPatch(_StrictModel):
    protocol_version: Literal[PROTOCOL_VERSION]
    base_revision: int = Field(ge=1)
    base_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    changes: list[TailoringChange] = Field(min_length=1, max_length=50)


class TailoringProvenance(_StrictModel):
    operation: str
    section_id: str | None = None
    entry_id: str | None = None
    field: str | None = None
    reason: str | None = None
    evidence: list[TailoringEvidenceRef] = Field(default_factory=list, max_length=20)


class TailoringSubmitResponse(_StrictModel):
    protocol_version: Literal[PROTOCOL_VERSION] = PROTOCOL_VERSION
    session_id: str
    application_id: str
    source_cv_id: str
    cv_id: str
    base_revision: int
    new_revision: int
    applied_operations: list[str]
    gaps: list[TailoringReportedGap]
    provenance: list[TailoringProvenance]
    before_relevance: dict
    relevance: dict


__all__ = [
    "PROTOCOL_VERSION",
    "AddLibraryEntryChange",
    "CreateSectionChange",
    "RemoveBulletChange",
    "RemoveEntryChange",
    "RemoveSectionChange",
    "ReorderBulletsChange",
    "ReorderEntriesChange",
    "ReorderSectionsChange",
    "ReportGapChange",
    "ReplaceDescriptionChange",
    "ReplaceRichTextChange",
    "RewriteRichTextChange",
    "TailoringChange",
    "TailoringCodeExchange",
    "TailoringCV",
    "TailoringEvidencePacket",
    "TailoringEvidenceRef",
    "TailoringExchangeResponse",
    "TailoringJob",
    "TailoringLibraryEntry",
    "TailoringPatch",
    "TailoringProvenance",
    "TailoringReportedGap",
    "TailoringRichTextBlock",
    "TailoringRichTextItem",
    "TailoringSessionCreateResponse",
    "TailoringSessionState",
    "TailoringSessionStatusResponse",
    "TailoringSection",
    "TailoringSubmitResponse",
    "TailoringTextStyle",
]
