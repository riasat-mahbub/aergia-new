---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M129QBNK54QF2Y9PV8WDKNA4
TYPE: feature
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: M
OWNER: riasat
CONFIDENCE: Medium
TAGS:
- renderer
- layout
- grid
- visual-diff
- golden-pdf
- manifest
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-13T17:29:18.594093+00:00'
UPDATED_AT: '2026-08-13T17:29:18.594093+00:00'
---

# Two-column entry layout (projects, research, certifications)

## Background

## Background

After the row-order fix (commit 97ccc20) shipped, three visual-diff bugs
remained against the golden PDF (~/Downloads/Resume.pdf) and the
user-supplied manual CV (~/Downloads/Riasat_Mahbub-9.pdf):

1. **Research: gap when venue is absent.** A research entry with no
   publication_value produced a sparse secondary row (link only) above
   the description, leaving a fixed  band between them in
   the entry's vertical flex container.

2. **Research: paper link drops by one line when title wraps.** With
   a long title like *Exploring Code Smells In Simulation Modelling
   Systems: Effectiveness, Risks And Impacts*, the date rail sat on
   the title's first visual line (y=55.1) but the link lived in the
   secondary row and landed on the title's second visual line
   (y=100.9). The link was anchored to the title's bottom, not the
   entry's top.

3. **Project: long description stretches to full content width.**
   The -group description had no max-width constraint, so it
   wrapped to the full ~570pt of the content area instead of staying
   in a readable column.

All three were caused by the same underlying constraint: the
single-column stack layout puts each field in a separate row, with
no way to put the date+link on the same visual line as the title
when the title wraps.

## Investigation

Traced the full AST pipeline ( ->  -> 
 ->  for PDF; same chain 
with  post-transform for live preview). Both 
surfaces share the renderer, so a renderer-side change in 
 applies to both automatically.

Confirmed that  is the existing cascade carrier for
document semantics (alongside , ,
). Adding a new field  is non-breaking: Pydantic's BaseModel
ignores unknown fields on input, and the class default handles
existing manifests and customizations that don't set it.

Confirmed that  already provides per-type defaults
that flow through  -> . The three
target section types (projects, research, certifications) get
 as their default; all other types stay
on 'stack'.

## Decision

**Layout**: .

- **Right column** = Thu 13 Aug ADT 2026 02:29:18 PM field +  field only (key-based
  selection via ).
  The right column has  to right-justify the date and link
  on separate lines.
- **Left column** = everything else (title, venue, description,
  tech, issuer, location, etc.). Stacked as block fields with no
  extra max-width cap — the grid column IS the natural width
  constraint.
- The right column anchors to the entry's top via ,
  so a long title wrapping in the left column doesn't push the right
  column down.

**Scope**: applies only to projects, research, and certifications
by default. Other section types (experience, education, profile,
skills, languages, extras) keep the existing single-column stack
layout — the new mode is targeted at sections whose body content
benefits from being separated from the date/link rail.

**No customize-panel UI**:  lives in 
and the wire shape () accepts it, but
the customize panel doesn't expose a control. The user explicitly
asked for this to be a system-templates decision; per-CV override is
possible via the wire shape (power users) but not surfaced in the UI.

## Implementation

**Renderer** ():
-  gains an  parameter
  and branches to  when set.
-  (new helper) splits fields by key,
  renders the right column as a single right-justified block of
  , and renders the left column as a vertical stack of
  block fields. No  reuse — the right column is
  deliberately NOT grouped by group; it's a flat right-justified
  block.
-  passes  to .

**Schema** ():
- One new field: . Class default keeps existing manifests/customizations
  working without modification.

**Policy** ():
-  sets  for
  'projects', 'research', 'certifications'. Other types keep the
  class default ('stack').
-  gains one line to cascade  through
  the manifest override path.

**Tests**:
- : 
  asserts the per-type defaults.
- : 3 cascade tests covering the manifest override
  path, the section default path, and the per-instance overlay path
  via .
- : 3 new tests (right-column structure,
  no-venue case, stack-default-for-experience) + 1 updated test
  (the link is now in the right column, not the old rail pattern).

**Codegen**:  regenerated. 
 added. No
frontend code changes (the customize panel doesn't reference
).

## Verification

- pytest: 338 pass, 4 deselected (pre-existing auth/cv/db issues
  unrelated to this work). 1 pre-existing failure in
  test_seed_templates () is
  unrelated to this commit.
- ruff: clean across all changed files.
- codegen --check: clean (SectionPolicy.entry_layout present in
  generated TS).
- end-to-end PDF render (Playwright headless Chromium):
  - Manual CV project (Aergia + 2026-03 + github link + summary):
    Aergia x=24 y=50.8 (left col), 2026-03 x=537 y=64.1 (right col),
    summary x=24 y=72.8 (left col).
  - Research (with venue): Exploring x=24 y=50.8 (left col), PDF
    x=545 y=64.1 (right col), NeurIPS x=24 y=89.3 (left col),
    description x=24 y=109.6 (left col).
  - Research (no venue): Exploring x=24 y=50.8 (left col), PDF
    x=545 y=64.1 (right col), description x=24 y=89.3 (left col) —
    no vertical gap between the link and the description.
  - Long-description project: line widths 424pt, 441pt, 170pt —
    fills the full left column.

## Follow-up

- Customize-panel UI for  is intentionally not exposed.
  If a future feature wants users to toggle entry layout per CV, the
  field is already in the wire shape and the panel can read it
  without further schema changes.
- The 5:1 column ratio is hard-coded in the renderer. If a future
  template needs a different ratio, this can be added to
   as a new optional field.
- A custom  cap on body fields was removed (the grid
  column now constrains width). If a future template wants narrower
  body text, it can be added as a  field on
  .

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from FEAT-01KZY2QN02VNF4XK7H5SQFB2KD during the schema-4 cutover. -->
