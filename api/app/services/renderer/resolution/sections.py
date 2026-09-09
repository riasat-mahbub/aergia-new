"""Resolve section style layers and renderer capability gates."""

from __future__ import annotations

from collections.abc import Iterable

from app.document_schema.models import (
    Customizations,
    LayoutHints,
    Section,
    SectionInstanceStyle,
    SectionPolicy,
    SectionTypography,
    SubsectionStyle,
    TemplateManifest,
)
from app.services.renderer.builders import apply_field_text_styles
from app.services.renderer.html_values import (
    FONT_TOKEN_VALUES as FONT_TOKENS,
    resolve_color_ref,
)
from app.services.renderer.policy import resolve_policy
from app.services.renderer.support import SupportLevel

from .context import ResolutionContext


def _default_date_style() -> dict[str, str]:
    """Return the professional default date style."""

    return {"key": "Month YYYY", "range_sep": " – "}


def _overlay_subsection(
    base: SubsectionStyle | None,
    override: SubsectionStyle | None,
) -> SubsectionStyle:
    if override is None:
        return base or SubsectionStyle()
    base_dict = base.model_dump(exclude_none=True) if base else {}
    over_dict = override.model_dump(exclude_none=True)
    return SubsectionStyle.model_validate({**base_dict, **over_dict})


def _overlay_layout(base: LayoutHints | None, override: LayoutHints | None) -> LayoutHints:
    if override is None:
        return base or LayoutHints()
    base_dict = base.model_dump(exclude_none=True) if base else {}
    over_dict = override.model_dump(exclude_none=True)
    return LayoutHints.model_validate({**base_dict, **over_dict})


def _overlay_policy(
    base: SectionPolicy | None,
    override: SectionPolicy | None,
) -> SectionPolicy | None:
    if override is None:
        return base
    if base is None:
        return override
    base_dict = base.model_dump(exclude_none=True)
    over_dict = override.model_dump(exclude_none=True)
    return type(base).model_validate({**base_dict, **over_dict})


def _overlay_typography(
    base: SectionTypography | None,
    override: SectionTypography | None,
) -> SectionTypography | None:
    if override is None:
        return base
    base_dict = base.model_dump(exclude_none=True) if base else {}
    over_dict = override.model_dump(exclude_none=True)
    merged: dict[str, object] = {}
    for role in ("heading", "body"):
        role_values = {
            **(base_dict.get(role) or {}),
            **(over_dict.get(role) or {}),
        }
        if role_values:
            merged[role] = role_values
    return SectionTypography.model_validate(merged or {})


def _apply_section_overlay(section: Section, override: SectionInstanceStyle) -> Section:
    """Merge a per-instance override onto a section's local style."""

    section = section.model_copy(update={
        "subsection": _overlay_subsection(section.subsection, override.subsection),
        "layout": _overlay_layout(section.layout, override.layout),
        "typography": _overlay_typography(section.typography, override.typography),
        "policy": _overlay_policy(section.policy, override.policy),
    })
    if override.text:
        section = apply_field_text_styles(section, override.text)
    return section


def _apply_template_defaults(section: Section, manifest: TemplateManifest | None) -> Section:
    """Fill values that remain unset after section and user overrides."""

    if manifest is None:
        return section

    layout_dict = section.layout.model_dump(exclude_none=True) if section.layout else {}
    sub_dict = section.subsection.model_dump(exclude_none=True) if section.subsection else {}

    body_font = manifest.global_styles.body_font
    if body_font and not layout_dict.get("font_family"):
        layout_dict["font_family"] = FONT_TOKENS.get(body_font, body_font)

    accent = manifest.global_styles.accent_color
    if accent and not sub_dict.get("section_color"):
        sub_dict["section_color"] = resolve_color_ref(accent)

    if not layout_dict.get("date_style"):
        layout_dict["date_style"] = _default_date_style()

    new_layout = LayoutHints.model_validate(layout_dict) if layout_dict else section.layout
    new_subsection = SubsectionStyle.model_validate(sub_dict) if sub_dict else section.subsection
    return section.model_copy(update={"subsection": new_subsection, "layout": new_layout})


def _apply_user_customizations(section: Section, customizations: Customizations) -> Section:
    """Fill unset section values from legacy shared user customizations."""

    layout_dict = section.layout.model_dump(exclude_none=True) if section.layout else {}
    sub_dict = section.subsection.model_dump(exclude_none=True) if section.subsection else {}

    if customizations.body_font and not layout_dict.get("font_family"):
        layout_dict["font_family"] = FONT_TOKENS.get(customizations.body_font, customizations.body_font)
    if customizations.accent_color and not (
        section.typography and section.typography.body and section.typography.body.color
    ):
        sub_dict["section_color"] = resolve_color_ref(customizations.accent_color)
    if customizations.default_text_align and not sub_dict.get("text_align"):
        sub_dict["text_align"] = customizations.default_text_align

    new_layout = LayoutHints.model_validate(layout_dict) if layout_dict else section.layout
    new_subsection = SubsectionStyle.model_validate(sub_dict) if sub_dict else section.subsection
    return section.model_copy(update={"subsection": new_subsection, "layout": new_layout})


def _apply_capability_gates(section: Section, context: ResolutionContext) -> Section:
    """Remove section values that the selected renderer cannot represent."""

    support = context.support
    if support.feature_skills_inline is SupportLevel.NONE and section.type == "skills":
        if section.policy is not None and section.policy.skill_variant is not None:
            section = section.model_copy(update={
                "policy": section.policy.model_copy(update={"skill_variant": "block"}),
            })

    if section.layout is None:
        return section

    none_fields = [
        field
        for field in ("break_before", "keep_together", "heading_keeps_with_first")
        if getattr(support, field) is SupportLevel.NONE
    ]
    updates = {
        field: False
        for field in none_fields
        if getattr(section.layout, field)
    }
    if not updates:
        return section
    return section.model_copy(update={"layout": section.layout.model_copy(update=updates)})


def resolve_section(section: Section, context: ResolutionContext) -> Section:
    """Resolve one section through the documented precedence cascade."""

    if section.policy is None:
        section = section.model_copy(update={
            "policy": resolve_policy(section.type, context.manifest),
        })

    override = context.customizations.per_section.get(section.id)
    if override is not None:
        section = _apply_section_overlay(section, override)

    section = _apply_user_customizations(section, context.customizations)
    section = _apply_template_defaults(section, context.manifest)
    return _apply_capability_gates(section, context)


def resolve_sections(
    sections: Iterable[Section],
    context: ResolutionContext,
) -> dict[str, Section]:
    """Resolve sections while preserving their input order."""

    resolved_sections: dict[str, Section] = {}
    for section in sections:
        resolved = resolve_section(section, context)
        resolved_sections[resolved.id] = resolved
    return resolved_sections


__all__ = ["resolve_section", "resolve_sections"]
