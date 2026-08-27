---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M129QBNK54QF2Y9PV8WDKN99
TYPE: feature
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: High
TAGS:
- customize
- typography
- sections
- renderer
RELATIONS:
  related:
  - FEAT-01M129QBNK54QF2Y9PV8WDKN8D
  - FEAT-01M129QBNK54QF2Y9PV8WDKN87
AFFECTS:
  files:
  - web/src/lib/sections/fieldStyles.ts
  - web/src/lib/sections/types.ts
  - web/src/components/customization/CustomizePanel.tsx
  - web/src/components/sections/SectionPreviewPanel.tsx
  - api/app/schemas/sections.py
  - api/app/services/renderer/ir.py
  - api/app/services/renderer/types.py
  - api/app/services/renderer/backends/html.py
  - api/app/services/renderer/section_renderers/profile.py
  - api/app/services/renderer/section_renderers/experience.py
  - api/app/services/renderer/section_renderers/education.py
  - api/app/services/renderer/section_renderers/projects.py
  - api/app/services/renderer/section_renderers/skills.py
  - api/app/services/renderer/section_renderers/languages.py
  - api/app/services/renderer/section_renderers/certifications.py
  - api/tests/test_section_renderers.py
  - api/tests/test_cvs.py
  - web/src/components/__tests__/CustomizePanel.test.tsx
LINKS: null
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: '2026-08-04T03:53:05+00:00'
UPDATED_AT: '2026-08-04T03:53:05+00:00'
---

# Per-section field typography

## Background

Each `SectionInstance` previously exposed a single typography bundle (font
family, weight, color, align, show_title) that applied to every element in
the section. The user wanted each **named data field** inside a section to
carry its own typography choices — independently of every other field. The
motivating example was a Profile section where changing the Name field's
font size to 24 px should leave the Title, Summary, Email, Phone,
Location, and Site link untouched.

The control key is the field's semantic name (Name, Email, Summary,
Position, Company, Degree, GPA, …), which is the same identifier used in
the entry's data dict. Section types share a common entry schema, so each
section type exposes a fixed list of fields; the panel renders one
Font / Size / Weight row per field.

## Decision

- Field-level typography is keyed by data field name, not HTML tag. The
  map lives on the existing per-instance `SectionStyle.field_styles` so
  no data-model migration is required and two instances of the same type
  can carry different typography.
- Renderers tag each field element with `class="f-{key}"`. A defaults
  stylesheet at the top of the HTML document restores the original
  sizes/weights byte-for-byte when no override is set, so PDFs without
  field styles render exactly as before.
- Per-section overrides are emitted as a scoped `<style>` block per
  panel, targeted via `#s-{instance.id} .f-{key}`. The wrapper `<div>`
  now carries that stable id (the existing `instance.id` is already
  unique), so live preview and PDF both honor the override.
- `FieldStyle` uses `size` (not `font_size`) to match the UI label "Size"
  and keep the wire format JSON-friendly.
- The React inline preview deliberately does NOT honor field styles —
  the iframe preview hits `/render/html` and is the source of truth.
  This is called out in a code comment on `SectionPreviewPanel.tsx` so
  the next implementer knows.

## Implementation

- **New: `web/src/lib/sections/fieldStyles.ts`** — `FIELD_DEFS` map keyed
  by section type (`profile`, `experience`, `education`, `projects`,
  `skills`, `languages`, `certifications`) plus a `getFieldDefs(type)`
  helper that returns `[]` for unknown types. Each `FieldDef` is
  `{ key, label }` keyed by the entry-data field name.
- **`web/src/lib/sections/types.ts`** — added `FieldStyle` interface
  (`font?`, `size?`, `weight?`) and `field_styles?: Record<string,
  FieldStyle>` on `SectionStyle`. Existing fields preserved for
  backward compatibility.
- **`api/app/schemas/sections.py`** — mirrored `FieldStyle` and
  `field_styles` on the backend Pydantic `SectionStyle`. Optional fields
  mean existing CV rows continue to deserialize.
- **`api/app/services/renderer/types.py`** — propagated `field_styles`
  through the IR type so `_build_section_panel` can read it.
- **`api/app/services/renderer/section_renderers/*.py`** — replaced
  inline `font-size` / `font-weight` declarations on field elements with
  `class="f-{key}"` for every field in `FIELD_DEFS`. Layout styles
  (margin, display, alignment) stay inline.
- **`api/app/services/renderer/backends/html.py`** — added a defaults
  ruleset (`.f-name`, `.f-title`, `.f-summary`, `.f-contact`,
  `.f-position`, `.f-company`, `.f-date`, `.f-description`,
  `.f-degree`, `.f-institution`, `.f-gpa`, `.f-url`, `.f-tech`,
  `.f-category`, `.f-tag`, `.f-language`, `.f-proficiency`, `.f-meta`)
  whose values exactly mirror the inline defaults they replaced. The
  `.f-name` rule uses `var(--profile-name-size, 1.5rem)` so the existing
  template slider keeps working.
- **`api/app/services/renderer/ir.py`** — wrapper `<div>` now carries
  `id="s-{instance.id}"`. After computing `wrapper_style` and
  `heading_style`, `_build_section_panel` emits a per-panel `<style>`
  block with one rule per user-set property (`font-family`,
  `font-size`, `font-weight`) per field, scoped via the panel id.
  Only set properties are emitted; missing/empty `field_styles` emits
  no block.
- **`web/src/components/customization/CustomizePanel.tsx`** — added a
  new "Per-field typography" section below the existing per-section
  controls, above the Show Title toggle. For each field in
  `getFieldDefs(selectedInstance.type)` it renders a `FieldStyleRow`
  (inline component) with Font / Size / Weight selects that reuse the
  existing `FONT_OPTIONS`, `SIZE_OPTIONS`, and `WEIGHT_OPTIONS`. A
  Reset link clears the row. New helper `updateSelectedFieldStyle`
  merges into `selectedStyle.field_styles[field]`. `hasValues` extended
  to include `field_styles` so the section card lights up when any
  field is customized.
- **`web/src/components/sections/SectionPreviewPanel.tsx`** —
  comment-only change documenting that the inline React preview does
  NOT honor field styles; the iframe preview via `/render/html` is the
  source of truth.
- **Tests** — 4 new tests in `api/tests/test_section_renderers.py`
  (render as CSS rules, skip unset properties, omit when empty, schema
  round-trip). Existing CV round-trip assertions updated in
  `api/tests/test_cvs.py`. 2 new tests in
  `web/src/components/__tests__/CustomizePanel.test.tsx` (Profile
  labels, Projects labels).

## Verification

- **Backend tests**: `pytest tests/test_section_renderers.py
  tests/test_cvs.py -q` → 57 passed (existing 53 + 4 new).
- **Frontend tests**: `vitest run CustomizePanel.test.tsx` → 15 passed
  (existing 13 + 2 new).
- **End-to-end check**: stamped
  `style.field_styles.name = {size: "24px", weight: "700"}` on a
  Profile instance in the seed CV and rendered via `HTMLBackend._format`.
  Asserted `font-size:24px` appears inside a scoped `.f-name` rule,
  `.f-name` selector is present, and no other field grew to 24 px.
  Output: `OK — name field picked up 24px override`.
- **PDF byte-equivalence for non-users**: defaults ruleset in
  `backends/html.py` carries the same values the inline declarations
  used before, so CVs without `field_styles` continue to render
  unchanged. Verified by the unchanged test counts in
  `test_section_renderers.py` and `test_cvs.py`.
- **Validation**: `tracker rebuild && tracker validate` clean.

## Follow-up

- Per-entry field styles (one typography per row inside a section) are
  not exposed yet. The data model can grow an
  `entries: { [entryId]: FieldStyle }` layer without breaking the
  existing `field_styles` shape if a future need arises.
- The React inline preview still renders at default sizes. If users
  complain, the field-style context can be threaded through the React
  renderers; until then the iframe preview is authoritative.

<!-- Migrated from FEAT-01KZ5EEMD1EZ756KKG93J8ETRG during the schema-4 cutover. -->
