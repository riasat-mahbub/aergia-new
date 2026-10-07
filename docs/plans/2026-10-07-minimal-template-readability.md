# Minimal template readability — Luna execution plan

Status: **implemented and verified** following the user's execution request. See
[execution checkpoints](2026-10-07-minimal-template-execution-state.md).
Base reviewed: `b8e4016`. Tracker:
`FEAT-01M4BXMQHJT56A8C43KXTQZZYR`.

This plan implements the Minimal portion of A06 in the
[CV builder/ATS audit](../cv-builder-ats-audit-2026-10-07.md).
Minimal already passed the local structural extraction checks. The objective
is a more readable single-column document that retains those results.

## Scope and visual targets

Improve the defaults of `generic-minimal` without changing document content,
section ordering, URLs, database structure, or authored customization values.
Retain its current sans-serif identity, neutral palette, centered profile,
single-column placement, section dividers, readable URL labels, comma-separated
skills, A4 format, and 32 px zone padding.

| Property | Current | Target |
| --- | --- | --- |
| Body descriptions and summary | 9 pt | 10.5 pt, using the existing `small` token |
| Contact details, dates, links, skill tags, project tech labels | Mostly 9 pt | 10.5 pt; labels remain real selectable text |
| Body line height | Browser default | Existing `normal` token, 1.4 |
| Section spacing | 0 px | Existing `minimal` spacing preset, 16 px |
| Entry spacing | 0 px | Existing `snug` token, 8 px |
| Field spacing inside an entry | 0 px | Existing `tight` token, 4 px; rich-text paragraph/list rhythm remains |
| Candidate name | 18 pt | Keep 18 pt unless explicitly customized |
| Section headings | 12 pt | Keep 12 pt unless explicitly customized |

These are readability choices, not numerical ATS requirements. Keep the
short audit fixture on one page if the target values fit naturally. Longer
CVs may occupy more pages; do not auto-shrink text or delete evidence to force
a page count.

Do not include Modern/Classic redesigns, new ATS platforms, scanner heuristic
fixes, new document checks, keyboard/accessibility overhaul, photo/email
controls, Letter/DOCX export, new fonts, or additional density presets. Those
remain separately scoped audit work.

## Implementation contract

### 1. Add optional template defaults

The current manifest has no template body-size or independent entry-gap
settings. Do not change global CSS defaults, key behavior on the template's
display name, persist styling into every CV, or add a second renderer.

Add the following backwards-compatible optional fields, preserving manifest
version 2:

```text
GlobalStyles.body_font_size: FontSizeToken | None = None
GlobalStyles.body_line_height: Literal["tight", "normal", "relaxed"] | None = None
LayoutDefaults.entry_gap: SpacingToken | None = None
LayoutDefaults.field_gap: SpacingToken | None = None
```

Only the Minimal seed populates them:

```text
global_styles.body_font_size = "small"
global_styles.body_line_height = "normal"
layout_defaults.spacing = "minimal"
layout_defaults.entry_gap = "snug"
layout_defaults.field_gap = "tight"
```

Omitted/null fields retain current rendering semantics. Classic, Modern,
custom manifests without these fields, and manifest-free rendering retain
their visual defaults. Reuse the closed token vocabulary and validate extras
and invalid tokens as usual. This deliberately adds optional manifest fields;
it does not require a SQL migration, new endpoint, or changed CV payload.

The coordinator owns generated `web/src/generated/schema.ts`. Generate it
after the schema packet lands; do not hand-edit it.

### 2. Resolve defaults into the existing render model

Extend the pure resolver's CSS variables with validated native values for
body size, body line height, entry spacing, and field spacing. Use these
stable names:

```text
--body-size
--body-line-height
--spacing-entry
--spacing-field
```

Use `RenderModel.css_vars`; no new document/rendering subsystem is needed.
The resolver converts tokens to native values. The HTML renderer only accepts
the corresponding closed CSS values. Extend its variable allowlist and safe
spacing handling for the exact new variable references. Never accept raw CSS
from a manifest or let unknown variable names reach output.

Entry spacing and field spacing currently both inherit
`--spacing-subsection`. Replace their consumption with distinct variables,
falling back to the old subsection behavior for legacy manifests. Keep
section spacing owned by `--spacing-section`.

Preserve override behavior:

- Explicit section `subsection.entry_gap`, `field_gap`, and spacing controls
  win over inherited values. An explicit `none` means zero, not “inherit.”
- When `customizations.spacing` is set, its existing spacing-preset mapping
  owns document section/entry/field defaults. Do not let new Minimal gaps
  silently override an authored document spacing preset.
- Section typography and field/run styles continue to win over template
  defaults through the existing CSS/style cascade.
- Empty/null section choices inherit; rendering must not write defaults back
  to the stored CV or manufacture override indicators.
- Preserve the existing behavior of authored body-size overrides, including
  profile fields. Template defaults alone must not resize the candidate name.

### 3. Apply body defaults without flattening hierarchy

Have the existing body-sized field rules use the resolved body-size variable
with their current fallback. Include descriptions, summaries, contact data,
dates, GPA, links, tech labels, skill tags, social labels, and chip text.
Keep name, heading, role/degree/project title hierarchy intact. Set line height
on `body` as an inherited variable with its existing `normal` fallback. Do not
put a direct line-height rule on field classes: it would bypass explicit
section line-height inheritance. Keep chips' existing direct 1.2 line-height.
Check list items and multiline links as well as plain strings.

Do not implement this by filling every section's
`typography.body.font_size`: the current renderer applies an explicit section
body size to `.f-name` too. Do not replace rich-text run styling or change list
semantics. Existing authored inline size/color choices must still render.

Keep project chip appearance in this scope; increasing its text size should
not change it into an image, alter labels, or hide the tech-stack text.

### 4. Reflect inheritance in the inspector

Pass the active manifest's new defaults through the builder/inspector props.
Show useful inherited hints such as “Template default (10.5 pt)” and the
effective entry/field spacing. Retain empty select values for inheritance.
Never copy inherited values into `instance.style` on load, save, or opening
a section. `Reset this section` returns to the new template defaults.

Use existing feature entrypoints and shared schema imports. The React surface
remains an editor and preview adapter. Do not create frontend document CSS or
hard-code a special `generic-minimal` cascade. Review profile size hints so
they do not imply the candidate name has the body size.

### 5. Preserve existing CVs and freshness

The seed updater refreshes stored system manifests. Existing Minimal CVs
without explicit style overrides therefore pick up the new default rendering;
this is the intended improvement. Explicit authored overrides remain stored
and effective.

CV creation copies zone geometry into `customizations.layout`, so preserve the
seed's existing zones, padding, and placement. A change to seed zone padding
alone would not uniformly update previously created CVs. No data rewrite is
authorized by this plan.

Verify scanner render-input fingerprints detect the changed manifest. Advance
`PDF_RENDERER_VERSION` in `api/app/scanner/service.py` for the changed renderer
semantics, using the next value after checking the integration branch. Do not
rewrite immutable historical preview PDFs or their bindings. Existing
freshness/reevaluation paths should explain that an older result is stale.

## Subagent assignments

Use **GPT-6 Luna with max reasoning** for each execution packet. Four total
assignments; root plus at most three active children. Do not start these
implementation packets while merely writing or reviewing the plan.

```json
{
  "task_name": "minimal_p01",
  "model": "gpt-6-luna",
  "reasoning_effort": "max",
  "fork_turns": "none",
  "message": "Implement the assigned packet from docs/plans/2026-10-07-minimal-template-readability.md in the specified checkout."
}
```

Each real assignment must give the absolute checkout, base revision, tracker
ID, packet, allowed files, relevant audit evidence, and this plan. Read root
and closest AGENTS.md and applicable skills before editing. Use apply_patch
for hand edits. Agents must not spawn children, overwrite another packet,
edit tracker history/generated code, merge to master, or deploy. Return file
changes, verification evidence, remaining risks, and suggested tracker notes.
Flag a contract correction to the coordinator before broadening ownership.

### P01 — Template schema, resolver, and HTML defaults

**Start first. Own:**

- `api/app/document_schema/models.py`
- `api/app/db/seed.py`
- `api/app/services/renderer/html_values.py`
- `api/app/services/renderer/resolution/render_model.py`
- `api/app/services/renderer/html_renderer/html_document.py`
- `api/app/services/renderer/html_renderer/html_entries.py`
- `api/app/services/renderer/html_renderer/html_sections.py`
- `api/app/scanner/service.py`, only the renderer-version declaration
- `api/tests/test_seed_templates.py`, `test_resolve.py`, `test_html_renderer.py`

Implement the contract, including compatibility and override tests. Preserve
the section/entry page-flow rules. Capture reproducible sibling-template
baseline measurements before editing; PDF binaries themselves need not match
byte for byte. Do not add typography decisions in schema validation methods.

**Deliver:** optional fields, Minimal seed defaults, resolved CSS variables,
safe HTML consumption, scoped typography/gaps, appropriate renderer version,
focused tests, and a concise handoff describing the final field/cascade shape.
The coordinator reviews it and runs codegen before dependents start.

### P02 — Builder inheritance hints

**Depends on:** reviewed P01 and generated types. **Own:**

- `web/src/features/builder/components/BuilderWorkspace.tsx`
- `web/src/features/builder/components/customization/Inspector.tsx`
- `web/src/features/builder/components/customization/SectionInspector.tsx`
- `web/src/features/builder/components/customization/groups/BodyTextGroup.tsx`
- `web/src/features/builder/components/customization/groups/SpacingGroup.tsx`
- `web/src/features/builder/components/customization/groups/types.ts`
- `web/src/features/builder/domain/customization/cascade.ts`
- A focused behavior fixture/test using the repository's existing frontend
  testing conventions, only if needed for inheritance/save/reset behavior

Load Impeccable's craft-floor reference immediately before a UI edit. Keep
the current inspector layout and controls. Add truthful inherited labels and
spacing display without persisting defaults or falsely marking overrides.
Verify opening, editing, saving, clearing, and resetting a section, plus
switching templates under the existing template-switch behavior.

**Deliver:** inherited values visible and accurate, stored overrides unchanged,
lint/typecheck/structure checks, and desktop/mobile evidence for the changed
controls. One batched inspection and at most one confirmation after fixes.

### P03 — Real-PDF and freshness regressions

**Depends on:** reviewed P01; may run alongside P02. **Own:**

- `api/tests/test_pdf_readability.py`
- A focused new file, proposed `api/tests/test_minimal_readability.py`
- `api/tests/test_scanner_backfill.py`, freshness regressions only
- Generated synthetic evidence under an agreed docs fixture directory

Reuse the production pipeline and Playwright singleton, closing it normally.
Use synthetic content, not user CVs. Extend meaningful regression coverage
for these cases:

1. Audit-like short CV with profile, two jobs, education, skills, and project.
2. Longer multi-page CV, including an entry near a page boundary.
3. Long name, long employer/title, long URL slug, international characters,
   plus research, certifications, languages, and rich-text styles.
4. Explicit section/field typography, zero/nonzero gaps, legacy document
   spacing presets, and clear/reset-to-inherit behavior at the renderer boundary.
5. Legacy manifests and unchanged Classic/Modern typography/geometry.
6. Stored scan freshness before and after the new manifest/renderer version.

Assert actual PDF glyph sizes in representative fields, physical bounds,
identity integrity, headings, entry/date association, visible addresses,
clickable links, and retained punctuation-sensitive skills (`C++`, `C#`,
`.NET`, `CI/CD`). Compare pdfplumber and PDFium. Do not assert universal ATS
success, exact PDF bytes, or a fixed page count for the long fixture.

**Deliver:** focused tests, representative PDF/PNG/text evidence, parser
results, and a list of any new failure with its exact fixture. Do not silence
known Modern sidebar warnings to obtain a green generic ATS report.

### P04 — Independent integration review

**Depends on:** P01–P03 integrated. **Read-only assignment.**

The packet architecture was reviewed read-only by GPT-6 Luna at max reasoning
during planning. That review confirmed the optional fields, override cascade,
copied-layout behavior, and existing freshness mechanism; it did not implement
or validate the future changes.

Review the final diff and evidence against the contract. Inspect the exported
Minimal PDF and current preview; check typography hierarchy, spacing,
overrides, freshness, manifest compatibility, and sibling-template isolation.
Assess the meaningfulness of tests and identify accidental scope expansion.
Return concrete findings with file/line and reproduction evidence. Do not
edit code or generate extra subjective redesign variants.

The coordinator applies any necessary fixes through the owning packet,
reruns affected checks, and updates tracker history. Passing review is not a
substitute for the release smoke gate.

## Coordinator integration and completion

Use one integration branch with clearly assigned shared-tree ownership, or
isolated worktrees whose reviewed changes are integrated before dependents
start. Protect existing uncommitted audit/report files. Freeze P01's contract
and regenerate schema once it is accepted. P02 and P03 own disjoint files.
Only the coordinator edits generated schema, tracker history, final evidence
summary, or the plan's execution status.

Completion requires:

- Minimal's target sizes/gaps measured in real output; 18 pt name and 12 pt
  headings retain hierarchy; no visual clipping or malformed link wrapping.
- Representative ordinary PDFs retain local structural/parser results.
- Explicit overrides, including `none`, survive save/reload and clearing them
  returns to inheritance; no automatic edits to stored content or layout.
- Preview uses the same HTML and displays the same typography and section
  geometry as export. Inspect actual pagination instead of assuming parity.
- Classic/Modern and manifests omitting the new fields keep prior visual
  behavior; old manifest JSON remains valid.
- Changed render inputs invalidate prior scanner results as expected without
  changing immutable historical PDFs.
- Focused tests and required repository checks pass. Run the release gate
  once after integration, then repeat only when a correction warrants it:

```bash
cd api
.venv/bin/pytest
.venv/bin/ruff check .
cd ../web
npm run lint
npm run typecheck
npm run architecture:test
npm run architecture:check
npm run codegen:check
cd ..
node --test tailoring-skill/tests/*.test.mjs
./dev.sh --smoke
tracker rebuild
tracker validate
git diff --check
```

For iteration, run only affected focused tests first. Chromium may need the
normal approved execution path outside the filesystem sandbox; do not alter
the renderer or tests to bypass environmental launch restrictions.

Record implementation outcomes and remaining limitations in a short execution
report. Keep documented tracker fork warnings visible. If merge is authorized
as part of execution, use a regular merge commit into `master` as the cutover;
subagents never merge independently. This planning request itself does not
publish, deploy, or execute the proposed product changes.
