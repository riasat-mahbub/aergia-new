"""Section renderer registry."""

from .profile import SECTION_LABELS as SECTION_LABELS, render_profile
from .experience import render_experience
from .education import render_education
from .skills import render_skills
from .projects import render_projects
from .languages import render_languages
from .certifications import render_certifications

SECTION_RENDERERS = {
    "profile": render_profile,
    "experience": render_experience,
    "education": render_education,
    "skills": render_skills,
    "projects": render_projects,
    "languages": render_languages,
    "certifications": render_certifications,
}


def render_section_preview(section_type: str, data: any) -> str:
    renderer = SECTION_RENDERERS.get(section_type)
    if not renderer:
        raise ValueError(f"Unknown section type: '{section_type}'")
    return renderer(data)