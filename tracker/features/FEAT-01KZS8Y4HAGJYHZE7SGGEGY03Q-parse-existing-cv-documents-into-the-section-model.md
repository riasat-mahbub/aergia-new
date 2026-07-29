---
SCHEMA: 3
FORMAT: project-tracker
ID: FEAT-01KZS8Y4HAGJYHZE7SGGEGY03Q
TYPE: feature
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: L
OWNER: riasat
CONFIDENCE: High
TAGS:
- import
- pdf
- extras
- parser
RELATIONS:
  supersedes:
  - FEAT-01KYZ1HDXP92GQS3Z8CA47R3HW
AFFECTS:
- api/app/services/parser/extract.py
- api/app/services/parser/classify.py
- api/app/services/parser/mapper.py
- api/app/services/parser/strategies.py
- api/app/services/parser/imports.py
- api/app/routes/imports.py
- web/src/components/builder/ImportPDFButton.tsx
- web/src/lib/api/imports.ts
LINKS:
- local://pdf-import-plan.md
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: '2026-08-11T20:41:30.410155+00:00'
UPDATED_AT: '2026-08-11T20:41:30.410155+00:00'
---

# Parse existing CV documents into the section model

## Background

Phase 2 of PDF import shipped: PDF/JSON extract → classify → map to
typed SectionInstance list. Closed-text OCR fallback intentionally
omitted; LLM deferred (`LLMStrategy` stub raises `NotImplementedError`).
Extras section became first-class in this same iteration so the parser
has somewhere valid to put everything it can't classify.

User flow: click "Import PDF" in the builder toolbar → upload → parsed
sections land in `cvStore` → user reviews/edits → save via the existing
`POST /api/v1/cvs` flow. No silent auto-persist; no LLM in v1.

## Investigation

- Confirmed the existing AST pipeline has only 8 closed-vocab section
  types (`profile | experience | education | skills | projects |
  languages | certifications | research`) wired through `BUILDERS`
  and `SECTION_POLICIES`. A catch-all land is required for
  unknown/unclassifiable content; promoting `extras` to first-class
  gives the user manual control over the same shape the parser fills
  automatically.
- Agreed against adding PyMuPDF: AGPL, conflict with `MIT.html`.
  Reuse existing `pypdf` (≥4.2) + `pypdfium2` (≥4.30) — both already
  pinned in `pyproject.toml`.
- Three-axis `SectionInstanceStyle` is already in scope; the parser
  consumes the wire shape, not the resolved RenderModel, so no resolver
  changes were needed.
- `SectionInstance.data: list | dict` is already permissive; no
  `app/schema/models.py` change is required for `extras` or for the
  parser schemas (which live in the parser package and don't reach
  the codegen output).

## Decision

- `extras` chosen over `unmapped`/`custom`/`notes` to avoid collision
  with the existing `Customizations` model and `CustomizePanel` UI.
- Shape: `list[{ id, title, fields: list[{ label, value }] }]` —
  weakly typed, reuses the existing `_render_field_row` HTML path so
  no per-type renderer branch is needed.
- Parser strategy as a `Protocol` seam so an `LLMStrategy` adapter
  slots in without touching the regex path. v1 ships only
  `RegexStrategy`; the LLM stub raises `NotImplementedError` per the
  "no LLMs" decision.
- Two-endpoint flow: `/cvs/import/pdf` parses only (returns
  `ParseResult`), persistence stays on the existing `POST /cvs`. No
  auto-persist.
- Route at `/api/v1/cvs/import/pdf` (symmetric with `/cvs/{id}/preview`
  and `/cvs/{id}/export/pdf`).
- Confidence levels: reuse parser-side vocabulary `high | medium | low`
  (NOT `SupportLevel`'s `FULL | BEST_EFFORT | NONE` — semantic
  mismatch).

## Implementation

Backend (`api/`):

- `app/services/renderer/builders/extras.py` — typed AST builder,
  one `Entry` per `data` row, fields rendered as
  `FieldBlock(key="field:{label}", group="body")`. URL-shaped values
  pass through `normalize_url_scheme`.
- `app/services/renderer/builders/__init__.py` — `BUILDERS` dispatch
  extended and `build_extras` exported via `__all__`.
- `app/services/renderer/policy.py` — `SECTION_POLICIES["extras"] =
  SectionPolicy(show_title=True)`.
- `app/services/parser/schemas.py` — `TextBlock`, `ExtractedDocument`,
  `FieldConfidence`, `ConfidenceReport`, `ParseMeta`, `ParseResult`
  Pydantic models.
- `app/services/parser/extract.py` — mime dispatcher; PDF path uses
  pypdf plain-mode with header/column heuristics; JSON path returns
  empty `ExtractedDocument` and the orchestrator validates against
  `SectionInstance.list`.
- `app/services/parser/classify.py` — title synonyms, all-caps-bold
  header detection, per-section parsers (experience split on
  `--/at/@`; skills split on `,;/•` with 40-char cap; ambiguous
  title/company both filled with `confidence=low`).
- `app/services/parser/mapper.py` — per-type builders that emit the
  closed-vocab `data` shapes; `extras` emits the
  `{title, fields:[{label,value}]}` shape; `_skip_header` strips
  the heading line itself from each section's data input.
- `app/services/parser/strategies.py` — `RegexStrategy` ships,
  `LLMStrategy` raises `NotImplementedError`.
- `app/services/parser/imports.py` — `parse_cv(file_bytes, mime_type)`
  orchestrator; warning flags `scanned_pdf_text_empty`,
  `parsed_with_unmapped_content`, `low_confidence_regex_parse`,
  `json_fastpath`.
- `app/routes/imports.py` — `POST /api/v1/cvs/import/pdf` JWT-protected
  multipart endpoint; status code map: 200/400/401/413/422/500.
- `app/app.py` — `imports_router` mounted at `/api/v1`.

Frontend (`web/`):

- `src/components/sections/extras/ExtrasEditor.tsx` — uses
  `useFieldArray` + `SortableAccordionList`; per-entry title +
  add/remove `{label, value}` fields.
- `src/components/sections/SectionRegistry.tsx` — `ExtrasEditor`
  imported and registered in `sectionMap`.
- `src/lib/sections/types.ts` — `extras` added to `SECTION_LABELS`,
  `SECTION_TYPES`, and `createDefaultSectionData` switch.
- `src/components/sections/AddSectionModal.tsx` — `extras` icon
  (`<Plus>`).
- `src/components/customization/CustomizePanel.tsx` — text-align
  allowlist extended to include `extras`. Date-format allowlist
  unchanged (extras has no date field).
- `src/lib/sections/fieldStyles.ts` — `extras` entry with `{title,
  field}` keys.
- `src/lib/api/imports.ts` — axios `importPDF(file)` wrapper, 60s
  timeout, multipart upload.
- `src/components/builder/ImportPDFButton.tsx` — mirrors
  `ExportPDFButton` shape, hidden file input, `FileUp` icon, toast
  on success/info/error.
- `src/pages/BuilderPage.tsx` — `<ImportPDFButton />` next to
  `<ExportPDFButton />`.

Fixture:

- `api/tests/fixtures/sample.pdf` — hand-crafted 848-byte single-page
  PDF with a multi-section CV (Jane Doe + EXPERIENCE + SKILLS) so
  smoke_live can assert against a real file rather than a mock.

## Verification

- `cd api && pytest tests/test_extras_builder.py tests/test_parser_imports.py tests/test_parser_strategies.py tests/test_smoke_live.py -q`
  → 30 passing.
- `cd api && DATABASE_URL="sqlite+aiosqlite:///./data/aergia.test.db" ENVIRONMENT=test pytest -q`
  → 233 passing (3 pre-existing flakes in `test_auth.py` and
  `test_cvs.py` from the persistent test DB, unrelated).
- `cd web && npm test`
  → 182/182 passing.
- `cd web && npm run build`
  → production build green.
- `cd web && npm run codegen:check`
  → exit 0 (no codegen drift; `extras` adds no Pydantic models).
- `cd api && ruff check app/ scripts/ tests/`
  → all clean (auto-fixed one unused import).
- Manual route check (auth required):
  - `POST /cvs/import/pdf` with `application/pdf` returns 200 +
    `ParseResult`.
  - Same with `text/plain` body returns 400.
  - Without `Authorization` returns 401.
  - Body >15 MB returns 413.
  - Body not starting with `%PDF` returns 422.

## Follow-up

- LLM seam: implement `LLMStrategy.structure`, add
  `app/services/parser/keys.py` (provider detection + per-prefix
  redaction), `app/services/parser/providers/{base,anthropic,openai,
  gemini}.py`. Widen `ParseMeta.source` to
  `Literal["regex", "llm"]`. Add `api_key` + `provider` form fields
  to `/cvs/import/pdf`. AuthError must raise verbatim (per plan).
- Layout-aware PDF extraction: replace pypdf plain-mode synthesis
  with the visitor-protocol extractor for proper multi-column CVs
  (left rail of dates + right column of description). Affects
  `app/services/parser/extract.py:_extract_pdf`.
- Scanner support: `pypdfium2` rasterize → Tesseract OCR fallback
  inside `_extract_pdf`, surfaced via
  `meta.warnings += ["scanned_pdf_text_empty"]` already wired.
- Customize-panel "reclassify extras → other type" UI:
  dropdown that mutates `SectionInstance.type` and runs the
  matching per-type mapper on the captured paragraphs.
- DOCX and JSON-fastpath routes: `extract.py` already has the
  dispatcher shape; only need the `_extract_docx` and
  `_extract_json` implementations and an `ALLOWED_MIME` widener on
  the route.
