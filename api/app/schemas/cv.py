"""CV wire schema — request / response models for the CV endpoints.

The CV wire shape carries the new :class:`SectionInstance` list, so
type-aware data validation lives in the new ``app.schema`` package.
``legacy_style`` round-trips through the builder, which normalises the
legacy ``SectionStyle`` into the three-axis shape per the ADR mapping
table.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schema.models import Customizations, SectionInstance
from app.schemas.application import ApplicationStatus, GenerationStatus


DEFAULT_SECTIONS: list[dict] = [
    {
        "id": "sec_profile",
        "type": "profile",
        "title": "Profile",
        "enabled": True,
        "data": {"name": "", "title": "", "email": "", "phone": "", "location": "", "summary": "", "photo_url": ""},
    }
]


class CVCreate(BaseModel):
    title: str = Field(max_length=255)
    description: str | None = Field(default=None, max_length=500)
    template_id: str = Field(default="generic-modern", max_length=100)
    sections: list[SectionInstance] | dict = Field(default=DEFAULT_SECTIONS, max_length=100)
    customizations: Customizations | dict | None = None
    extra_metadata: dict = Field(default_factory=dict, max_length=100)


class CVUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    template_id: str | None = Field(default=None, max_length=100)
    sections: list[SectionInstance] | dict | None = Field(default=None, max_length=100)
    customizations: Customizations | dict | None = None


class CVResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    title: str
    description: str | None
    template_id: str
    customizations: dict
    sections: list | dict
    extra_metadata: dict
    created_at: datetime
    updated_at: datetime


class CVApplicationSummary(BaseModel):
    id: str
    company: str
    role: str
    status: ApplicationStatus
    generation_status: GenerationStatus
    applied_at: datetime | None


class CVListItem(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    title: str
    template_id: str
    created_at: datetime
    updated_at: datetime
    application: CVApplicationSummary | None = None


__all__ = [
    "DEFAULT_SECTIONS",
    "CVCreate",
    "CVApplicationSummary",
    "CVListItem",
    "CVResponse",
    "CVUpdate",
]
