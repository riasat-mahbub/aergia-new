"""Pydantic models for section instance data validation.

Maps to the TypeScript interfaces in web/src/lib/sections/types.ts.
"""

from typing import Literal

from pydantic import BaseModel


class ProfileData(BaseModel):
    name: str = ""
    title: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    summary: str = ""
    photo_url: str = ""


class ExperienceEntry(BaseModel):
    id: str
    company: str = ""
    position: str = ""
    start_date: str = ""
    end_date: str | None = None
    current: bool = False
    location: str = ""
    description: str = ""


class EducationEntry(BaseModel):
    id: str
    institution: str = ""
    degree: str = ""
    start_date: str = ""
    end_date: str | None = None
    current: bool = False
    gpa: str = ""


class SkillGroup(BaseModel):
    id: str
    category: str = ""
    items: list[str] = []


class ProjectEntry(BaseModel):
    id: str
    name: str = ""
    url: str = ""
    link_text: str = ""
    start_date: str = ""
    end_date: str | None = None
    description: str = ""
    tech_stack: list[str] = []

class LanguageEntry(BaseModel):
    id: str
    language: str = ""
    proficiency: str = ""


class CertificationEntry(BaseModel):
    id: str
    name: str = ""
    issuer: str = ""
    date: str = ""
    credential_url: str = ""


class SectionStyle(BaseModel):
    font: str | None = None
    color: str | None = None
    weight: str | None = None
    text_align: Literal["left", "right", "center", "justify"] | None = None
    # show_title controls the section heading (e.g. "PROFILE" / "EXPERIENCE")
    # in the live preview and PDF. None means use the per-section default
    # (profile hides the heading, everything else shows it).
    show_title: bool | None = None


# Map section type → data model
SECTION_DATA_MODELS: dict[str, type[BaseModel] | list[type[BaseModel]]] = {
    "profile": ProfileData,
    "experience": [ExperienceEntry],
    "education": [EducationEntry],
    "skills": [SkillGroup],
    "projects": [ProjectEntry],
    "languages": [LanguageEntry],
    "certifications": [CertificationEntry],
}
