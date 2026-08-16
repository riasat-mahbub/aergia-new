---
SCHEMA: 4
FORMAT: project-tracker
ID: ADR-01M129QBNK54QF2Y9PV8WDKN6W
TYPE: adr
STATUS: DONE
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: riasat
CONFIDENCE: Medium
TAGS:
- phase-7
- three-axis
- style
- migrated
RELATIONS:
  related:
  - FEAT-01M129QBNK54QF2Y9PV8WDKN7Y
  - ADR-01M129QBNK54QF2Y9PV8WDKN6V
  - FEAT-01M129QBNK54QF2Y9PV8WDKN9E
AFFECTS: null
LINKS:
  plan: local://phase-7-closeout-phase-8-hardening-plan.md
  source: tracker/decisions/ADR-01KZCCM17NP6QSKMGG71QV4PWH-three-axis-style-model.md
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: '2026-08-08T22:35:29.174858+00:00'
UPDATED_AT: '2026-08-08T22:35:29.174858+00:00'
---

# Three-axis style model

## Context

The current `SectionStyle` (10 fields: font, color, weight, text_align, field_styles, show_title, layout, date_style, subsection_gap, row_gap) conflates three different concerns:

1. **Inline per-field appearance** (bold, italic, color, font-size, link).
2. **Block-level appearance** (text-align, spacing, background).
3. **Page-flow and structural intent** (break_before, keep_together, orphans, widows, font, date_style).

The customize panel flattens these into one "Style" disclosure. The user has to figure out which thing they meant. The result is a UX that conflates categories and a data model that mixes concerns.

## Decision

The new system splits the styling into three orthogonal axes:

### `TextStyle` — inline per-field appearance

Applied to a single run of text inside a field. Decoration of one field.

```python
class TextStyle(BaseModel):
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strike: bool = False
    color: str | None = None
    link: str | None = None
    font_size: Literal["xs", "small", "normal", "large", "xl"] | None = None
```

### `SubsectionStyle` — block-level appearance

Applied to the wrapper of a section or entry. Affects the block as a whole.

```python
class SubsectionStyle(BaseModel):
    text_align: Literal["left", "right", "center", "justify"] | None = None
    spacing_before: str | None = None
    spacing_after: str | None = None
    background_color: str | None = None
```

### `LayoutHints` — page flow and structural intent

Page-flow constraints the renderer honors (or warns about).

```python
class LayoutHints(BaseModel):
    font_family: str | None = None
    date_style: DateStyle | None = None
    break_before: bool = False
    keep_together: bool = True
    heading_keeps_with_first: bool = True
    orphans: int = 2
    widows: int = 2
```

### `SectionPolicy` — document semantics

Renderer-implemented structural rules. The HTML renderer implements them with HTML constructs; a future DOCX renderer would implement them with DOCX constructs.

```python
class SectionPolicy(BaseModel):
    show_title: bool = True
    skill_variant: Literal["block", "inline"] | None = None
```

## Mapping from old to new

| Old `SectionStyle` field | New location |
|---|---|
| `font` | `LayoutHints.font_family` (section-level) |
| `color` | `TextStyle.color` (per-field) |
| `weight` | `TextStyle.bold` (per-field) |
| `text_align` | `SubsectionStyle.text_align` (section wrapper) |
| `show_title` | `SectionPolicy.show_title` (renderer-determined) |
| `layout` (skills) | `SectionPolicy.skill_variant` (renderer-determined) |
| `field_styles` | per-field `TextStyle` on each entry field |
| `date_style` | `LayoutHints.date_style` (section-level) |
| `subsection_gap` | `SubsectionStyle.spacing_after` (per-entry) |
| `row_gap` | `SubsectionStyle.spacing_after` (profile section) |

## Consequences

- **The customize panel exposes three disclosure groups.** Layout, Block style, Field styles. Each group has its own controls.
- **Per-field styling is a first-class feature.** The user can decorate the school name, the company, the date — any field — without touching the rest of the section.
- **The cascade is invariant.** Template defaults → user customizations → per-instance overrides. The Resolver produces a fully resolved RenderModel.
- **The renderer is simpler.** It reads the RenderModel and emits HTML. No decisions to make.

## Related

- `EPIC-01KZCCC3MTXDGPY31H06NFYP1Q-html-first-pipeline-with-three-axis-style-ast`
- `ADR-01KZHR8NXNVWPHJTQFE6E37V9G-html-first-architecture`
- `FEAT-01KZHR8NTSB4D8JZ4JX2D9THGE-html-first-pipeline-phase-7-migrated`
- `AGENTS.md`, `PLAN.md`, `local://phase-7-ast-pipeline-closeout.md`

<!-- Migrated from ADR-01KZHR8P0PPWSZZPGYBT8HGGVT during the schema-4 cutover. -->
