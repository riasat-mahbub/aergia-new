"""CV wire schema — request / response models for the CV endpoints.

The CV wire shape carries the new :class:`SectionInstance` list, so
type-aware data validation lives in the new ``app.schema`` package.
``legacy_style`` round-trips through the builder, which normalises the
legacy ``SectionStyle`` into the three-axis shape per the ADR mapping
table.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schema.models import Customizations, SectionInstance


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
    title: str
    description: str | None = None
    template_id: str = "generic-modern"
    sections: list[SectionInstance] | dict = DEFAULT_SECTIONS
    customizations: Customizations | dict | None = None
    extra_metadata: dict = {}


class CVUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    template_id: str | None = None
    sections: list[SectionInstance] | dict | None = None
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


class CVListItem(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    title: str
    template_id: str
    created_at: datetime
    updated_at: datetime


__all__ = [
    "DEFAULT_SECTIONS",
    "CVCreate",
    "CVListItem",
    "CVResponse",
    "CVUpdate",
]
