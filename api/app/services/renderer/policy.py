"""Section policy defaults.

The default policy per section type lives here. The resolver applies the
manifest's ``policy_overrides.by_type[type]`` on top of these defaults
(see :func:`resolve_policy`).

Profile hides its title by default (no redundant ``PROFILE`` header); the
others show theirs. Skills default to a block layout; the user can switch
to inline via the customize panel.
"""

from __future__ import annotations

from app.schema.models import SectionPolicy, TemplateManifest


SECTION_POLICIES: dict[str, SectionPolicy] = {
    "profile": SectionPolicy(show_title=False, skill_variant=None),
    "experience": SectionPolicy(show_title=True),
    "education": SectionPolicy(show_title=True),
    "skills": SectionPolicy(show_title=True, skill_variant="block"),
    "projects": SectionPolicy(show_title=True, entry_layout="two-column"),
    "languages": SectionPolicy(show_title=True),
    "certifications": SectionPolicy(show_title=True, entry_layout="two-column"),
    "research": SectionPolicy(show_title=True, entry_layout="two-column"),
    "extras": SectionPolicy(show_title=True),
}


def resolve_policy(type_: str, manifest: TemplateManifest | None) -> SectionPolicy:
    """Return the effective :class:`SectionPolicy` for a section type.

    Layered as: default per-type → manifest override → instance policy (the
    last is applied by the resolver, not here).
    """

    base = SECTION_POLICIES.get(type_, SectionPolicy(show_title=True))
    if manifest is None:
        return base
    overrides = manifest.policy_overrides.by_type
    if type_ not in overrides:
        return base
    return _merge_policies(base, overrides[type_])


def _merge_policies(base: SectionPolicy, override: SectionPolicy) -> SectionPolicy:
    """Apply ``override`` on top of ``base`` (override wins for set fields)."""

    return SectionPolicy(
        show_title=override.show_title if override.show_title != base.show_title else base.show_title,
        heading_divider=(
            override.heading_divider
            if override.heading_divider != base.heading_divider
            else base.heading_divider
        ),
        skill_variant=override.skill_variant if override.skill_variant is not None else base.skill_variant,
        entry_layout=override.entry_layout if override.entry_layout != base.entry_layout else base.entry_layout,
    )
