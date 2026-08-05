# PDF Parser: pdfplumber cutover

> **For agentic workers:** implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking. One commit per task, in order; every commit is self-contained (code + tests green for its scope) and carries its tracker update (`tracker update ... + tracker rebuild && tracker validate`) so the tracker never drifts from the branch.

**Goal:** Swap the parser's PDF extraction layer from pypdf's plain-mode visitor (which carries a Chromium-specific CTM band-aid, see `extract.py:113-118`) to pdfplumber (which uses pdfminer.six and resolves the cumulative CTM for us). This closes the residual bug from the post-resilience investigation (BUG-01KZSHINVESTIGATEPARSERBUGS Task 1: profile social_links silently dropped because the CTM-scale bbox math leaves a 50pt gap between the rendered contact line and its annotation rects). The classifier and mapper are unchanged in API; their input block shape becomes more permissive (title + date on the same line is the new normal) and they need a small hardening step to handle it.

**Benchmark corpus:** `api/tests/fixtures/resume-benchmark.pdf` (Riasat Mahbub's Resume.pdf, md5 `8d91e1fec2e433ebc6b5fa6c7c88e9ee`). After the change, `parse_cv(pdf_bytes, "application/pdf")` returns a `ParseResult` with sections for every CV section AND `profile.social_links` contains both LinkedIn and GitHub AND every experience entry has a non-empty `position` and `company`.

**Execution contract:** one commit per task, in order; each commit is self-contained (code + tests green for that task's scope) and carries its tracker update (`tracker update ... + tracker rebuild && tracker validate`) so the tracker never drifts from the branch. Commit messages follow the repo's conventional style (`feat(parser): …` / `fix(parser): …` / `refactor(parser): …` / `tracker: …`).

**Branch:** `refactor/parser-pdfplumber` (already off `master`). Merged into `master` via a regular merge commit per `AGENTS.md`.

---

## Architecture

```
                                ┌────────────────────┐
                                │  Settings.parser_  │
                                │     backend        │
                                └─────────┬──────────┘
                                          │ (default "pdfplumber")
                                          ▼
                                ┌────────────────────┐
file bytes ──► extract() ──────► │  dispatcher        │
                                │  (top of module)   │
                                └─────────┬──────────┘
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  │                                               │
                  ▼                                               ▼
        ┌─────────────────────┐                       ┌─────────────────────┐
        │  extract_with_      │                       │  _extract_pdf (pypdf│
        │  pdfplumber         │                       │  visitor, deleted)  │
        │  ─────────────────  │                       │                     │
        │  page.extract_text_ │                       │                     │
        │   lines()           │                       │                     │
        │  + extract_words()  │                       │                     │
        │  + page.hyperlinks  │                       │                     │
        │  ─────────────────  │                       │                     │
        │  block.x/y/w/h      │                       │                     │
        │   already in        │                       │                     │
        │   PDF-native top-   │                       │                     │
        │   down coords       │                       │                     │
        │  block.links from   │                       │                     │
        │   hyperlink rect    │                       │                     │
        │   overlap           │                       │                     │
        └─────────┬───────────┘                       └─────────────────────┘
                  │
                  ▼ blocks + plain_text + links
        ┌─────────────────────┐
        │  classify.py        │
        │  ─────────────────  │
        │  NO API change.     │
        │  Internal change:   │
        │  _split_rail_lines  │
        │   normalizer peels  │
        │   date range off a  │
        │   line that carries │
        │   one. So the       │
        │   existing per-line │
        │   flow sees         │
        │   already-          │
        │   normalized text.  │
        └─────────┬───────────┘
                  ▼ labeled blocks
        ┌─────────────────────┐
        │  mapper.py          │
        │  (unchanged)        │
        └─────────┬───────────┘
                  ▼
                SectionInstance list
```

### What changes in the classifier (Task 3)

pdfplumber's `extract_text_lines()` groups words on the same visual line into one block, **including right-rail date text** like:

```
Research Assistant                September 2023 – October 2025
```

vs the old pypdf visitor, which emitted them as two separate spans (and therefore two separate blocks). The classifier's existing experience splitter assumes title and date are on separate lines:

```python
# classify.py:351-353 (current behaviour)
if DATE_RANGE_RE.search(line):
    date_text = line
    continue
if _looks_like_position_title(line):
    ...
```

When the line is `"Research Assistant  September 2023 – October 2025"`:
- `DATE_RANGE_RE` matches → `date_text = "Research Assistant  September 2023 – October 2025"`, the **title is lost**.
- Next line `"Dalhousie University"` enters `_looks_like_position_title`, **passes** (no punctuation, short), and becomes `position = "Dalhousie University"`.
- Result: `pos='Dalhousie University' co=''` — observed regression.

**Fix shape (one place, not two):** add `_split_rail_lines(text)` that pre-normalizes the section text. For each input line, if it contains a date-range match **plus** other text, emit two lines: the title part first, then the date part. The existing per-line splitter then sees data on its expected shape. The fix is symmetric for experience and education (date appears as a rail next to position or degree) but the experience case is the one observed; education is hardened as defence-in-depth.

This is intentionally NOT a per-`_extract_*_fields` change. Doing the normalization once at the classify boundary means every section-type-specific splitter stays simple.

### Why we keep `_infer_font` in `extract.py`

`api/tests/test_extract_fonts.py` locks the bold-inference contract (`_infer_font`, `_font_family_from_basefont`, `_font_family_is_bold`). The pdfplumber module imports `_infer_font` (`_extract_pdfplumber.py:34`). We delete the pypdf-specific extraction code (`_extract_pdf`, `_collect_text_spans`, `_group_spans_into_lines`, `_extract_font_dict`, `_collect_page_annotations`, `_attach_annotations_to_block`, `_TEXT_CTM_SCALE`, `_FALLBACK_FONT_SIZE`, `_TextSpan`, `_Line`) but **keep** the three helpers and the `_FONT_NAME_BOLD_TOKENS` constant. They move into a new tiny module `_fonts.py` so `extract.py` shrinks to just the dispatcher + JSON fast-path, and `_extract_pdfplumber.py` + `test_extract_fonts.py` import from `_fonts.py` instead of `extract.py`. This also breaks the import cycle risk of `_extract_pdfplumber` → `extract` → `_extract_pdfplumber`.

---

## Root cause summary (one bug, three downstream symptoms)

The pypdf visitor path in `api/app/services/parser/extract.py:113-569` was tuned for one Chromium export (page CTM `0.24` × nested `3.125` × text-block Tm `1.0` = `0.75`). On the benchmark PDF the visitor reports `tm_y` for the contact line at y∈[833, 842], but the contact-line annotation rects are at y∈[768, 781]. The CTM-scale bbox math produces `(page_h - 0.75 * tm_y)`, leaving a 50pt gap between the rendered contact line and the name. `_attach_annotations_to_block` finds no overlap, so the four `/Annots /Link` URIs on the contact line never attach. The mailto annotation accidentally attaches to the name block (overlaps y∈[782, 795]); LinkedIn, GitHub, and site annotations are silently dropped. The site_url is then recovered by `_BARE_DOMAIN_RE` matching `rmahbub.com`; LinkedIn and GitHub have no fallback, so `profile.social_links = []`.

Pdfplumber uses pdfminer.six, which resolves the cumulative CTM itself. `page.hyperlinks` returns rects in the same top-down space as `page.extract_words`. The overlap test works directly. Bug closed.

---

## Tasks

### Task 1 — Wire the dispatcher to a Settings flag

- **Add** `pdfplumber>=0.11` to `api/pyproject.toml:23`.
- **Add** `parser_backend: str = "pdfplumber"` to `Settings` (`api/app/config.py`). Pydantic-settings auto-binds `AERGIA_PARSER_BACKEND` env var via the existing `BaseSettings` machinery.
- **Rewrite** `extract()` (`api/app/services/parser/extract.py:73-104`) to dispatch by `Settings.parser_backend`. Module-level cache the backend choice after the first read so we don't hit settings on every call.
- **Re-export** `extract_with_pdfplumber` from `api/app/services/parser/__init__.py` and add to `__all__`.
- **Verify** by running the existing `api/tests/test_parser_smoke.py` end-to-end against the benchmark — all 11 tests must stay green (the dispatcher still routes to the pypdf path by default in tests if env is unset; but with the new field defaulting to `"pdfplumber"`, the test suite implicitly switches backends. Re-run with `AERGIA_PARSER_BACKEND=pypdf` if any test regresses — that's information, not a blocker, and the next task fixes the underlying classifier.)

**Commit:** `feat(parser): dispatch PDF extraction on Settings.parser_backend flag`

**Tracker:** Update `TASK-01KZSG1PARSERPDFPLUMBER` → IN_PROGRESS note "task 1 done: dispatcher + settings flag wired."

### Task 2 — Move font helpers to `_fonts.py` and switch pdfplumber to the new import

- **Create** `api/app/services/parser/_fonts.py` containing `_FONT_NAME_BOLD_TOKENS`, `_font_family_from_basefont`, `_font_family_is_bold`, `_infer_font`. Move them verbatim from `extract.py:601-662`. Update their module docstring (they no longer live next to the visitor).
- **Update** `api/app/services/parser/_extract_pdfplumber.py:34` to import from `.fonts` instead of `.extract`.
- **Update** `api/tests/test_extract_fonts.py:26-29` to import from `app.services.parser._fonts`.
- **Verify** `pytest api/tests/test_extract_fonts.py -v` (13 cases) green. No production behaviour change yet.

**Commit:** `refactor(parser): move font-name helpers into _fonts module`

**Tracker:** Update `TASK-01KZSG1PARSERPDFPLUMBER` → note "task 2 done: font helpers extracted; pdfplumber module imports from new location."

### Task 3 — Harden the classifier for title-rail layouts

- **Add** `def _split_rail_lines(text: str) -> list[str]` at `classify.py` (right after `_split_entries`). Implementation: walk input lines; for each line, run `DATE_RANGE_RE.search`. If the match has `start() > 0`, the line carries both title and date — emit two output lines: `line[:start].strip(" \t·–—-")` and `m.group(0)`. Otherwise emit the line unchanged. Pure function, no I/O.
- **Update** `_extract_experience_fields` (classify.py:312) to call `_split_rail_lines` on the input text before the existing per-line loop. **No change** to the inner per-line logic — the splitter still works once each input line is on its expected shape.
- **Update** `_extract_education_fields` (classify.py:380) the same way.
- **Add tests** in `api/tests/test_parser_imports.py`:
  - `test_experience_splits_title_rail_date`: input text `"Research Assistant  September 2023 – October 2025\nDalhousie University\nBuilt things."` produces entries with `position="Research Assistant"`, `company="Dalhousie University"`.
  - `test_education_splits_degree_rail_date`: input `"Master of Computer Science  Sep 2023 – Oct 2025\nDalhousie University"` produces entries with `degree="Master of Computer Science"`, `institution="Dalhousie University"`.
- **Verify** the existing benchmark suite still passes AND the live benchmark now shows `position='Research Assistant'`, `company='Dalhousie University'` for the first experience entry (was `pos='Dalhousie University' co=''` before this task).

**Commit:** `fix(parser): split title-rail date lines so experience/education recover title and date`

**Tracker:** Update `TASK-01KZSG1PARSERPDFPLUMBER` → note "task 3 done: classifier handles title+date-on-same-line."

### Task 4 — Add regression test for the social_links annotation fix

- **Add** `test_benchmark_profile_social_links_attached` to `api/tests/test_parser_smoke.py`. Asserts: `profile` section exists; `social_links` is a non-empty list; at least one entry has `label == "LinkedIn"` and at least one has `label == "GitHub"`.
- **Add** `test_collect_page_annotations_attaches_contact_line_links` to `api/tests/test_parsers.py` for the unit-level case: synthesise a PDF-like page with annotations and a contact line at y where the CTM-scale bbox would NOT reach, verify the new pipeline still attaches them. (This locks the fix; without it, a future revert to pypdf would pass the corpus test only by accident.)
- **Verify** `pytest api/tests/test_parser_smoke.py::test_benchmark_profile_social_links_attached` green.

**Commit:** `test(parser): lock profile social_links attachment against regression`

**Tracker:** Update `TASK-01KZSG1PARSERPDFPLUMBER` → note "task 4 done: regression test in place; Bug 1 closed."

### Task 5 — Delete the pypdf visitor extraction path

- **Delete** from `api/app/services/parser/extract.py`:
  - Line 30-31: `from pypdf import PdfReader` / `from pypdf.errors import PdfReadError`
  - Lines 107-569: the entire "PDF extraction (visitor-mode synthesis)" section, including `_TEXT_CTM_SCALE`, `_FALLBACK_FONT_SIZE`, `_extract_pdf`, `_TextSpan`, `_Line`, `_collect_text_spans`, `_group_spans_into_lines`, `_extract_font_dict`, `_collect_page_annotations`, `_attach_annotations_to_block`.
- **Keep** in `extract.py`: the dispatcher (`extract`, `_parser_backend`), `SUPPORTED_MIME`, the `ParserError` / `UnsupportedFormatError` / `EmptyInputError` / `ExtractionFailedError` class definitions, `validate_section_instance_list`, and the `__all__` list.
- **Update** `api/app/services/parser/extract.py`'s module docstring to describe the dispatcher shape, not the visitor.
- **Remove** `pypdf>=4.2` from `api/pyproject.toml:22` (pdfplumber uses pdfminer.six; pypdf is no longer needed).
- **Verify** `grep -rn "pypdf" api/` returns no hits except doc-comments / changelog.

**Commit:** `refactor(parser): delete pypdf visitor extraction path; pdfplumber is the only backend`

**Tracker:** Update `TASK-01KZSG1PARSERPDFPLUMBER` → IN_PROGRESS note "task 5 done: pypdf extraction path deleted."

### Task 6 — Final verification + tracker close

- **Run** `./dev.sh --smoke` from repo root. This runs pytest + ruff + source-only vitest + ESLint (smoke config) + production build + the live-render smoke (`api/scripts/smoke_live.py`) against `generic-modern`, `generic-classic`, `generic-minimal` on a fresh temp SQLite. All must pass.
- **Spot-check** `parse_cv` on the benchmark end-to-end: confirm `social_links` contains LinkedIn + GitHub, experience entries have non-empty position and company, education entries have non-empty degree and institution.
- **Close** `TASK-01KZSG1PARSERPDFPLUMBER` with `tracker close TASK-01KZSG1PARSERPDFPLUMBER --resolution "pdfplumber backend shipped; classifier hardened for title-rail layouts; Bug 1 (profile social_links loss) closed; pypdf path deleted; benchmark corpus + dev.sh --smoke green."`
- **Close** the post-resilience investigation entry: `tracker update TASK-01KZSHINVESTIGATEPARSERBUGS --status DONE --note "Bug 1 (profile social_links) closed via pdfplumber cutover. Other findings (Bug 2: lowercase-leading skill category prefix, Bug 3: source PDF has no annotation for research entry #2) are data-quality concerns, not parser bugs."`

**Commit:** `chore(parser): close pdfplumber cutover; dev.sh --smoke green`

**Tracker:** Both entries closed; tracker rebuilt.

---

## Risk register

- **Pdfminer.six slower than pypdf.** On the 1-page benchmark the call is ~30ms vs ~10ms for pypdf. For 10-page CVs this is ~300ms. The orchestrator is async; user-perceived latency impact is acceptable. If real-world CVs regress noticeably, drop `pdfminer.six` per-page parse caching.
- **Pdfplumber `extract_text_lines()` line grouping differs across PDF generators.** Word/LaTeX exports may put the date above the position, not next to it. The `_split_rail_lines` normalizer handles "title + date on same line" but not "title on one line, date on previous line" — that's the same shape pypdf produced, which the existing splitter already handles. Worst case: a generator puts the date as a separate line ABOVE the title. The existing `_extract_experience_fields` would capture the date as the first entry's `date_text` and the title as the second entry's `position`. Defensible; not a regression. Mitigation deferred to the next plan if observed.
- **Edge case: very long lines.** `_split_rail_lines` uses `m.start()` to slice. If the date appears at column 0 the slice is empty (line `[0:0] = ''`); the function falls through and the existing `DATE_RANGE_RE.search(line)` branch captures it. Covered by the existing tests.
- **`pypdf` removal could break an undocumented caller.** The grep in Task 0 confirmed only `extract.py:30-31` imports it. If a new caller appears between plan-write and execution, the grep at Task 5 will surface it. Plan is safe.

## Out of scope (intentionally)

- Multi-column layout support (`extract.py:218-224` returns `columns=[[]]` honestly). Defer to next plan.
- LLM-as-default-strategy (would let us drop `_extract_*_fields` entirely). Defer.
- `Tracker rebuild / validate` CLI bug (pre-existing, affects `history` / `rebuild` / `validate`). Defer to a tracker-tooling fix.
- Research entry #2 missing paper_url (the source PDF has no annotation). Not a parser bug.

## Plan checklist

- [ ] Task 1 — Settings flag + dispatcher
- [ ] Task 2 — Font helpers extracted to `_fonts.py`
- [ ] Task 3 — Classifier hardened for title-rail layouts
- [ ] Task 4 — Regression tests for social_links
- [ ] Task 5 — Delete pypdf extraction path
- [ ] Task 6 — `./dev.sh --smoke` green; trackers closed
