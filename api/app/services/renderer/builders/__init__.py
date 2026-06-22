"""AST builders — one per section type.

Each builder takes a wire :class:`SectionInstance` and emits a
:class:`Section` AST node. Builders do NOT apply styles; that's the
Resolver's job. They only emit ``FieldBlock``s.

The :func:`build_document` entry point walks ``cv.sections``, normalises
each instance's three-axis style via :func:`build_section_style`, and
dispatches to the per-type builder.

Each builder takes the wire :class:`SectionInstance` and emits a
:class:`Section` AST node. ``build_section_style`` overlays the per-instance
three-axis style onto the section.
"""

from __future__ import annotations

from app.schema.models import (
    Document,
    LayoutHints,
    Section,
    SectionInstance,
    SectionInstanceStyle,
    SectionPolicy,
    SubsectionStyle,
    TemplateManifest,
    TextStyle,
)

from .certifications import build_certifications
from .education import build_education
from .experience import build_experience
from .languages import build_languages
from .profile import build_profile
from .projects import build_projects
from .research import build_research
from .skills import build_skills


BUILDERS = {
    "profile": build_profile,
    "experience": build_experience,
    "education": build_education,
    "skills": build_skills,
    "projects": build_projects,
    "languages": build_languages,
    "certifications": build_certifications,
    "research": build_research,
}


def build_section_style(
    instance_type: str,
    instance_style: SectionInstanceStyle | None,
    manifest: TemplateManifest | None,
) -> tuple[SectionInstanceStyle, SectionPolicy]:
    """Resolve a :class:`SectionInstanceStyle` from the wire form.

    Layers the inputs in this order:

    1. ``instance_style`` (already three-axis).
    2. ``policy`` default from ``SECTION_POLICIES`` (overridden by
       ``manifest.policy_overrides.by_type``).

    Returns ``(style, policy)``. The style is the resolved three-axis
    shape; the policy is the resolved per-type policy.
    """

    # Start from the new shape (or empty).
    base = instance_style.model_dump() if instance_style else {}
    text: dict[str, TextStyle] = dict(base.get("text") or {})
    subsection_dict = base.get("subsection") or {}
    subsection = SubsectionStyle.model_validate(subsection_dict) if subsection_dict else SubsectionStyle()
    layout_dict = base.get("layout") or {}
    layout = LayoutHints.model_validate(layout_dict) if layout_dict else LayoutHints()
    policy_dict = base.get("policy")
    explicit_policy = SectionPolicy.model_validate(policy_dict) if policy_dict else None

    # Resolve the default policy unless the instance declared one.
    if explicit_policy is None:
        from app.services.renderer.policy import resolve_policy

        explicit_policy = resolve_policy(instance_type, manifest)

    style = SectionInstanceStyle(
        text=text,
        subsection=subsection,
        layout=layout,
        policy=explicit_policy,
    )
    return style, explicit_policy


def build_document(
    cv,
    manifest: TemplateManifest | None = None,
) -> Document:
    """Build a :class:`Document` AST from a CV's wire ``SectionInstance`` list.

    ``cv`` is a SQLAlchemy ``CV`` row; we only read ``cv.sections`` and
    ``cv.customizations`` to keep the builder dependency-light. ``manifest``
    is optional — when omitted, policy defaults from ``SECTION_POLICIES``
    still apply.
    """

    raw_sections = cv.sections if isinstance(cv.sections, list) else []

    sections: list[Section] = []
    for raw in raw_sections:
        if not isinstance(raw, dict):
            continue
        # Re-validate through the new SectionInstance shape; this catches
        # legacy rows that don't match the new wire format.
        instance = SectionInstance.model_validate(raw)
        if not instance.enabled:
            continue
        builder = BUILDERS.get(instance.type)
        if builder is None:
            raise ValueError(f"Unknown section type: '{instance.type}'")

        style, policy = build_section_style(
            instance_type=instance.type,
            instance_style=instance.style,
            manifest=manifest,
        )

        section = builder(instance)
        # Attach the resolved three-axis style + policy onto the AST node.
        section = section.model_copy(update={
            "policy": policy,
            "subsection": style.subsection,
            "layout": style.layout,
        })
        sections.append(section)

    return Document(sections=sections)


__all__ = [
    "BUILDERS",
    "build_document",
    "build_section_style",
    "build_profile",
    "build_experience",
    "build_education",
    "build_skills",
    "build_projects",
    "build_languages",
    "build_certifications",
    "build_research",
]
