from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal, Optional


class ZoneStyle(BaseModel):
    """Arbitrary CSS styles for a zone (width, background-color, padding, etc.)."""

    width: Optional[str] = None
    background_color: Optional[str] = Field(None, alias="background-color")
    padding: Optional[str] = None
    # allow extra arbitrary keys
    class Config:
        extra = "allow"
        populate_by_name = True


class ZoneManifest(BaseModel):
    id: str
    label: Optional[str] = None
    row: int = 0
    styles: ZoneStyle = Field(default_factory=ZoneStyle)


class StyleVarSchema(BaseModel):
    """Declaration of a customizable global style variable."""

    key: str
    type: Literal["color", "font", "length", "enum"]
    label: str
    default: str
    options: Optional[list[str]] = None  # for enum


class Manifest(BaseModel):
    version: int = 1
    name: str
    zones: list[ZoneManifest] = Field(default_factory=list)
    placement: dict[str, str] = Field(default_factory=dict)
    global_style_schema: list[StyleVarSchema] = Field(
        default_factory=list, alias="globalStyleSchema"
    )
    assets: dict[str, str] = Field(default_factory=dict)
    section_schema: dict[str, dict] = Field(default_factory=dict, alias="sectionSchema")

    class Config:
        populate_by_name = True
        extra = "allow"


# Helper to generate JSON Schema for documentation / validation
def manifest_json_schema() -> dict:
    return Manifest.model_json_schema()