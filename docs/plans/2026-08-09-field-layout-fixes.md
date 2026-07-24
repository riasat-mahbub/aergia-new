# Field-Layout Fixes: right rails, link arrows, venue, typography consistency

> **For agentic workers:** implement this plan task-by-task — dispatch a fresh subagent per task with the native `task` tool, or use the superpowers-executing-plans skill to work through it inline. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix nine reported bugs/missing features in the section editors and the Python render pipeline: the "Publication Value" typo, venue missing from preview, right-rail placement for location / GPA / link text / certification dates, link arrows, certification link text, typography consistency across projects/certifications/research, and exclusive content accordions.

**Execution contract:** one commit per task, in order; each commit is self-contained (code + tests green for that task's scope) and carries its tracker update (`tracker new`/`tracker close` + `tracker rebuild && tracker validate`) so the tracker never drifts from the branch. Commit messages follow the repo's conventional style (`feat(…): …` / `fix(…): …` / `tracker: …`).

## Change request (2026-08-09, post-implementation)

Final link contract (after two direction corrections — see tracker chain):

1. **Link arrow is up-right diagonal** — `.f-link::after { content: " ↗"; }` (U+2197) instead of `→`.
2. **Live preview: NO working links.** `strip_anchor_hrefs` (in `api/app/routes/render.py`) neutralizes every anchor's href to `"#"` in both preview endpoints (`/render/html?preview=true` and `/cvs/{id}/preview`), so the sandboxed iframe never navigates away while editing. The anchor markup, inline styling, and the `.f-link` arrow are preserved — links are visible but dead. The iframe sandbox stays `allow-scripts allow-same-origin` (no `allow-popups`).
3. **PDF: clickable links.** The PDF paths (`/render/pdf` and `/cvs/{id}/export/pdf`) use the raw renderer output — the same document without the preview strip — so Chromium's print engine creates real link annotations (`/Subtype /Link` + `/URI`). Verified by generating a real PDF: annotations present for project/research/cert URLs, `pdftotext` shows `Repo ↗` / `PDF ↗`.

The original request text ("preview should have working links, but the pdf should not") was inverted relative to intent; the final contract is: preview dead, PDF alive. Tests: `api/tests/test_render_links.py` guards the preview strip (href→"#", markup preserved) and that the raw renderer output keeps real hrefs; the renderer arrow test asserts U+2197.

## Bug fix (2026-08-09): scheme-less hrefs drop PDF link annotations

**Symptom:** user's exported PDF showed link text (`github ↗`, `Certificate ↗`, `paper.com ↗`) but no clickable links — zero `/Subtype /Link` annotations.

**Root cause:** Chromium's print pipeline silently drops `<a href>` annotations when the href has no scheme (treated as a relative path against `about:blank`). The user's CV data stored scheme-less values (`github.com`, `asdgasdg…`, `paper`) — legacy/loose data that bypassed the frontend `urlSchema` (which rejects bare domains at form time). The backend already had `normalize_url_scheme` in `builders/_utils.py` documenting this exact quirk, but it was dead code — never wired into the link-emitting builders.

**Fix:** the three link builders (`projects`, `research`, `certifications`) now run `normalize_url_scheme` over the URL before emitting the anchor (`github.com` → `https://github.com`). Verified by re-exporting the exact CV: `/Subtype /Link` + `/URI` annotations present for all three links. Regression tests in `test_builders.py`.

**Architecture:** All placement/typography changes are *builder-emitted AST data* (`FieldBlock.group` / `.align` / `.key`, `TextRun.style`) plus renderer CSS. No Pydantic schema change, no manifest vocabulary change, no resolver change, no DB migration. The wire data keys (`name`, `title`, `publication_value`, `issuer`, `date`, `credential_url`, `paper_url`, `paper_link_text`, `url`, `link_text`) are untouched — only the internal AST field keys and the panel's `FIELD_DEFS` change, in lockstep.

**Tech Stack:** Python 3.12 + Pydantic v2 + FastAPI, HTMLDocumentRenderer (inline-styled HTML5), React 19 + Vitest, project-tracker SCHEMA 3, pytest, Ruff, `./dev.sh --smoke`.

---

## File structure

| File | Responsibility | Change |
|---|---|---|
| `api/app/services/renderer/builders/experience.py` | Experience fields | `location` gains `align="right"`; stale docstring fix |
| `api/app/services/renderer/builders/education.py` | Education fields | `gpa` moves to `group="secondary"` + `align="right"` |
| `api/app/services/renderer/builders/projects.py` | Projects fields | `name`→key `project`; `link` right rail + `TextStyle(link=url)`; `tech.<i>`→key `tech` |
| `api/app/services/renderer/builders/research.py` | Research fields | `title`→key `paper`; new `venue` field from `publication_value`; `link` right rail + href |
| `api/app/services/renderer/builders/certifications.py` | Certification fields | `name`→key `certification`; `meta` split into `issuer` + `date`(right); `link` right rail + href + `link_text` |
| `api/app/services/renderer/builders/__init__.py` | Field-style bridge | `apply_field_text_styles` merges (not replaces) run style so `link` hrefs survive user styling |
| `api/app/services/renderer/html.py` | Renderer CSS | Size groups for `.f-venue`/`.f-issuer`/`.f-link`; weight-600 for `.f-project`/`.f-certification`/`.f-paper`; `.f-link::after` arrow; drop dead `.f-url` |
| `web/src/components/sections/research/ResearchEditor.tsx` | Editor | Label "Publication Value" → "Publication Venue" |
| `web/src/components/sections/certifications/CertificationsEditor.tsx` | Editor | Add Link Text input |
| `web/src/lib/sections/types.ts` | Entry types | `CertificationEntry.link_text?` |
| `web/src/lib/validators/sections.ts` | Zod schemas | `certificationEntrySchema` gains `link_text` |
| `web/src/lib/sections/fieldStyles.ts` | Panel field defs | Keys aligned to builders (`project`/`link`/`certification`/`issuer`/`paper`/`venue`) |
| `web/src/components/builder/ContentSectionList.tsx` | Content accordions | `expandedSections: Set` → single `expandedSectionId` (exclusive open) |
| `api/tests/test_builders.py` | Builder tests | Key/group/align/href assertions |
| `api/tests/test_html_renderer.py` | Renderer tests | Rail rows, link arrow/href, new CSS classes |
| `web/src/components/__tests__/ContentSectionList.test.tsx` | Accordion test | Exclusivity case |
| `web/src/lib/validators/__tests__/sections.test.ts` | Validator test | `link_text` accepted on certifications |
| `tracker/` | Project graph | Task entry, closed, rebuilt |

**Target row model per entry** (builder `group` + `align` after the change):

| Section | header row | secondary row | body |
|---|---|---|---|
| experience | `position` + `date` (right) | `company` + `location` (right) | `description` |
| education | `degree` + `date` (right) | `institution` + `gpa` (right) | `summary` |
| projects | `project` + `date` (right) | `link` (right) | `description` + `tech` |
| certifications | `certification` | `issuer` + `date` (right) | `link` (right) |
| research | `paper` + `date` (right) | `venue` + `link` (right) | `description` |

**Field keys after the change** (must match `FIELD_DEFS` keys exactly — the panel writes `text[key]` and `apply_field_text_styles` matches `field.key`):

| Section | keys |
|---|---|
| experience | `position`, `date`, `company`, `location`, `description` |
| education | `degree`, `date`, `institution`, `gpa`, `summary` |
| projects | `project`, `date`, `link`, `description`, `tech` |
| certifications | `certification`, `issuer`, `date`, `link` |
| research | `paper`, `date`, `venue`, `link`, `description` |

**Renderer rule reused:** a right-aligned field (`align="right"`) in a row becomes the row's right rail (`margin-left:auto`); consecutive same-group fields share one flex row. All five sections now follow one visual grammar: title-weight header left, date right; secondary info left, small meta right; link under the date on the right with an arrow.

**Design note — why only the *conflicting* keys get renamed, not every key in every section:**

A key collision only matters when the sections sharing it want *different* default typography. After the renames in this plan, every remaining shared key (`date`, `description`, `link`, `location`, `summary`) carries identical intent in every section that uses it — one CSS rule serves them all, and that is the point of the `.f-{key}` vocabulary, not a defect. Renaming everything would:

1. silently orphan **every** saved per-field style (`text.*`) in **every** section — the plan's blast radius is deliberately limited to the three sections whose keys were already mis-keyed (`url` vs `link`, `tech.<i>` vs `tech`) or conflicting (`name`, `title`);
2. multiply identical CSS rules fivefold (five `.f-date`-equivalent rules for the same 0.75rem value);
3. churn every builder test, `FIELD_DEFS`, and DOM class with zero present-day behavioral gain.

Per-field styling is already isolated per section instance (`apply_field_text_styles` consumes the instance's own `style.text`), so a shared key can never leak user styling across sections. If future intent-divergence (e.g. education dates styled differently from project dates) is a real concern, the mechanism is section-type-scoped CSS defaults (`section[data-type="…"]` selectors), not key renames — that is a renderer-architecture decision, deliberately out of scope here.

**Does the shared key interfere with the customize panel? No.** The panel edits one section at a time: it reads/writes the *selected instance's* `style.text[field_key]` (`CustomizePanel.tsx`, `selectedStyle.text?.[f.key]`), and the cascade applies that map only to that instance (`apply_field_text_styles(section, instance.style.text)`; `Customizations.per_section[id]` in the resolver). Styling "Date" in Education writes Education's `text.date` only — Projects, Experience, etc. each carry their own `text` dict and are untouched. The shared `date` key names only the renderer's *default* CSS class (`.f-date { font-size: 0.75rem }`), and any user override is emitted inline on the run, which beats the class. There is no global per-field style map anywhere in the pipeline (verified: `TemplateManifest` exposes only `global_styles`/`layout_defaults`/`policy_overrides`; `Customizations` per-field styling is `per_section`, keyed by section id). The only document-wide knobs — body font, accent color, spacing, default text align — are intentionally document-wide, and none of them touch per-field `text` styles.

---

## Task 1: Research venue — typo + missing from preview (bugs 1–2)

**Root cause of bug 2:** `build_research` never reads `publication_value`; the field is collected by the editor and validated by Zod but dropped at the AST boundary, so it never reaches the HTML renderer → no preview, no PDF. The label typo is in `ResearchEditor.tsx`.

**Files:** `api/app/services/renderer/builders/research.py`, `web/src/components/sections/research/ResearchEditor.tsx`, `web/src/lib/sections/fieldStyles.ts`, `api/tests/test_builders.py`.

- [x] **Step 1: Fix the editor label.** In `web/src/components/sections/research/ResearchEditor.tsx:42` change `Publication Value` → `Publication Venue`. Keep the wire key `publication_value` (renaming it would orphan saved CV data; the key is internal and only the label was wrong).

- [x] **Step 2: Emit the venue field.** In `build_research`, after the `date` field and before `link`:

```python
venue = str(row.get("publication_value") or "").strip()
if venue:
    fields.append(FieldBlock(key="venue", group="secondary", runs=[TextRun(text=venue)]))
```

- [x] **Step 3: Add the field def.** In `web/src/lib/sections/fieldStyles.ts`, research becomes:

```ts
research: [{ key: "paper", label: "Paper title" }, { key: "venue", label: "Venue" }, { key: "link", label: "Paper link" }, { key: "date", label: "Publication date" }, { key: "description", label: "Description" }],
```

(`paper` replaces `title` per Task 6; both land in the same edit.)

- [x] **Step 4: Update builder tests.** `test_research_emits_title_link_date_description` asserts `keys == ["title", "date", "link", "description"]`. With a fixture row carrying `publication_value`, expect `["paper", "date", "venue", "link", "description"]`. Add a companion assertion that a row **without** `publication_value` emits no `venue` field.

- [x] **Step 5: Verify.** `cd api && .venv/bin/pytest -q tests/test_builders.py -k research` and a live check: render a CV with a research entry via `/render/html` (or the smoke live render) and confirm the venue text appears in the HTML.

---

## Task 2: Experience — location right, under date (bug 3)

**Root cause:** the builder emits `location` in `group="secondary"` without `align`, so it sits left-aligned next to `company` instead of on the right edge.

**Files:** `api/app/services/renderer/builders/experience.py`, `api/tests/test_builders.py`.

- [x] **Step 1: Right-align location.**

```python
if row.get("location"):
    fields.append(FieldBlock(key="location", group="secondary", align="right", runs=[TextRun(text=str(row["location"]))]))
```

The renderer already puts `company` (left) and `location` (right rail) in one flex row — the row directly under the header row that holds the date.

- [x] **Step 2: Fix the stale docstring.** The module docstring says "The renderer joins company + location with a comma when location is present" — no comma logic exists in `html.py`; location is now a right rail. Rewrite the sentence to describe the row model (`company` left, `location` right rail).

- [x] **Step 3: Test.** Extend `test_experience_fields_carry_row_groups` (or add a new test): `fields["location"].align == "right"` and `fields["location"].group == "secondary"`.

- [x] **Step 4: Verify.** `cd api && .venv/bin/pytest -q tests/test_builders.py -k experience`; renderer smoke: the `f-location` div carries `margin-left:auto` in its row.

---

## Task 3: Education — GPA right, under date (bug 4)

**Root cause:** `gpa` is emitted in `group="meta"` (its own left-aligned row) instead of sitting on the institution row as a right rail.

**Files:** `api/app/services/renderer/builders/education.py`, `api/tests/test_builders.py`.

- [x] **Step 1: Move gpa onto the secondary row as a rail.**

```python
if row.get("gpa"):
    fields.append(FieldBlock(key="gpa", group="secondary", align="right", runs=[TextRun(text=str(row["gpa"]))]))
```

`institution` + `gpa` now share one row (institution left, GPA right), directly under the `degree`/`date` header row.

- [x] **Step 2: Test.** Assert `fields["gpa"].group == "secondary"` and `fields["gpa"].align == "right"` (update any assertion that expects `group == "meta"`; the `meta` group disappears from education).

- [x] **Step 3: Verify.** `cd api && .venv/bin/pytest -q tests/test_builders.py -k education`.

---

## Task 4: Link text — right rail + arrow + real href + cert link text (bugs 5, 7)

**Root cause of the missing arrow/alignment:** link fields (`key="link"`) are emitted left-aligned with a plain `TextRun` (no `TextStyle.link`), so the renderer emits a bare `<span>` with no right rail, no href, and no `f-link` CSS class. Certifications additionally render the raw URL as the link text because there is no `link_text` input.

**Files:** `api/app/services/renderer/builders/projects.py`, `.../research.py`, `.../certifications.py`, `.../__init__.py`, `api/app/services/renderer/html.py`, `web/src/components/sections/certifications/CertificationsEditor.tsx`, `web/src/lib/sections/types.ts`, `web/src/lib/validators/sections.ts`, `api/tests/test_builders.py`, `api/tests/test_html_renderer.py`.

- [x] **Step 1: Builders — right rail + href.** In all three builders, emit the link field with `align="right"` and a link style so `_render_text_run` produces a real `<a href="…">` (the preview iframe neutralizes hrefs via `strip_anchor_hrefs`, the PDF keeps them):

```python
# projects.py
if url:
    fields.append(FieldBlock(
        key="link", group="secondary", align="right",
        runs=[TextRun(text=link_text, style=TextStyle(link=url))],
    ))

# research.py — same shape, group="secondary", link_text default "Paper"
# certifications.py — same shape, group="body" (stays its own row), link_text default "Certificate"
```

- [x] **Step 2: Preserve hrefs through field styling.** `apply_field_text_styles` in `builders/__init__.py` currently **replaces** `run.style` with the user's `TextStyle` — which would drop the `link` href whenever the user styles the link field. Merge instead:

```python
new_fields.append(field.model_copy(update={
    "runs": [
        r.model_copy(update={"style": _with_link(r, ts)})
        for r in field.runs
    ],
}))
```

where `_with_link(run, ts)` returns `ts` when the run has no href, else `ts.model_copy(update={"link": run.style.link})`. Add a unit test: a link field with a user `text["link"]` style keeps `run.style.link`.

- [x] **Step 3: Certification link text.** Add `link_text` end to end:
  - `web/src/lib/sections/types.ts`: `CertificationEntry` gains `link_text?: string;`
  - `web/src/lib/validators/sections.ts`: `certificationEntrySchema` gains `link_text: z.string(),`
  - `web/src/components/sections/certifications/CertificationsEditor.tsx`: default entry factory gains `link_text: ""`; add a "Link Text" input (placeholder `Certificate`) next to the Credential URL input
  - `build_certifications`: `link_text = str(row.get("link_text") or "Certificate")` used as the run text
  - `web/src/lib/validators/__tests__/sections.test.ts`: certification fixture with `link_text` validates

- [x] **Step 4: Arrow + size in renderer CSS.** In `html.py` `_render_document`:
  - add `.f-link` to the `0.75rem` size group (matches `.f-date`/`.f-gpa` — the "base" small-meta size)
  - add the arrow:

```css
.f-link::after {{ content: " →"; }}
```

  (U+2192 renders in Chromium and in PDF print. The arrow inherits the field color/font-size.)

- [x] **Step 5: Tests.**
  - `test_builders.py`: link fields carry `align == "right"` and `runs[0].style.link == url` for projects/research/certifications; cert link run text equals `link_text` (and falls back to `"Certificate"`).
  - `test_html_renderer.py`: a model with a project/research/cert link renders `<a href="…">`, the `f-link` div sits in a row with `margin-left:auto`, and the stylesheet contains `.f-link::after`.

- [x] **Step 6: Verify.** `cd api && .venv/bin/pytest -q tests/test_builders.py tests/test_html_renderer.py`.

---

## Task 5: Certification date — right rail (bug 6)

**Root cause:** the builder joins `issuer · date` into one `meta` field, so the date cannot be independently aligned.

**Files:** `api/app/services/renderer/builders/certifications.py`, `web/src/lib/sections/fieldStyles.ts`, `api/tests/test_builders.py`.

- [x] **Step 1: Split `meta` into `issuer` + `date`.**

```python
issuer = str(row.get("issuer") or "").strip()
if issuer:
    fields.append(FieldBlock(key="issuer", group="secondary", runs=[TextRun(text=issuer)]))

raw_date = str(row.get("date") or "")
if raw_date:
    formatted = format_single_date(raw_date)
    fields.append(FieldBlock(key="date", group="secondary", align="right", runs=[TextRun(text=formatted)]))
```

Row: `issuer` left, `date` right rail, under the certification name — same grammar as experience (`company`/`location`) and education (`institution`/`gpa`).

- [x] **Step 2: Update field defs.** `fieldStyles.ts` certifications becomes:

```ts
certifications: [{ key: "certification", label: "Name" }, { key: "issuer", label: "Issuer" }, { key: "date", label: "Date" }, { key: "link", label: "Credential link" }],
```

(`certification` replaces `name` per Task 6; `meta` and the mis-keyed `url` are gone — see risk register.)

- [x] **Step 3: Tests.** `test_certifications_emits_name_meta_link` becomes `keys == ["certification", "issuer", "date", "link"]`; assert `date.align == "right"`; a row with no `date` emits no date field.

- [x] **Step 4: Verify.** `cd api && .venv/bin/pytest -q tests/test_builders.py -k cert`.

---

## Task 6: Typography consistency — one grammar off experience/education (bug 8)

**Root cause:** the renderer's CSS classes are keyed by field key and shared across sections. `projects` and `certifications` both emit `key="name"`, so they inherit the *profile-name* class (`.f-name`: 1.5rem / 700) — project and certification names render huge. Research `title` shares `.f-title` with the profile subtitle (0.875rem, no weight). Link fields have no size class at all (default 1rem). Also, `FIELD_DEFS` keys (`url`, `tech`) don't match builder keys (`link`, `tech.<i>`), so per-field styling of links and tech silently never applies.

**Target grammar (from experience/education):** header title = weight 600 at body size; date/meta = 0.75rem; secondary line = 0.875rem; description = 0.875rem; weight-600 rule currently covers `.f-position, .f-degree` only.

**Files:** all five builders, `api/app/services/renderer/html.py`, `web/src/lib/sections/fieldStyles.ts`, `api/tests/test_builders.py`.

- [x] **Step 1: Section-specific header keys** (already applied in Tasks 1–5):
  - projects: `name` → `project`
  - certifications: `name` → `certification`
  - research: `title` → `paper`

  Data keys on the wire stay `name`/`title`; only the AST field key changes.

- [x] **Step 2: Tech keys.** In `build_projects`, emit every tech chip as `FieldBlock(key="tech", group="body", …)` instead of `tech.<i>`. `apply_field_text_styles` then applies one `text["tech"]` style to all chips (that is the panel's existing intent — `FIELD_DEFS.projects` already lists `tech`).

- [x] **Step 3: CSS.** In `html.py` `_render_document`:

```css
/* secondary line (0.875rem group): */
.f-title, .f-summary, .f-company, .f-description, .f-institution, .f-category, .f-venue, .f-issuer { font-size: 0.875rem; }
/* small meta (0.75rem group): add .f-link */
.f-contact, .f-contact-sep, .f-email, .f-phone, .f-location, .f-site, .f-social-links, .f-date, .f-gpa, .f-link, .f-tech, .f-tag, .f-proficiency, .f-meta { font-size: 0.75rem; }
/* header titles (weight 600): */
.f-position, .f-degree, .f-project, .f-certification, .f-paper { font-weight: 600; }
```

  Remove the now-dead `.f-url` from the 0.75rem group (no builder emits `key="url"`).

- [x] **Step 4: Update builder key assertions** (`test_builders.py`): projects `["project", "date", "link", "description", "tech", "tech"]` (two tech chips, same key — the list may contain duplicates; assert membership/order instead if that is cleaner), certifications `["certification", "issuer", "date", "link"]`, research `["paper", "date", "venue", "link", "description"]`.

- [x] **Step 5: Renderer test.** Assert the stylesheet contains `.f-project`/`.f-certification`/`.f-paper` in the weight-600 rule and `.f-link` in the 0.75rem rule (a `test_*_consistency` test that greps the rendered `<style>` block).

- [x] **Step 6: Verify.** `cd api && .venv/bin/pytest -q tests/test_builders.py tests/test_html_renderer.py && cd ../web && npm run test -- --run`.

---

## Task 7: Exclusive content accordions (bug 9)

**Root cause:** `ContentSectionList` holds `expandedSections: Set<string>` and toggles membership, so any number of section editors can be open at once.

**Files:** `web/src/components/builder/ContentSectionList.tsx`, `web/src/components/__tests__/ContentSectionList.test.tsx`.

- [x] **Step 1: Single open section.**

```tsx
const [expandedSectionId, setExpandedSectionId] = useState<string | null>(null);

const toggleSectionExpand = (id: string) => {
  setExpandedSectionId((prev) => (prev === id ? null : id));
};
```

`SortableRow` gets `isExpanded={expandedSectionId === instance.id}`.

- [x] **Step 2: Test.** Extend `ContentSectionList.test.tsx` with an exclusivity case: expand section 1, then section 2 → `getAllByTitle("Collapse").length === 1` and it belongs to section 2's row.

- [x] **Step 3: Verify.** `cd web && npm run test -- --run ContentSectionList`.

**Scope note (flag):** the *entry-level* accordions inside each section (`AccordionPanel` in `SortableAccordionList`, per-entry local `open` state) stay independently toggleable — multiple entries within one section can still be open. Making those exclusive requires lifting state through `SortableAccordionList`; not included unless requested.

---

## Task 8: Full verification gate

- [x] `cd api && .venv/bin/pytest -q`
- [x] `cd api && .venv/bin/ruff check .`
- [x] `cd web && npm run test -- --run`
- [x] `cd web && npm run lint` (or `eslint --config web/eslint.config.smoke.js .` as in smoke)
- [x] `cd web && npm run build`
- [x] `./dev.sh --smoke` (runs all of the above + live preview/PDF smoke against the three seed templates)
- [x] Manual spot check: research entry with `publication_value` renders the venue in preview; project/research/cert links show `Link →` right-aligned under the date and are clickable in the exported PDF; cert dates right-aligned; one content section open at a time.

---

## Risk register

1. **`f-name` key collision (root of bug 8).** Projects/certifications reuse `key="name"`, inheriting profile-name typography. Fix = section-specific keys. Consequence: saved per-field styles under `text.name` / `text.title` for projects/certs/research stop applying. They were partly dead already (`text.url` never matched the `link` key), so real-world impact is minimal; the panel writes the new keys from the moment `FIELD_DEFS` changes. Accepted clean-cutover tradeoff.
2. **`apply_field_text_styles` replacement.** Without the merge in Task 4 Step 2, styling a link field drops its href. The merge is mandatory, not optional.
3. **Certification `meta` key removed.** Per-field styles saved under `text.meta` stop applying once `meta` splits into `issuer`/`date`. Same category as (1); accepted.
4. **`date_style` LayoutHints is currently a no-op** (no builder passes a `DateStyle` to `format_single_date`/`format_date_range`; the resolver sets `layout.date_style` after date strings are already formatted). Pre-existing; out of scope here — flagged so it is not mistaken for a regression. A follow-up can thread `instance.style.layout.date_style` through the builders.
5. **Exclusive accordions are section-level only** (see Task 7 scope note). Entry-level accordions within a section remain multi-open.
6. **Arrow glyph.** `content: " →"` (U+2192) is safe in Chromium and PDF; the smoke live render exercises it against all three seed templates.
7. **Tech chips share one key.** Two `FieldBlock`s with `key="tech"` in one row is valid (keys need not be unique); only `apply_field_text_styles` and the CSS class consume the key, both fine with duplicates. The builder test should assert membership rather than strict list equality if duplicates make the assertion brittle.
