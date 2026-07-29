# PDF Parser Resilience: real-world CVs

> **For agentic workers:** implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking. One commit per task, in order; every commit is self-contained (code + tests green for its scope) and carries its tracker update (`tracker new` / `tracker update` + `tracker rebuild && tracker validate`) so the tracker never drifts from the branch.

**Goal:** The PDF parser currently parses only the **profile** section of a real-world CV (the user's `~/Downloads/Resume.pdf`). Every other section (Experience, Education, Projects, Research, Skills) is silently dropped. Fix the chain that broke on this corpus and lock it in with parser-pipeline tests so the next real resume doesn't break the same way.

**Benchmark corpus:** `~/Downloads/Resume.pdf` (Riasat Mahbub's resume, August 2026). After the change, `parse_cv(pdf_bytes, "application/pdf")` returns a `ParseResult` with sections for every CV section in the file, plus a confidence report.

**Execution contract:** one commit per task, in order; each commit is self-contained (code + tests green for that task's scope) and carries its tracker update (`tracker new` / `tracker update` + `tracker rebuild && tracker validate`) so the tracker never drifts from the branch. Commit messages follow the repo's conventional style (`feat(parser): …` / `fix(parser): …` / `tracker: …`).

**Branch:** `fix/pdf-parser-resilience` (off `master`). Merged into `master` via a regular merge commit per `AGENTS.md`.

---

## Root cause (single bug, six downstream symptoms)

The benchmark PDF embeds five fonts (`NotoSans-Bold`, `NotoSans-Regular`, `NotoSans-Medium`, `NotoSans-SemiBold`, `DejaVuSans`) as `Type0` subsets. The extractor (`api/app/services/parser/extract.py`) builds `TextBlock` records that ignore the font dictionary entirely:

- `_infer_font` only marks a line as bold when `line == line.upper()` (`extract.py:252`). Body text and headings are mixed-case, so **no headers are flagged bold**.
- `_extract_font_dict` returns `{}` for `Type0` subsets because `_font_name_size_hint` returns `0.0` (`extract.py:240`) and the hint is dropped at `extract.py:223-226`.
- `_FALLBACK_FONT_SIZE = 10.0` (`extract.py:112`) makes every block `font_size=10.0`, so the page-median threshold (`10 × 1.15 = 11.5`) is never met.

Result: `_detect_sections` returns `[]`, every block is unclassified, and only the page-1 `profile` fallback fires. The mapper then has nothing to map, so the result is a single `profile` instance.

The six downstream extractors that fail once the headers are detected:

1. `URL_RE` / `LINKEDIN_RE` / `GITHUB_RE` (classify.py:88-90) — the contact line is `riasat-mahbub Riasat Mahbub rmahbub.com` (bare handles + bare domain, no scheme). Every regex misses.
2. `_extract_experience_fields` — the bullet regex (`^\s*[•\-*]\s+`) requires an explicit bullet character; the resume uses continuation paragraphs with no bullets, so the description is dropped.
3. `_extract_education_fields` — splits on blank lines, but the two degrees are joined by a blank line only inside the date-range pattern; the blank-line split doesn't help.
4. `_extract_skills_fields` — splits on `,;\n•` which makes `Programming Languages: TypeScript, JavaScript, …` become `['Programming Languages: TypeScript', 'JavaScript', …]`. Category labels are lost.

## Architecture

All fixes are isolated to the parser package (`api/app/services/parser/`). No Pydantic schema change, no manifest vocabulary change, no resolver change, no DB migration. The wire data keys (`name`, `title`, `email`, …, `category`, `items`) are untouched.

**Bold inference strategy:** switch from text-based `line == line.upper()` to **font-name-based** inference. Wire the existing `_extract_font_dict` to actually parse the BaseFont (currently broken for `Type0`), and route the per-line font name (from the page's `/Resources/Font` table) through the visitor or the layout-mode extractor. For the benchmark PDF:

- `NotoSans-Bold` → `is_bold=True`
- `NotoSans-SemiBold` → `is_bold=True`
- `NotoSans-Medium` → `is_bold=False`
- `NotoSans-Regular` / `DejaVuSans` → `is_bold=False`

The user-visible header-detection heuristic (`_is_candidate_header`) is unchanged — it still needs `is_bold OR font_size >= threshold`. The size threshold will still be page-median × 1.15, but with a workable font dictionary in play it's now redundant for the benchmark corpus. (Future: drop the ALL-CAPS heuristic entirely, but that's out of scope.)

**Skills group split:** the skills splitter learns one new regex (`^([A-Z][A-Za-z0-9 &/+-]+):\s*`) that peels category labels off the first item of each line. The output shape stays `list[{"category", "items"}]` (already the mapper's contract).

**Contact regex:** add bare-handle and bare-domain alternatives. Existing patterns keep their case; new alternatives are scoped to the `·`-separated contact line context.

---

## File structure

| File | Responsibility | Change |
|---|---|---|
| `api/app/services/parser/extract.py` | PDF extraction | Fix `_extract_font_dict` + `_font_name_size_hint` for `Type0` subsets; switch `_infer_font` to font-name-based bold; route per-line font to TextBlock |
| `api/app/services/parser/classify.py` | Classification | Add bare-handle / bare-domain alternatives to `URL_RE` / `LINKEDIN_RE` / `GITHUB_RE`; teach `_extract_experience_fields` to land continuation paragraphs as description; teach `_extract_education_fields` to split on date-range boundaries; teach `_extract_skills_fields` to peel category prefixes |
| `api/tests/test_parser_imports.py` | Pipeline tests | Add benchmark-corpus-shaped fixtures (one test per section type) |
| `api/tests/test_parsers.py` (new) | Per-regex unit tests | Add new file with one focused test per regex change |
| `api/tests/test_extract_fonts.py` (new) | Font-extraction tests | Add new file with a fixture that exercises the `Type0` subset path |
| `api/tests/fixtures/sample.pdf` | Hand-crafted PDF | Replace with the benchmark corpus (or add a new fixture alongside) |
| `tracker/` | Project graph | 1 bug entry, 1 feature task, 6 task updates per phase |

---

## Tracker entries (created at the start of each task)

| ID | Type | Status | Name | Affects |
|---|---|---|---|---|
| `BUG-01KZS8Y4Q…` | bug | DONE | `pdf-parser-only-emits-profile-on-real-resume` | `extract.py`, `classify.py` |
| `TASK-01KZS8Y4Q…` | task | DONE | `pdf-parser-resilience` (umbrella) | `extract.py`, `classify.py`, `tests/` |
| `TASK-01KZS8Y4Q…-bold` | task | DONE | `pdf-parser: font-name-based bold inference` | `extract.py` |
| `TASK-01KZS8Y4Q…-contact` | task | DONE | `pdf-parser: bare-handle contact regex` | `classify.py` |
| `TASK-01KZS8Y4Q…-experience` | task | DONE | `pdf-parser: experience description recovery` | `classify.py` |
| `TASK-01KZS8Y4Q…-education` | task | DONE | `pdf-parser: education entry split on date range` | `classify.py` |
| `TASK-01KZS8Y4Q…-skills` | task | DONE | `pdf-parser: skills category prefix parser` | `classify.py` |
| `TASK-01KZS8Y4Q…-fixture` | task | DONE | `pdf-parser: benchmark corpus fixture` | `tests/fixtures/` |

Each task closes the same commit it lives in: `tracker update <id> --status DONE --note "..."` + `tracker rebuild && tracker validate`.

---

## Commit plan

```
1. fix(parser): use font-name-based bold inference for Type0 subset PDFs
2. fix(parser): recognise bare LinkedIn/GitHub handles and bare domains in contact lines
3. fix(parser): recover experience descriptions when no bullets are present
4. fix(parser): split education entries on date-range boundaries
5. fix(parser): peel category prefixes from skills lines
6. test(parser): add benchmark-corpus fixture and integration assertion
```

Six commits. Each one is independently green. The umbrella bug closes on commit 6.

---

## Task 1: Bold inference — font-name-based, not text-based

**Root cause:** `_infer_font` (extract.py:243-261) flags a line as bold only when `line == line.upper()`. The benchmark PDF's sectional headers are mixed-case (`Experience`, `Education`, `Projects`, `Research`, `Skills`), so **none** are flagged. Result: `_is_candidate_header` rejects everything (it's gated on `is_bold OR font_size >= threshold`).

**Files:** `api/app/services/parser/extract.py`, `api/tests/test_extract_fonts.py` (new).

- [x] **Step 1: Fix `_extract_font_dict` for `Type0` subsets.** The current code calls `_font_name_size_hint(basefont)` which parses `[A-Z]{6}\+(.+?)-` from `NotoSans-Bold` and returns `0.0` because the font is `/Type0` (CID-keyed, no size in the name). The right move is to *not* read size from the name at all — keep the mapping `{basefont: family_name}` and let `_infer_font` decide bold from the family. Update the return type to `dict[str, str]`.

- [x] **Step 2: Surface per-line font names from the PDF.** pypdf's plain-mode `extract_text()` strips the per-glyph font reference. Switch the synth path to the layout-mode visitor (`page.extract_text(extraction_mode="layout")` with a visitor callback) that captures `/Span` / `/Text` operator font + size + position. **Or** — preferred — keep plain-mode for the text and add a separate font-walk that reads the page's content stream once and yields `[(font_name, size, x, y)]`, then matches by approximate position to the plain-mode lines. The plain-mode path already produces one line per logical line; the font-walk produces one text-span per glyph run; matching by line index is enough.

- [x] **Step 3: Teach `_infer_font` to use the font name.** When the font-walk yields a font family for the current line, set `is_bold = "bold" in family.lower() or "semibold" in family.lower() or "black" in family.lower() or "heavy" in family.lower()`. The `"regular"` / `"medium"` / unset families are not bold. Drop the `line == line.upper()` heuristic entirely — it's a lie on every mixed-case resume.

- [x] **Step 4: Tests.** `api/tests/test_extract_fonts.py`:
  - `test_font_name_hint_returns_family_for_type0_subset` — `NotoSans-Bold` → `"NotoSans-Bold"`, `NotoSans-Regular` → `"NotoSans-Regular"`.
  - `test_infer_font_flags_bold_for_bold_family` — call `_infer_font("Experience", {"font": "NotoSans-Bold"}, 10.0)` and assert `is_bold=True`.
  - `test_infer_font_drops_text_uppercase_heuristic` — call `_infer_font("experience", {"font": "NotoSans-Regular"}, 10.0)` and assert `is_bold=False` (the text-lowercased version of the section header — the old heuristic would have flattened it).

- [x] **Step 5: Verify.** `cd api && .venv/bin/pytest -q tests/test_extract_fonts.py`. Then run `python -c "from pathlib import Path; from app.services.parser.extract import extract; doc = extract(Path('/home/riasat/Downloads/Resume.pdf').read_bytes(), 'application/pdf'); print(sum(b.is_bold for b in doc.blocks))"` — should be `> 0` (8+ bold blocks).

- [x] **Step 6: Tracker.** `tracker new bug "pdf-parser-only-emits-profile-on-real-resume" --priority High --severity High --tags parser,regex,fix --description "..."` (captures the user-reported behavior). `tracker new task "pdf-parser: font-name-based bold inference" --priority High --tags parser,fix --description "..."`. `tracker update <bug-id> --status IN_PROGRESS --note "Task 1: font-name-based bold inference"`. `tracker rebuild && tracker validate`.

- [x] **Step 7: Commit.**
  ```
  fix(parser): use font-name-based bold inference for Type0 subset PDFs

  Plain-mode synthesis was treating ALL-CAPS lines as bold and ignoring
  the page's font dictionary entirely. The page's /Resources/Font table
  carries the actual font family for each text span; wire it through
  _infer_font so Type0 subset PDFs (e.g. Chromium-generated resumes)
  get the right headers.

  - _extract_font_dict now returns {basefont: family_name}; the size
    hint is removed because Type0 subsets never carry size in the name.
  - _infer_font consults the font family ("bold"/"semibold"/"black"
    /"heavy" → True; "regular"/"medium"/unset → False) and drops the
    ALL-CAPS text heuristic.
  - New test file tests/test_extract_fonts.py locks the new behaviour.

  Closes TASK-01KZS8Y4Q…-bold.
  ```

---

## Task 2: Contact regexes — bare handles and bare domains

**Root cause:** the benchmark's third contact line is `riasat-mahbub Riasat Mahbub rmahbub.com` — bare handles and a bare domain with no scheme. `URL_RE` (https://www./) misses, `LINKEDIN_RE` (linkedin.com/in/) misses (no `linkedin.com/` prefix), `GITHUB_RE` (github.com/) misses (no `github.com/` prefix). Result: `site_url=""`, `social_links=[]`.

**Files:** `api/app/services/parser/classify.py`, `api/tests/test_parsers.py` (new).

- [x] **Step 1: Add bare-handle patterns.** Append to the existing regexes:
  - `URL_RE` → `r"(?:^|[\s·])(?P<bare>(?P<host>[a-z0-9-]+\.(?:com|io|dev|me|net|org|co|ai|app))/?\b)"` — matches bare `rmahbub.com` between `·` separators or whitespace.
  - `LINKEDIN_RE` → `r"(?P<handle>linkedin\.com/in/[\w-]+|(?:^|[\s·])(?:in/)?(?P<hn>[\w-]{3,})(?=[\s·]|$))` — wait, that's noise. Better: keep the path-form regex for typed links, and add a **separate** bare-handle detector that runs *after* the existing patterns and only matches when the handle is delimited by `·` or whitespace. Place that in `_extract_profile_fields` as a third pass, not in the regex.
  - `GITHUB_RE` → same shape: keep the path-form for typed links, add a separate bare-handle pass in `_extract_profile_fields`.

- [x] **Step 2: Implement the bare-handle pass in `_extract_profile_fields`.** After the existing regex sweep, scan the raw text for tokens like `[\w-]{3,}` that sit between `·` separators or start/end-of-line. Recognise three shapes:
  - `linkedin.com/in/<handle>` → existing regex handles.
  - `<handle>` (alphanumeric, dash, underscore, 3+ chars) following `linkedin` or matching `linkedin\.com/in/...` — already covered.
  - **Bare domain** `<host>.<tld>` not already matched by `URL_RE` → fall back to `site_url`. Format: prefix `https://` if no scheme.

- [x] **Step 3: Split URL vs social based on host.** Known social hosts: `linkedin.com`, `github.com`, `twitter.com`, `x.com`, `mastodon.social`, `medium.com`. If the bare domain *is* a known social host, treat it as a social link. Otherwise, treat it as `site_url`. The third contact line on the benchmark is `rmahbub.com` → `site_url`.

- [x] **Step 4: Tests.** `api/tests/test_parsers.py`:
  - `test_social_re_matches_bare_handle_in_contact_line` — input `riasat-mahbub`, `Riasat Mahbub`, `rmahbub.com` separated by `·` → `social_links` has LinkedIn/GitHub entries (when recognisable), `site_url = "https://rmahbub.com"`.
  - `test_url_re_matches_bare_domain_when_no_scheme` — input `rmahbub.com` isolated → `site_url = "https://rmahbub.com"`.
  - `test_extract_profile_fields_does_not_double_prepend_scheme` — input `https://rmahbub.com` → `site_url = "https://rmahbub.com"` (no `https://https://`).

- [x] **Step 5: Verify.** `cd api && .venv/bin/pytest -q tests/test_parsers.py`. Spot-check the pipeline against the benchmark PDF: `python -c "..."` (driver inline) → `profile.data["site_url"] == "https://rmahbub.com"`, `profile.data["social_links"]` non-empty.

- [x] **Step 6: Tracker.** `tracker new task "pdf-parser: bare-handle contact regex" --priority High --tags parser,fix --description "..."`. `tracker update <bug-id> --note "Task 2: contact regex"`. `tracker rebuild && tracker validate`.

- [x] **Step 7: Commit.**
  ```
  fix(parser): recognise bare LinkedIn/GitHub handles and bare domains in contact lines

  The contact-line regexes only fired on scheme-prefixed URLs. Real-world
  resumes routinely emit bare handles ("riasat-mahbub") and bare domains
  ("rmahbub.com") separated by middot; the typed path forms
  (linkedin.com/in/<handle>, github.com/<handle>) never matched.

  - Add a contact-line bare-token pass in _extract_profile_fields:
    - bare <handle> in a known social host family → social link
    - bare <host>.<tld> → site_url (https:// prepended)
  - Existing URL_RE / LINKEDIN_RE / GITHUB_RE untouched; the new pass
    runs only after the existing sweep fails to claim a token.
  - New tests in tests/test_parsers.py lock the bare-handle behaviour.

  Closes TASK-01KZS8Y4Q…-contact.
  ```

---

## Task 3: Experience descriptions — continuation paragraphs

**Root cause:** the benchmark's experience descriptions are running paragraphs, not bulleted lists. `_extract_experience_fields` (classify.py:245-284) only collects a line as `description` when it matches `^\s*[•\-*]\s+`. Result: every experience entry's `description` is empty.

**Files:** `api/app/services/parser/classify.py`, `api/tests/test_parser_imports.py`.

- [x] **Step 1: New entry-boundary rule.** The current `_split_entries` splits on blank lines. The benchmark has no blank lines between entries — the date range of entry 1 is followed by the description, which is followed by `Associate Software Engineer` of entry 2. Detect a new entry by: a line that looks like a position/company header (e.g. preceded by a date range, or a line followed by another line that doesn't look like a continuation sentence). Two signals are good enough:
  - The line is the **first** non-meta line after a date range.
  - The line is the **first** non-meta, non-date line of a new section, or follows a previous entry's last non-meta line.

- [x] **Step 2: Switch the description heuristic.** Replace the bullet-only gate with: "**every non-meta, non-date line is a description sentence for the current entry until the next entry's position+company pair or the next date range**". The bullet regex stays as a *strip* (`description_lines.append(bullet_re.sub("", line).strip())`) but the *gate* opens: every remaining line is a description sentence.

- [x] **Step 3: De-dup stripped bullets.** If a line started with `•`, `*`, or `-`, strip the marker and the rest of the line is the description. Don't double-split.

- [x] **Step 4: Sentence-join.** Concatenate consecutive description lines with a single space (or `\n` if the line ended with a sentence terminator, but space is safer for paragraph-style resumes). The benchmark's descriptions are 4–5 lines of continuation text — joining with spaces preserves the original prose.

- [x] **Step 5: Tests.** `api/tests/test_parser_imports.py`:
  - `test_extract_experience_recovers_continuation_paragraphs` — fixture: position + company + date + 4-line paragraph + next position + company + date + 1-line paragraph → assert `entry[0]["description"]` contains the full paragraph, `entry[1]["description"]` contains the 1-line paragraph.
  - `test_extract_experience_strips_bullet_marker_when_present` — fixture: `- Built things` → `entry["description"] == "Built things"`.
  - `test_extract_experience_keeps_blank_line_split_for_compact_inputs` — existing test (`test_pipeline_emits_experience_with_title_and_company_split`) must still pass.

- [x] **Step 6: Verify.** `cd api && .venv/bin/pytest -q tests/test_parser_imports.py -k experience`. Spot-check the benchmark: `python -c "..."` → `experience.data[0]["description"]` contains the full "Worked with civil engineers…" prose.

- [x] **Step 7: Tracker.** `tracker new task "pdf-parser: experience description recovery" --priority High --tags parser,fix --description "..."`. `tracker update <bug-id> --note "Task 3: experience"`. `tracker rebuild && tracker validate`.

- [x] **Step 8: Commit.**
  ```
  fix(parser): recover experience descriptions when no bullets are present

  _extract_experience_fields only collected description lines that
  matched the bullet regex. Modern resumes usually write running
  paragraphs; the result was empty descriptions on every entry.

  - Description gate opens: every non-meta, non-date line is a
    description sentence for the current entry until the next entry's
    position+company pair or the next date range.
  - The bullet regex becomes a strip (removes the leading marker) but
    no longer gates inclusion.
  - Consecutive description lines are joined with a single space.
  - New tests in tests/test_parser_imports.py lock paragraph recovery.

  Closes TASK-01KZS8Y4Q…-experience.
  ```

---

## Task 4: Education — split on date-range boundaries

**Root cause:** `_extract_education_fields` (classify.py:287-318) splits on blank lines via `_split_entries`. The benchmark has two degrees (`Master of Computer Science` + `Bachelor of Computer Science and Engineering`) joined by the date range and the second institution in a single block; the blank-line split never fires because the PDF has no blank lines between entries. Result: one entry with the second degree dropped, or fields drifting.

**Files:** `api/app/services/parser/classify.py`, `api/tests/test_parser_imports.py`.

- [x] **Step 1: Split on date-range boundaries.** Re-implement `_extract_education_fields` to split the raw text on `DATE_RANGE_RE` matches (treat each date range as the *end* of one entry). For each entry, scan backwards from the date range to collect: the most recent degree-like line (containing `Bachelor` / `Master` / `PhD` / `Diploma` / etc.), then the most recent institution-like line (the line immediately before the degree).

- [x] **Step 2: Preserve the existing happy path.** The existing test fixture in `test_parser_imports.py` (if any) uses blank-line splits; that path must still work. The new logic *replaces* the blank-line split entirely — it doesn't add a second pass.

- [x] **Step 3: Tests.** `api/tests/test_parser_imports.py`:
  - `test_extract_education_splits_on_date_range` — fixture: `Master of Computer Science\nDalhousie University\nSeptember 2023 – October 2025\nBachelor of Computer Science and Engineering\nBRAC University\nJanuary 2018 – January 2022` → two entries, both with degree + institution + start/end dates.
  - `test_extract_education_survives_blank_line_split` — existing tests still pass.

- [x] **Step 4: Verify.** `cd api && .venv/bin/pytest -q tests/test_parser_imports.py -k education`. Spot-check the benchmark: `education.data` length 2, both with correct field values.

- [x] **Step 5: Tracker.** `tracker new task "pdf-parser: education entry split on date range" --priority High --tags parser,fix --description "..."`. `tracker update <bug-id> --note "Task 4: education"`. `tracker rebuild && tracker validate`.

- [x] **Step 6: Commit.**
  ```
  fix(parser): split education entries on date-range boundaries

  _extract_education_fields relied on blank lines to delimit entries.
  Real-world resumes often omit blank lines between the date range of
  entry N and the degree of entry N+1.

  - Re-implement _extract_education_fields to split on DATE_RANGE_RE
    matches: each date range closes one entry, the most recent
    degree-keyword line is the degree, the line immediately before is
    the institution.
  - New test in tests/test_parser_imports.py locks the two-entry case.

  Closes TASK-01KZS8Y4Q…-education.
  ```

---

## Task 5: Skills — peel category prefixes

**Root cause:** `_extract_skills_fields` (classify.py:321-328) splits on `,;\n•` and returns a flat list. The benchmark's skills section is structured as `Category: item1, item2, item3\nOther Category: item4, item5`. The current splitter collapses `Programming Languages: TypeScript, JavaScript` into `['Programming Languages: TypeScript', 'JavaScript', …]` — the category label is glued to the first item and the rest is decontextualised.

**Files:** `api/app/services/parser/classify.py`, `api/tests/test_parser_imports.py`.

- [x] **Step 1: Split on lines first, then peel category prefixes.** New regex: `^([A-Z][A-Za-z0-9 &/+-]+):\s*(.*)$` — matches `Programming Languages: TypeScript, JavaScript, Python` and yields `category="Programming Languages"`, `items="TypeScript, JavaScript, Python"`. Lines without a `:` prefix belong to the most recent category.

- [x] **Step 2: Multi-item category.** Once the category is established, split the items on `,;` and trim. Continue accumulating items into the same category until a new `Category: …` line appears.

- [x] **Step 3: Empty category fallback.** If a line has no `:`, emit it as a single-item category with `category=""`. Matches the existing mapper contract (`mapper.py:204-212`).

- [x] **Step 4: Update the mapper to consume the grouped shape.** `_extract_skills_fields` now returns `list[{"category", "items"}]`. The mapper (`map_to_sections` for skills, `mapper.py:204-212`) already iterates `data` as `list[{"category", "items"}]` — update the call site to pass the new shape directly.

- [x] **Step 5: Tests.** `api/tests/test_parser_imports.py`:
  - `test_extract_skills_groups_by_category_prefix` — fixture: 5 lines of `Category: item1, item2, …` → 5 groups, each with the right category and items.
  - `test_extract_skills_falls_back_to_uncategorised` — existing test (`test_pipeline_emits_skills_with_split_tokens`) must still pass.

- [x] **Step 6: Verify.** `cd api && .venv/bin/pytest -q tests/test_parser_imports.py -k skills`. Spot-check the benchmark: `skills.data[0]["category"] == "Programming Languages"`, items are clean.

- [x] **Step 7: Tracker.** `tracker new task "pdf-parser: skills category prefix parser" --priority High --tags parser,fix --description "..."`. `tracker update <bug-id> --note "Task 5: skills"`. `tracker rebuild && tracker validate`.

- [x] **Step 8: Commit.**
  ```
  fix(parser): peel category prefixes from skills lines

  The skills splitter collapsed "Programming Languages: TypeScript,
  JavaScript" into "Programming Languages: TypeScript" + "JavaScript",
  decontextualising the category label.

  - Split skills text on lines first; peel lines starting with
    "^([A-Z][A-Za-z0-9 &/+-]+):\s*" into category + items.
  - Subsequent lines without a prefix accumulate into the current
    category's items list.
  - _extract_skills_fields now returns list[{"category", "items"}]; the
    mapper already consumed that shape.
  - New test in tests/test_parser_imports.py locks the grouping.

  Closes TASK-01KZS8Y4Q…-skills.
  ```

---

## Task 6: Benchmark corpus fixture + integration assertion

**Root cause:** the parser has no real-world PDF in its test suite. `tests/fixtures/sample.pdf` is a hand-crafted 848-byte single-page PDF (Jane Doe + EXPERIENCE + SKILLS) — the parser knows it was hand-crafted. The benchmark corpus (`~/Downloads/Resume.pdf`) is the missing ground-truth.

**Files:** `api/tests/fixtures/sample.pdf`, `api/tests/test_parser_imports.py`, `api/tests/test_parser_smoke.py` (new).

- [x] **Step 1: Add the benchmark corpus as a fixture.** Copy `~/Downloads/Resume.pdf` to `api/tests/fixtures/resume-benchmark.pdf`. Add a comment in `api/tests/fixtures/__init__.py` (create if absent) describing the fixture's provenance (user's own CV, Riasat Mahbub, August 2026).

- [x] **Step 2: Add a real-PDF integration test.** `api/tests/test_parser_smoke.py` (new file):
  - `test_benchmark_corpus_emits_all_sections` — load the fixture, run `parse_cv`, assert every section type is present (profile, experience, education, projects, research, skills). Assert profile email/phone/name/site_url/non-empty social_links. Assert experience has 2 entries with full descriptions. Assert education has 2 entries. Assert skills has 5+ categories. Assert projects has 3 entries. Assert research has 4 entries.

- [x] **Step 3: Wire `sample.pdf` (the existing one) with a clarifying comment.** The existing fixture is a hand-crafted minimal CV. Comment above it explains it's the smoke-gate fixture, not a regression test. The new `resume-benchmark.pdf` is the regression test.

- [x] **Step 4: Tighten the `--smoke` gate.** `scripts/smoke.sh` already runs `pytest tests/test_smoke_live.py`. Add `tests/test_parser_smoke.py` to the same gate (or its own sub-run). Confirm the smoke still runs fast (the benchmark PDF is 54 KB; pypdf is ~150 ms).

- [x] **Step 5: Verify.** `cd api && .venv/bin/pytest -q tests/test_parser_imports.py tests/test_parser_smoke.py tests/test_extract_fonts.py tests/test_parsers.py`. Should be 100% green.

- [x] **Step 6: Final tracker.** `tracker update <bug-id> --status DONE --note "All six tasks closed. Benchmark corpus now parses end-to-end."`. `tracker new task "pdf-parser-resilience" --priority High --tags epic,parser --description "Umbrella for the six CommitPlan tasks."` then close it. `tracker rebuild && tracker validate`.

- [x] **Step 7: Commit.**
  ```
  test(parser): add benchmark corpus fixture and integration assertion

  The parser pipeline had no real-world PDF fixture. The user's own
  CV (~/Downloads/Resume.pdf) was the missing ground-truth — drop it
  into api/tests/fixtures/resume-benchmark.pdf and assert every
  section lands in the ParseResult.

  - New fixture: api/tests/fixtures/resume-benchmark.pdf (54 KB, real
    resume, 6 sections + 11 entries).
  - New test file: api/tests/test_parser_smoke.py asserts the
    end-to-end pipeline emits every section, every entry, and every
    non-empty field the user expects.
  - Existing tests/fixtures/sample.pdf remains the smoke-gate
    minimum (hand-crafted, 848 bytes).

  Closes TASK-01KZS8Y4Q…-fixture. Closes BUG-01KZS8Y4Q….
  ```

---

## Final verification

After the six commits:

```bash
cd api && pytest -q
# All tests pass — the existing 233 + the new ~15 tests in
# test_extract_fonts.py, test_parsers.py, test_parser_smoke.py.

cd web && npm test && npm run lint && npm run codegen:check
# All green (no frontend changes were made).

cd api && ruff check app/ scripts/ tests/
# Clean.

./dev.sh --smoke
# Hardening gate green.
```

Spot-check the benchmark corpus from the host shell:

```bash
source /home/riasat/Projects/aergia/api/.venv/bin/activate
python -c "
from pathlib import Path
from app.services.parser import parse_cv
import asyncio
result = asyncio.run(parse_cv(Path('/home/riasat/Downloads/Resume.pdf').read_bytes(), 'application/pdf'))
for s in result.sections:
    print(f'-- {s.type} ({len(s.data) if isinstance(s.data, list) else 1} entries) --')
"
```

Expected: `profile`, `experience`, `education`, `projects`, `research`, `skills` sections, each with the entries the benchmark corpus actually contains.

---

## Merge

After all six commits land on `fix/pdf-parser-resilience` and the smoke gate is green, merge into `master` with a regular merge commit (per `AGENTS.md`):

```
git checkout master
git merge --no-ff fix/pdf-parser-resilience -m "Merge branch 'fix/pdf-parser-resilience'"

fixes BUG-01KZS8Y4Q… and TASK-01KZS8Y4Q…-*.
```

Update the umbrella feature entry `FEAT-01KZS8Y4HAGJYHZE7SGGEGY03Q` (which already lists `extract.py` and `classify.py` in `AFFECTS`) via `tracker update` to note the post-merge hardening.

---

## Follow-up (out of scope for this plan)

- Layout-aware PDF extraction (the visitor-protocol extractor) — the follow-up entry already exists on `FEAT-01KZS8Y4HAGJYHZE7SGGEGY03Q` ("Layout-aware PDF extraction"). Promotes to PLANNED in the next round.
- The contact-line bare-handle detector could be made smarter about LinkedIn/GitHub host families (`linkedin.com/in/<handle>` is the canonical form; bare `<handle>` is ambiguous). A future iteration could consult the host's `<link>` tag from the PDF's `/Annots` to disambiguate.
- The skills category regex `^([A-Z][A-Za-z0-9 &/+-]+):\s*` accepts a lot of false positives. A future iteration could anchor on a known vocabulary (`Programming Languages`, `Frontend`, `Backend`, `DevOps & Tooling`, `AI/ML`, `Databases`, `Cloud`, `Tools`, `Soft Skills`, `Languages`, `Frameworks`, `Testing`).
