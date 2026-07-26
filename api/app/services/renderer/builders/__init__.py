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
    TextRun,
)

from .certifications import build_certifications
from .education import build_education
from .experience import build_experience
from .languages import build_languages
from .profile import build_profile
from .projects import build_projects
from .research import build_research
from .skills import build_skills
from .extras import build_extras


BUILDERS = {
    "profile": build_profile,
    "experience": build_experience,
    "education": build_education,
    "skills": build_skills,
    "projects": build_projects,
    "languages": build_languages,
    "certifications": build_certifications,
    "research": build_research,
    "extras": build_extras,
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
    subsection = SubsectionStyle.model_validate(subsection_dict) if subsection_dict else _default_subsection(instance_type)
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


def _default_subsection(instance_type: str) -> SubsectionStyle:
    """Type-level block defaults, applied only when the instance declares
    no subsection of its own.

    Profile content is centered by default; every other section inherits
    the document alignment. An explicit per-section ``text_align`` pick or
    a per-CV ``default_text_align`` still wins over this default."""

    if instance_type == "profile":
        return SubsectionStyle(text_align="center")
    return SubsectionStyle()


def apply_field_text_styles(section: Section, text_styles: dict[str, TextStyle]) -> Section:
    """Attach per-field :class:`TextStyle` entries onto the section's runs.

    The wire carries per-field appearance in ``SectionInstanceStyle.text``
    (field_key -> TextStyle); the renderer reads ``TextRun.style``. Without
    this bridge, bold / italic / color / font-size edits never reach the
    preview or the PDF.

    A builder-set ``link`` href on a run is preserved: the builders attach
    real anchors to link fields, and a plain replacement would silently
    drop the href whenever the user styles the link field.
    """

    if not text_styles:
        return section

    new_entries = []
    for entry in section.entries:
        new_fields = []
        for field in entry.fields:
            ts = text_styles.get(field.key)
            if ts is None:
                new_fields.append(field)
                continue
            new_fields.append(field.model_copy(update={
                "runs": [_merge_field_style(r, ts) for r in field.runs],
            }))
        new_entries.append(entry.model_copy(update={"fields": new_fields}))
    return section.model_copy(update={"entries": new_entries})


def _merge_field_style(run: TextRun, ts: TextStyle) -> TextRun:
    """Apply a user :class:`TextStyle` to a run, keeping a builder-set link."""

    href = run.style.link if run.style else None
    merged = ts if href is None else ts.model_copy(update={"link": href})
    return run.model_copy(update={"style": merged})


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
        # Per-field appearance (bold/italic/color/font-size) lands on the
        # runs; the renderer reads TextRun.style.
        if instance.style is not None:
            section = apply_field_text_styles(section, instance.style.text)
        sections.append(section)

    return Document(sections=sections)


__all__ = [
    "BUILDERS",
    "apply_field_text_styles",
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
    "build_extras",
]
