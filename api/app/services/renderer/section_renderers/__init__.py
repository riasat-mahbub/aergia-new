"""Section renderer registry."""

from .profile import SECTION_LABELS as SECTION_LABELS, render_profile
from .experience import render_experience
from .education import render_education
from .skills import render_skills
from .projects import render_projects
from .languages import render_languages
from .certifications import render_certifications
from .research import render_research

SECTION_RENDERERS = {
    "profile": render_profile,
    "experience": render_experience,
    "education": render_education,
    "skills": render_skills,
    "projects": render_projects,
    "languages": render_languages,
    "certifications": render_certifications,
    "research": render_research,
}


def render_section_preview(
    section_type: str,
    data: any,
    context: dict | None = None,
) -> str:
    """Render a single section's body HTML using the given template context.

    `context` is a dict with the keys:
        body_font: str      — body font family
        heading_font: str   — heading font family
        css_vars: dict[str, str] — resolved CSS variables for the template
    """
    renderer = SECTION_RENDERERS.get(section_type)
    if not renderer:
        raise ValueError(f"Unknown section type: '{section_type}'")
    return renderer(data, context or {})
