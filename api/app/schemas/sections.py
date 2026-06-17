"""Pydantic models for section instance data validation.

Maps to the TypeScript interfaces in web/src/lib/sections/types.ts.
"""

from typing import Literal

from pydantic import BaseModel, Field



class SocialLink(BaseModel):
    label: str = ""
    url: str = ""
    icon: str = ""  # SocialIconKey; validated by the editor dropdown

class ProfileData(BaseModel):
    name: str = ""
    title: str = ""
    email: str = ""
    email_link: bool = True
    phone: str = ""
    location: str = ""
    site_text: str = ""
    site_url: str = ""
    summary: str = ""
    photo_url: str = ""
    social_links: list[SocialLink] = Field(default_factory=list)

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
    summary: str = ""


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

class ResearchEntry(BaseModel):
    id: str
    title: str = ""
    paper_url: str = ""
    paper_link_text: str = ""
    description: str = ""
    publication_date: str = ""
    publication_value: str = ""

class FieldStyle(BaseModel):
    font: str | None = None
    size: str | None = None
    weight: str | None = None


class DateStyle(BaseModel):
    """Per-section date display format. Mirrors the TypeScript `DateStyle`
    in web/src/lib/sections/types.ts and the `DATE_STYLE_OPTIONS` list in
    web/src/lib/sections/DateField.tsx.
    """
    range_sep: str = " \u2013 "  # " – " (space + en-dash + space)
    model_config = {"extra": "allow"}

    key: str
    range_sep: str = "\u2013 "  # " – " (en-dash + space)


class SectionStyle(BaseModel):
    font: str | None = None
    color: str | None = None
    weight: str | None = None
    text_align: Literal["left", "right", "center", "justify"] | None = None
    show_title: bool | None = None
    layout: Literal["block", "inline"] | None = None
    field_styles: dict[str, FieldStyle] | None = None
    date_style: DateStyle | None = None
    # Accepts any CSS length string ("8px", "1rem", "0.5em", etc.). The UI
    # clamps to 0–24 px; the schema intentionally accepts arbitrary input so
    # programmatic customizations never 422.
    subsection_gap: str | None = None
    # Same semantics as subsection_gap but applies to profile's row layout.
    row_gap: str | None = None


# Map section type → data model
SECTION_DATA_MODELS: dict[str, type[BaseModel] | list[type[BaseModel]]] = {
    "profile": ProfileData,
    "experience": [ExperienceEntry],
    "education": [EducationEntry],
    "skills": [SkillGroup],
    "projects": [ProjectEntry],
    "languages": [LanguageEntry],
    "certifications": [CertificationEntry],
    "research": [ResearchEntry],
}
