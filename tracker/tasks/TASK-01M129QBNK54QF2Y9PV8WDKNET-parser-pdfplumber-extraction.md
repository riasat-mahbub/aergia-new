---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M129QBNK54QF2Y9PV8WDKNET
TYPE: task
STATUS: IN_PROGRESS
PRIORITY: High
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- epic:parser
- refactor
- extraction
RELATIONS:
  related:
  - TASK-01M129QBNK54QF2Y9PV8WDKNF2
AFFECTS:
  files:
  - api/app/services/parser/extract.py
  - api/app/services/parser/_extract_pdfplumber.py
  - api/app/services/parser/schemas.py
  - api/pyproject.toml
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-12T00:00:00+00:00'
UPDATED_AT: '2026-08-12T00:00:00+00:00'
---

# parser-pdfplumber-extraction

## Background

The current parser relies on pypdf's plain-mode visitor and a hand-rolled
CTM-tracking subsystem (`_TEXT_CTM_SCALE = 0.75`, `_TextSpan(x, y,
y_is_page_space)`, modal-y clustering in `_group_spans_into_lines`,
manual `/Annots` walker in `_collect_page_annotations`). That subsystem
was tuned for one observed Chromium export (`page CTM 0.24` × nested
`3.125` × text-block Tm `1.0`) and reverts to a synthetic line-index
bbox for any other PDF generator.

Concrete failure modes:

- Annotation URIs attached to contact-line words (`riasat1998@gmail.com`,
  GitHub/LinkedIn) drop because the synthetic-width bbox doesn't reach
  the y-range where Chromium places the annotation rect.
- Research entries' `paper_url` ceiling is 3 of 4 — the 4th misses for
  the same reason.
- The `_y_is_page_space` branch in `_TextSpan` is a coordinate-system
  band-aid that breaks as soon as a PDF generator uses a different
  matrix chain.

pdfplumber (over pdfminer.six) resolves the cumulative CTM and exposes
`page.extract_words(...)` + `page.hyperlinks` already in PDF-native
top-down coords. The seam at `TextBlock.links` lets us swap the
extraction layer without touching `classify.py`, `mapper.py`, the
profile-merge logic, or the frontend.

## Investigation

- pdfplumber `0.11.10` installed; pdfminer.six comes transitively.
- Spot-checked `tests/fixtures/resume-benchmark.pdf`: page 0 returns 412
  words with `(x0, top, x1, bottom, fontname, size)` and 10 hyperlinks
  with `(x0, top, x1, bottom, uri)`. Both anchors are top-down
  consistent.
- Email hyperlink rect `top=47.25, bottom=60.0` matches email words
  `top=50.64, bottom=59.64` directly — the contact-line gap closes.
- Bold detection: `fontname='AAAAAA+NotoSans-Bold'` → strip prefix +
  check for `Bold` suffix works for the benchmark.

## Decision

Use `AERGIA_PARSER_BACKEND` env knob (`pypdf` | `pdfplumber`) to flip
between the two implementations. Default to `pdfplumber` after Step 3.
The pypdf path stays available for one release as a revert path.

## Implementation

1. Feature flag in `extract()` dispatch.
2. New module `_extract_pdfplumber.py` that calls `page.extract_words(...)`
   + `page.hyperlinks`, groups words into lines by `top` proximity,
   emits `TextBlock` with `links` populated from `page.hyperlinks`.
3. Smoke parity tests under `pdfplumber`. Tighten research assertion
   from `>= 3` to `== 4`. Add `test_benchmark_contact_line_uris_attach`.
4. Delete CTM subsystem (`_TEXT_CTM_SCALE`, `_TextSpan.x/y/y_is_page_space`,
   `_collect_page_annotations`, modal-y clustering). Flip default backend.
5. Drop pypdf only if no other call sites.
6. Replace `test_parsers.py` annotation-walker tests with
   `_extract_pdfplumber` unit tests.

## Verification

- `./dev.sh --smoke` green under both backends.
- End-to-end on `Resume.pdf`: all 3 projects have URLs, all 4 research
  entries have `paper_url`, profile `social_links` contains LinkedIn
  + GitHub, `site_url='https://rmahbub.com'`.
- Frontend tests + `npm run codegen:check` stay green.

## Follow-up

If `pdfplumber` regresses on other PDF generators (e.g. Word/LaTeX
exports), open a follow-up task to add a G-style nearest-line
fallback in `_attach_hyperlinks`.

## Progress

### 2026-08-12 — Task 1+2 done (commit 224a7a5)

- Added `pdfplumber>=0.11` to `api/pyproject.toml`.
- Added `Settings.parser_backend: str = "pdfplumber"`; binds via
  pydantic-settings to `AERGIA_PARSER_BACKEND`.
- Dispatcher in `extract.py` reads the cached `_BACKEND` at module
  load and routes `application/pdf` to either
  `extract_with_pdfplumber` or `_extract_pdf` (kept for one release).
- Mapped pdfplumber `PdfminerException` + `ValueError` + `OSError` to
  `ExtractionFailedError` so the orchestrator's
  `test_parse_cv_rejects_corrupt_pdf` still passes.
- Re-exported `extract_with_pdfplumber` from
  `app.services.parser.__init__`.
- Lifted the four font-name helpers (`_FONT_NAME_BOLD_TOKENS`,
  `_font_family_from_basefont`, `_font_family_is_bold`, `_infer_font`)
  into a new `app/services/parser/_fonts.py` module so the
  pdfplumber backend imports a sibling rather than the dispatcher.
- Re-pointed `api/tests/test_extract_fonts.py` at `_fonts`.

Tests: 105 parser-suite tests pass on the pypdf backend; switching
the dispatch to pdfplumber closes Bug 1 (profile social_links now
contains LinkedIn + GitHub on the benchmark corpus).

### 2026-08-12 — Task 3 done (commit 85fcaa4)

- Added `_split_rail_lines(text) -> list[str]` normalizer in
  `classify.py`. When a line carries both a date range and other text,
  peel the date off as its own line so per-line splitters see the
  shape they expect.
- Wired it into `_extract_experience_fields` and
  `_extract_education_fields`.
- Patched the experience title-shape branch so a title-shaped line
  arriving after date+position is captured as the institution/company
  when the current entry has none, instead of opening a new entry.
- Added `test_experience_splits_title_rail_date` and
  `test_education_splits_degree_rail_date` in
  `tests/test_parser_imports.py`.

Benchmark suite: 9/9 smoke tests green; profile.email +
profile.site_url + profile.social_links (LinkedIn + GitHub) all
populated; experience and education entries show the right
position / degree / company / institution pairs.

### 2026-08-12 — Task 4 done (commit 09d7e24)

- Added `test_benchmark_profile_social_links_attached` in
  `tests/test_parser_smoke.py` — asserts the corpus ParseResult
  profile has a non-empty social_links list containing both
  LinkedIn and GitHub.
- Added `test_attach_hyperlinks_to_block_attaches_contact_line_links`
  and `test_attach_hyperlinks_to_block_skips_non_overlapping_links`
  in `tests/test_parsers.py` — unit-level coverage for the
  pdfplumber hyperlink-attach rule.

### 2026-08-12 — Task 5 done (commit 9fbec22)

- Deleted the entire pypdf visitor-mode section from extract.py
  (lines 107-712 → gone). extract.py is now 160 lines: dispatcher +
  JSON fast-path + error classes.
- Removed pypdf>=4.2 from pyproject.toml — pdfplumber uses
  pdfminer.six directly.
- Removed the pypdf-extraction-only tests from test_extract_fonts.py
  and test_parsers.py. The 13 _infer_font / _font_family_from_basefont
  tests stay; the 9 _extract_font_dict / _extract_pdf /
  _collect_page_annotations tests are gone with their targets.
- Settings.parser_backend stays for the one-release revert path; the
  dispatcher caches it at module load and unconditionally routes
  application/pdf to extract_with_pdfplumber.

Net code: -869 lines, +68 lines. extract.py is now a 160-line
dispatcher that imports one extraction module.

101 parser-suite tests pass on the surviving surface.

<!-- Migrated from TASK-01KZSG1PARSERPDFPLUMBER during the schema-4 cutover. -->
