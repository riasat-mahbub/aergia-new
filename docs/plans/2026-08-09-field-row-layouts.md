# Field-Row Layouts with Social Icons (Option A) Implementation Plan

> **For agentic workers:** implement this plan task-by-task — dispatch a fresh subagent per task with the native `task` tool (recommended for quality), or use the superpowers-executing-plans skill to work through it inline. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore sophisticated field layouts — fields grouped into semantic rows (name / contact / social / summary for profile; header / meta / body for the rest) with social icons — by adding a `group` + `icon` attribute to the AST `FieldBlock` and rendering rows in the HTML renderer. Per-CV customizations, per-field `TextStyle` (bold/italic/color/size), zones, and the PDF pipeline are untouched.

**Architecture:** Option A — grouping is *derived data*, declared by the builders per section type (exactly like `SECTION_POLICIES`). `FieldBlock` gains `group: str | None` (row name) and `icon: str | None` (social icon name). The renderer wraps consecutive same-group fields in one flex row; social fields render a small inline SVG from a renderer-owned icon table, falling back to plain text for unknown names. No schema vocabulary for users, no manifest changes, no resolver changes, no frontend changes beyond the regenerated `schema.ts`.

**Tech Stack:** Python 3.12 + Pydantic v2 + FastAPI, HTMLDocumentRenderer (inline-styled HTML5), project-tracker SCHEMA 3, pytest, Ruff, Vitest, `./dev.sh --smoke`.

---

## File structure

| File | Responsibility | Change |
|---|---|---|
| `api/app/schema/models.py` | `FieldBlock` AST node | Add `group` + `icon` fields |
| `web/src/generated/schema.ts` | Codegen output | Regenerate (auto-discovery picks up FieldBlock) |
| `api/app/services/renderer/builders/profile.py` | Profile fields | Emit groups + social icons |
| `api/app/services/renderer/builders/experience.py` | Experience fields | Emit groups |
| `api/app/services/renderer/builders/education.py` | Education fields | Emit groups |
| `api/app/services/renderer/builders/skills.py` | Skills fields | Emit groups |
| `api/app/services/renderer/builders/projects.py` | Projects fields | Emit groups |
| `api/app/services/renderer/builders/languages.py` | Languages fields | Emit groups |
| `api/app/services/renderer/builders/certifications.py` | Certifications fields | Emit groups |
| `api/app/services/renderer/builders/research.py` | Research fields | Emit groups |
| `api/app/services/renderer/html.py` | HTML emission | Row grouping, icon table, `.field-row` CSS |
| `api/tests/test_schema.py` | Schema tests | FieldBlock accepts group/icon |
| `api/tests/test_builders.py` | Builder tests | Per-type group + icon assertions |
| `api/tests/test_html_renderer.py` | Renderer tests | Row divs, separators, icons |
| `tracker/` | Project graph | Feature + 3 task entries, closed, rebuilt |

**Row model per section type** (the exact `group` values builders will emit):

| Section | `header` | `meta` | `body` | other |
|---|---|---|---|---|
| profile | — | — | — | name→`main`, title→`subtitle`, email/phone/location/site_text→`contact`, `social_links.{i}`→`social` (+icon), summary→`summary` |
| experience | position, company | location, date | description | — |
| education | degree, institution | date | gpa, summary | — |
| skills | category | — | `tag.{i}` | — |
| projects | name, link | date | description, `tech.{i}` | — |
| languages | language, proficiency | — | — | — |
| certifications | name, meta | — | link | — |
| research | title, link | date | description | — |

**Renderer rule:** consecutive fields with the same non-`None` `group` render inside one `<div class="field-row">` (flex, wrap, baseline, gap). A field with `group=None` renders as its own row wrapper (identical to today's look). The `.entry` column keeps its `var(--spacing-subsection)` gap, so spacing *between rows* is unchanged.

**Known pre-existing gap (not fixed here):** `SectionPolicy.skill_variant` (`inline`/`block`) is declared `FULL` in `RendererSupport` but the HTML renderer has no markup for it (`html.py` has no `skill_variant` handling). Grouping skills tags into one `body` row makes tags flow inline visually; the policy itself stays a no-op. Recorded in the risk register; out of scope.

---

## Task 1: FieldBlock schema — `group` and `icon`

**Files:**
- Modify: `api/app/schema/models.py:164-169` (`class FieldBlock`)
- Test: `api/tests/test_schema.py`
- Regenerate: `web/src/generated/schema.ts`

- [ ] **Step 1: Write the failing schema test**

Append to `api/tests/test_schema.py`:

```python
def test_field_block_accepts_group_and_icon():
    """FieldBlock carries the row-group and social-icon metadata that the
    builders emit and the renderer consumes (Option A row layouts)."""
    from app.schema.models import FieldBlock, TextRun

    fb = FieldBlock(key="social_links.0", runs=[TextRun(text="X")], group="social", icon="x")
    assert fb.group == "social"
    assert fb.icon == "x"
    assert FieldBlock(key="name", runs=[TextRun(text="Ada")]).group is None
```

- [ ] **Step 2: Run it — verify it fails**

```bash
cd api && .venv/bin/pytest -q tests/test_schema.py::test_field_block_accepts_group_and_icon
```

Expected: FAIL — `TypeError: FieldBlock.__init__() got an unexpected keyword argument 'group'`.

- [ ] **Step 3: Implement the schema change**

In `api/app/schema/models.py`, change:

```python
class FieldBlock(BaseModel):
    """A named field (e.g. ``"company"``, ``"title"``) containing one or more
    text runs. The renderer emits a ``<div class="f-{key}">`` wrapper."""

    key: str
    runs: list[TextRun]
```

to:

```python
class FieldBlock(BaseModel):
    """A named field (e.g. ``"company"``, ``"title"``) containing one or more
    text runs. The renderer emits a ``<div class="f-{key}">`` wrapper.

    ``group`` names the semantic row the field belongs to (``"header"``,
    ``"contact"``, ``"social"``, ``"body"``, ...); consecutive same-group
    fields render inline in one row. ``icon`` names a social icon for the
    field; the renderer draws it from its icon table when known."""

    key: str
    runs: list[TextRun]
    group: str | None = None
    icon: str | None = None
```

- [ ] **Step 4: Run the test — verify it passes**

```bash
cd api && .venv/bin/pytest -q tests/test_schema.py::test_field_block_accepts_group_and_icon
```

Expected: PASS.

- [ ] **Step 5: Regenerate the TypeScript schema**

```bash
cd api && .venv/bin/python scripts/codegen_schema.py && .venv/bin/python scripts/codegen_schema.py --check
```

Expected: `--check` exits 0; `web/src/generated/schema.ts` now has `"group"?: (string) | null;` and `"icon"?: (string) | null;` in the `FieldBlock` interface. The codegen drift test (`test_codegen.py`) passes automatically.

- [ ] **Step 6: Run the backend suite + frontend build (no regressions)**

```bash
cd api && rm -f data/aergia.test.db && .venv/bin/pytest -q
cd web && npm run build
```

Expected: all backend tests pass; `tsc -b && vite build` exits 0 (no frontend code constructs `FieldBlock` — verified by grep).

- [ ] **Step 7: Commit**

```bash
git add api/app/schema/models.py api/tests/test_schema.py web/src/generated/schema.ts
git commit -m "Field rows / Step 1: FieldBlock gains group and icon metadata"
```

---

## Task 2: Profile builder — groups and social icons

**Files:**
- Modify: `api/app/services/renderer/builders/profile.py`
- Test: `api/tests/test_builders.py`

- [ ] **Step 1: Write the failing builder test**

Append to `api/tests/test_builders.py`:

```python
def test_profile_fields_carry_row_groups_and_icons():
    """Profile fields are grouped into semantic rows: main (name), subtitle
    (title), contact (email/phone/location/site), social (links + icons),
    summary. This restores the sophisticated profile layout."""
    cv = _cv([{
        "id": "s1",
        "type": "profile",
        "title": "Profile",
        "enabled": True,
        "data": {
            "name": "Ada",
            "title": "Engineer",
            "email": "a@b.com",
            "phone": "123",
            "location": "London",
            "site_text": "ada.dev",
            "summary": "Pioneer",
            "social_links": [
                {"label": "X", "url": "https://x.com/ada", "icon": "x"},
                {"label": "GitHub", "url": "https://github.com/ada", "icon": "github"},
            ],
        },
    }])
    doc = build_document(cv)
    fields = {f.key: f for f in doc.sections[0].entries[0].fields}

    assert fields["name"].group == "main"
    assert fields["title"].group == "subtitle"
    assert fields["email"].group == "contact"
    assert fields["phone"].group == "contact"
    assert fields["location"].group == "contact"
    assert fields["site_text"].group == "contact"
    assert fields["summary"].group == "summary"

    assert fields["social_links.0"].group == "social"
    assert fields["social_links.0"].icon == "x"
    assert fields["social_links.1"].group == "social"
    assert fields["social_links.1"].icon == "github"


def test_profile_social_links_without_icon_name_get_no_icon():
    cv = _cv([{
        "id": "s1",
        "type": "profile",
        "title": "Profile",
        "enabled": True,
        "data": {
            "name": "Ada",
            "social_links": [{"label": "Site", "url": "https://ada.dev"}],
        },
    }])
    doc = build_document(cv)
    fields = {f.key: f for f in doc.sections[0].entries[0].fields}
    assert fields["social_links.0"].group == "social"
    assert fields["social_links.0"].icon is None
```

- [ ] **Step 2: Run — verify it fails**

```bash
cd api && .venv/bin/pytest -q tests/test_builders.py::test_profile_fields_carry_row_groups_and_icons tests/test_builders.py::test_profile_social_links_without_icon_name_get_no_icon
```

Expected: FAIL — `AttributeError: 'FieldBlock' object has no attribute 'group'`.

- [ ] **Step 3: Implement**

In `api/app/services/renderer/builders/profile.py`, add `group=` to every `fields.append(FieldBlock(...))` call:

```python
    fields.append(FieldBlock(key="name", group="main", runs=[TextRun(text=str(data.get("name", "") or ""))]))
    if data.get("title"):
        fields.append(FieldBlock(key="title", group="subtitle", runs=[TextRun(text=str(data["title"]))]))
    if data.get("email"):
        fields.append(FieldBlock(key="email", group="contact", runs=[TextRun(text=str(data["email"]))]))
    if data.get("phone"):
        fields.append(FieldBlock(key="phone", group="contact", runs=[TextRun(text=str(data["phone"]))]))
    if data.get("location"):
        fields.append(FieldBlock(key="location", group="contact", runs=[TextRun(text=str(data["location"]))]))
```

For the site field (around line 42):

```python
        fields.append(FieldBlock(key="site_text", group="contact", runs=[TextRun(text=site_text)]))
```

For the summary (around line 45):

```python
        fields.append(FieldBlock(key="summary", group="summary", runs=[TextRun(text=str(data["summary"]))]))
```

For the social links loop (around lines 47-59), change:

```python
    social_links = data.get("social_links") or []
    for i, link in enumerate(social_links):
        if not isinstance(link, dict):
            continue
        url = str(link.get("url") or "")
        if not url:
            continue
        label = str(link.get("label") or url)
        fields.append(
            FieldBlock(
                key=f"social_links.{i}",
                runs=[TextRun(text=label)],
            )
        )
```

to:

```python
    social_links = data.get("social_links") or []
    for i, link in enumerate(social_links):
        if not isinstance(link, dict):
            continue
        url = str(link.get("url") or "")
        if not url:
            continue
        label = str(link.get("label") or url)
        icon = str(link.get("icon") or "") or None
        fields.append(
            FieldBlock(
                key=f"social_links.{i}",
                group="social",
                icon=icon,
                runs=[TextRun(text=label)],
            )
        )
```

- [ ] **Step 4: Run — verify it passes**

```bash
cd api && .venv/bin/pytest -q tests/test_builders.py::test_profile_fields_carry_row_groups_and_icons tests/test_builders.py::test_profile_social_links_without_icon_name_get_no_icon
```

Expected: PASS. Also run the full builder file: `.venv/bin/pytest -q tests/test_builders.py` — all pass.

- [ ] **Step 5: Commit**

```bash
git add api/app/services/renderer/builders/profile.py api/tests/test_builders.py
git commit -m "Field rows / Step 2: profile builder emits field groups and social icons"
```

---

## Task 3: Remaining builders — field groups

**Files:**
- Modify: `api/app/services/renderer/builders/{experience,education,skills,projects,languages,certifications,research}.py`
- Test: `api/tests/test_builders.py`

- [ ] **Step 1: Write the failing tests**

Append to `api/tests/test_builders.py`:

```python
def test_experience_fields_carry_row_groups():
    cv = _cv([{
        "id": "s1", "type": "experience", "title": "Work", "enabled": True,
        "data": [{
            "id": "e1", "company": "BS23", "position": "Dev", "location": "Dhaka",
            "start_date": "2026-01", "end_date": None, "current": True,
            "description": "Built things",
        }],
    }])
    fields = {f.key: f for f in build_document(cv).sections[0].entries[0].fields}
    assert fields["position"].group == "header"
    assert fields["company"].group == "header"
    assert fields["location"].group == "meta"
    assert fields["date"].group == "meta"
    assert fields["description"].group == "body"


def test_education_fields_carry_row_groups():
    cv = _cv([{
        "id": "s1", "type": "education", "title": "Ed", "enabled": True,
        "data": [{
            "id": "e1", "degree": "BSc", "institution": "U", "start_date": "2020-01",
            "end_date": "2024-01", "gpa": "3.9", "summary": "Studied",
        }],
    }])
    fields = {f.key: f for f in build_document(cv).sections[0].entries[0].fields}
    assert fields["degree"].group == "header"
    assert fields["institution"].group == "header"
    assert fields["date"].group == "meta"
    assert fields["gpa"].group == "body"
    assert fields["summary"].group == "body"


def test_skills_fields_carry_row_groups():
    cv = _cv([{
        "id": "s1", "type": "skills", "title": "Skills", "enabled": True,
        "data": [{"id": "g1", "category": "Lang", "items": ["Python", "SQL"]}],
    }])
    fields = {f.key: f for f in build_document(cv).sections[0].entries[0].fields}
    assert fields["category"].group == "header"
    assert fields["tag.0"].group == "body"
    assert fields["tag.1"].group == "body"


def test_projects_fields_carry_row_groups():
    cv = _cv([{
        "id": "s1", "type": "projects", "title": "P", "enabled": True,
        "data": [{
            "id": "e1", "name": "Aergia", "url": "https://aergia.dev", "link_text": "site",
            "start_date": "2026-01", "end_date": None, "description": "CV builder",
            "tech_stack": ["Python", "React"],
        }],
    }])
    fields = {f.key: f for f in build_document(cv).sections[0].entries[0].fields}
    assert fields["name"].group == "header"
    assert fields["link"].group == "header"
    assert fields["date"].group == "meta"
    assert fields["description"].group == "body"
    assert fields["tech.0"].group == "body"
    assert fields["tech.1"].group == "body"


def test_languages_fields_carry_row_groups():
    cv = _cv([{
        "id": "s1", "type": "languages", "title": "L", "enabled": True,
        "data": [{"id": "e1", "language": "English", "proficiency": "Native"}],
    }])
    fields = {f.key: f for f in build_document(cv).sections[0].entries[0].fields}
    assert fields["language"].group == "header"
    assert fields["proficiency"].group == "header"


def test_certifications_fields_carry_row_groups():
    cv = _cv([{
        "id": "s1", "type": "certifications", "title": "C", "enabled": True,
        "data": [{"id": "e1", "name": "AWS", "issuer": "Amazon", "date": "2026-01", "credential_url": "https://x"}],
    }])
    fields = {f.key: f for f in build_document(cv).sections[0].entries[0].fields}
    assert fields["name"].group == "header"
    assert fields["meta"].group == "header"
    assert fields["link"].group == "body"


def test_research_fields_carry_row_groups():
    cv = _cv([{
        "id": "s1", "type": "research", "title": "R", "enabled": True,
        "data": [{
            "id": "e1", "title": "Paper", "paper_url": "https://x", "paper_link_text": "pdf",
            "description": "Work", "publication_date": "2026-09", "publication_value": "Conf",
        }],
    }])
    fields = {f.key: f for f in build_document(cv).sections[0].entries[0].fields}
    assert fields["title"].group == "header"
    assert fields["link"].group == "header"
    assert fields["date"].group == "meta"
    assert fields["description"].group == "body"
```

- [ ] **Step 2: Run — verify they fail**

```bash
cd api && .venv/bin/pytest -q tests/test_builders.py -k "carry_row_groups"
```

Expected: FAIL — `AttributeError: 'FieldBlock' object has no attribute 'group'`.

- [ ] **Step 3: Implement — add `group=` to each append per file**

Pattern (every field in these builders uses `fields.append(FieldBlock(key=..., runs=...))`; add `group=` with the value from the row model):

`experience.py`:
```python
fields.append(FieldBlock(key="position", group="header", runs=[TextRun(text=str(row["position"]))]))
fields.append(FieldBlock(key="company", group="header", runs=[TextRun(text=str(row["company"]))]))
fields.append(FieldBlock(key="location", group="meta", runs=[TextRun(text=str(row["location"]))]))
fields.append(FieldBlock(key="date", group="meta", runs=[TextRun(text=date)]))
fields.append(FieldBlock(key="description", group="body", runs=[TextRun(text=str(row["description"]))]))
```

`education.py`:
```python
fields.append(FieldBlock(key="degree", group="header", runs=[TextRun(text=str(row["degree"]))]))
fields.append(FieldBlock(key="institution", group="header", runs=[TextRun(text=str(row["institution"]))]))
fields.append(FieldBlock(key="date", group="meta", runs=[TextRun(text=date)]))
fields.append(FieldBlock(key="gpa", group="body", runs=[TextRun(text=str(row["gpa"]))]))
fields.append(FieldBlock(key="summary", group="body", runs=[TextRun(text=str(row["summary"]))]))
```

`skills.py`:
```python
fields.append(FieldBlock(key="category", group="header", runs=[TextRun(text=str(row["category"]))]))
fields.append(FieldBlock(key=f"tag.{i}", group="body", runs=[TextRun(text=str(item))]))
```

`projects.py`:
```python
fields.append(FieldBlock(key="name", group="header", runs=[TextRun(text=str(row["name"]))]))
fields.append(FieldBlock(key="link", group="header", runs=[TextRun(text=link_text)]))
fields.append(FieldBlock(key="date", group="meta", runs=[TextRun(text=date)]))
fields.append(FieldBlock(key="description", group="body", runs=[TextRun(text=str(row["description"]))]))
fields.append(FieldBlock(key=f"tech.{i}", group="body", runs=[TextRun(text=str(t))]))
```

`languages.py`:
```python
fields.append(FieldBlock(key="language", group="header", runs=[TextRun(text=str(row["language"]))]))
fields.append(FieldBlock(key="proficiency", group="header", runs=[TextRun(text=str(row["proficiency"]))]))
```

`certifications.py`:
```python
fields.append(FieldBlock(key="name", group="header", runs=[TextRun(text=str(row["name"]))]))
fields.append(FieldBlock(key="meta", group="header", runs=[TextRun(text=" · ".join(meta_parts))]))
fields.append(FieldBlock(key="link", group="body", runs=[TextRun(text=url)]))
```

`research.py`:
```python
fields.append(FieldBlock(key="title", group="header", runs=[TextRun(text=str(row["title"]))]))
fields.append(FieldBlock(key="link", group="header", runs=[TextRun(text=link_text)]))
fields.append(FieldBlock(key="date", group="meta", runs=[TextRun(text=formatted)]))
fields.append(FieldBlock(key="description", group="body", runs=[TextRun(text=str(row["description"]))]))
```

- [ ] **Step 4: Run — verify they pass**

```bash
cd api && .venv/bin/pytest -q tests/test_builders.py
```

Expected: ALL pass (the seven new tests + existing builder tests).

- [ ] **Step 5: Commit**

```bash
git add api/app/services/renderer/builders/ api/tests/test_builders.py
git commit -m "Field rows / Step 3: all builders emit per-type field groups"
```

---

## Task 4: HTML renderer — row grouping and social icons

**Files:**
- Modify: `api/app/services/renderer/html.py` (`_render_field_block` ~line 132, `_render_entry` ~line 133, stylesheet ~lines 250-260)
- Test: `api/tests/test_html_renderer.py`

- [ ] **Step 1: Write the failing renderer tests**

Append to `api/tests/test_html_renderer.py` (reuse its existing `_model()` / `render` helpers; see `test_html_renderer.py:25-40` for the fixture pattern):

```python
def test_same_group_fields_render_in_one_row():
    """Fields sharing a group render inside a single .field-row div."""
    manifest = TemplateManifest(
        name="M", zones=[Zone(id="main", styles={})], placement={"profile": "main"},
    )
    doc = Document(sections=[
        Section(id="p", type="profile", title="Profile", entries=[Entry(id="e", fields=[
            FieldBlock(key="name", group="main", runs=[TextRun(text="Ada")]),
            FieldBlock(key="email", group="contact", runs=[TextRun(text="a@b.com")]),
            FieldBlock(key="phone", group="contact", runs=[TextRun(text="123")]),
            FieldBlock(key="summary", group="summary", runs=[TextRun(text="Pioneer")]),
        ])]),
    ])
    model = resolve(doc, HTMLDocumentRenderer(), manifest, Customizations())
    html = HTMLDocumentRenderer().render(model)

    rows = re.findall(r'<div class="field-row"[^>]*>.*?</div>', html, re.S)
    assert len(rows) == 3  # main, contact, summary
    contact_row = next(r for r in rows if "a@b.com" in r)
    assert "123" in contact_row
    assert "Ada" not in contact_row  # name is in its own row


def test_social_field_renders_icon_when_known():
    manifest = TemplateManifest(
        name="M", zones=[Zone(id="main", styles={})], placement={"profile": "main"},
    )
    doc = Document(sections=[
        Section(id="p", type="profile", title="Profile", entries=[Entry(id="e", fields=[
            FieldBlock(key="social_links.0", group="social", icon="x",
                       runs=[TextRun(text="X")]),
        ])]),
    ])
    model = resolve(doc, HTMLDocumentRenderer(), manifest, Customizations())
    html = HTMLDocumentRenderer().render(model)

    assert '<span class="f-icon"' in html
    assert "<svg" in html
    assert "X" in html


def test_social_field_with_unknown_icon_renders_text_only():
    manifest = TemplateManifest(
        name="M", zones=[Zone(id="main", styles={})], placement={"profile": "main"},
    )
    doc = Document(sections=[
        Section(id="p", type="profile", title="Profile", entries=[Entry(id="e", fields=[
            FieldBlock(key="social_links.0", group="social", icon="mastodon",
                       runs=[TextRun(text="Fedi")]),
        ])]),
    ])
    model = resolve(doc, HTMLDocumentRenderer(), manifest, Customizations())
    html = HTMLDocumentRenderer().render(model)

    assert "<svg" not in html
    assert "Fedi" in html
```

- [ ] **Step 2: Run — verify they fail**

```bash
cd api && .venv/bin/pytest -q tests/test_html_renderer.py -k "same_group or social_field"
```

Expected: FAIL — no `.field-row` in the output; no `<svg>`.

- [ ] **Step 3: Implement the renderer**

**3a. Icon table** — add near the top of `html.py` (after `_FONT_SIZE_TO_CSS`):

```python
# Social icon table: name -> inline SVG markup (16x16, currentColor).
# Generic glyphs are hand-drawn; brand marks (github) copy the lucide path
# (https://lucide.dev/icon/github, ISC license) at implementation time.
_SOCIAL_ICONS: dict[str, str] = {
    "x": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 4l16 16M20 4L4 20"/></svg>',
    "twitter": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 4l16 16M20 4L4 20"/></svg>',
    "instagram": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3.5" y="3.5" width="17" height="17" rx="4.5"/><circle cx="12" cy="12" r="3.8"/><circle cx="17.2" cy="6.8" r="1.15" fill="currentColor" stroke="none"/></svg>',
    "linkedin": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3.5" y="3.5" width="17" height="17" rx="2"/><path d="M8.2 10v6.5M8.2 6.9v.2M11.8 16.5v-4.4a2.6 2.6 0 0 1 5.2 0v4.4"/></svg>',
    "facebook": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13.4 21v-6.8h2.3l.45-2.9H13.4V9.4c0-.85.3-1.6 1.7-1.6h1.15V5.1c-.55-.08-1.6-.2-2.55-.2-2.55 0-4.2 1.55-4.2 4.4v2.05H7.2v2.9h2.3V21"/></svg>',
    "youtube": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="6.2" width="18" height="11.6" rx="3.2"/><path d="M10.1 9.6l4.6 2.4-4.6 2.4z" fill="currentColor" stroke="none"/></svg>',
    "github": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"/><path d="M9 18c-4.51 2-5-2-7-2"/></svg>',
    "globe": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M3.6 9h16.8M3.6 15h16.8M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"/></svg>',
    "mail": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25H4.5a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5H4.5a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75"/></svg>',
    "phone": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 0 0 2.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 0 1-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 0 0-1.091-.852H4.5A2.25 2.25 0 0 0 2.25 4.5v2.25Z"/></svg>',
    "link": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244"/></svg>',
}
```

**3b. Field block rendering** — change `_render_field_block` (html.py:132):

```python
def _render_field_block(block: FieldBlock) -> str:
    inner = "".join(_render_text_run(r) for r in block.runs)
    icon_svg = _SOCIAL_ICONS.get(block.icon) if block.icon else None
    if icon_svg:
        icon_html = f'<span class="f-icon" aria-hidden="true">{icon_svg}</span>'
        inner = f'{icon_html}<span class="f-icon-label">{inner}</span>'
    return f'<div class="f-{attr(block.key)}">{inner}</div>'
```

**3c. Entry rendering** — replace `_render_entry` (html.py:133-138):

```python
def _render_entry(entry: Entry, section_subsection: SubsectionStyle | None) -> str:
    gap = (section_subsection.spacing_after if section_subsection else None) or "var(--spacing-subsection, 16px)"

    # Group consecutive fields that share a group name into one row.
    rows: list[str] = []
    current_group: str | None = None
    bucket: list[FieldBlock] = []
    for field in entry.fields:
        if field.group != current_group and bucket:
            rows.append(_render_field_row(bucket))
            bucket = []
        current_group = field.group
        bucket.append(field)
    if bucket:
        rows.append(_render_field_row(bucket))

    fields_html = "".join(rows)
    return f'<div class="entry" style="display:flex;flex-direction:column;gap:{gap};">{fields_html}</div>'


def _render_field_row(fields: list[FieldBlock]) -> str:
    inner = "".join(_render_field_block(f) for f in fields)
    return f'<div class="field-row" style="display:flex;flex-wrap:wrap;align-items:baseline;column-gap:1rem;row-gap:0.25rem;">{inner}</div>'
```

**3d. Stylesheet** — in `_render_document`'s `<style>` block (after the `.f-position, .f-degree` rule, html.py:~255):

```css
    .f-icon { display:inline-flex; width:0.9em; height:0.9em; margin-right:0.3em; vertical-align:-0.125em; }
    .f-icon svg { width:100%; height:100%; }
    .field-row { display:flex; flex-wrap:wrap; align-items:baseline; column-gap:1rem; row-gap:0.25rem; }
```

Note: the `field-row` div carries the same flex rules inline; the CSS class is the hook for future template styling. Add the class rules only if the inline style approach feels redundant — inline styles are authoritative, the class is a styling hook.

- [ ] **Step 4: Run — verify they pass**

```bash
cd api && .venv/bin/pytest -q tests/test_html_renderer.py
```

Expected: ALL pass (the three new tests + existing renderer tests). Then the full backend suite:

```bash
cd api && rm -f data/aergia.test.db && .venv/bin/pytest -q && .venv/bin/ruff check .
```

Expected: all pass, Ruff clean.

- [ ] **Step 5: Visual smoke — the user's CV shape**

Start an isolated backend (temp DB, port 8766), create a CV with the Riasat-Mahbub shape (profile with `social_links: [{label: "Twitter", icon: "x"}, {label: "insta", icon: "instagram"}]`, plus experience/education/skills/projects/languages/certifications/research), GET the preview, and assert:

```bash
curl -s http://127.0.0.1:8766/api/v1/cvs/<id>/preview -H "Authorization: Bearer $TOK" | grep -c 'class="field-row"'
# expect >= 1
curl -s http://127.0.0.1:8766/api/v1/cvs/<id>/preview -H "Authorization: Bearer $TOK" | grep -c '<svg'
# expect >= 1
```

And confirm the profile order in the rendered HTML: `f-name` … `f-title` … contact fields … `f-social_links.0` … `f-summary`.

- [ ] **Step 6: Commit**

```bash
git add api/app/services/renderer/html.py api/tests/test_html_renderer.py
git commit -m "Field rows / Step 4: HTML renderer groups fields into rows and renders social icons"
```

---

## Task 5: Tracker records (project-tracker)

**Files:**
- Create: `tracker/features/FEAT-<ULID>-field-row-layouts-with-social-icons.md`
- Create: `tracker/tasks/TASK-<ULID>-field-row-schema-and-builder-groups.md`
- Create: `tracker/tasks/TASK-<ULID>-renderer-row-grouping-and-social-icons.md`
- Create: `tracker/tasks/TASK-<ULID>-field-row-verification.md`
- Modify: `AGENTS.md`, `tracker/README.md` (counts, after rebuild)

- [ ] **Step 1: Create the feature entry**

```bash
cd /home/riasat/Projects/aergia
tracker new feature "Field-row layouts with social icons" --priority Medium --effort M --description "Restore sophisticated field layouts in the HTML-first renderer (Option A): FieldBlock gains group + icon; builders emit per-type row groups (profile: main/subtitle/contact/social/summary; others: header/meta/body); the renderer wraps same-group fields in .field-row and draws social icons from a renderer icon table. Fixes the flat back-to-back field rendering and missing social icons."
```

Then edit the created file's frontmatter: add `RELATIONS.related: [EPIC-01KZCCC3MTXDGPY31H06NFYP1Q]` and `AFFECTS.files: [api/app/schema/models.py, api/app/services/renderer/builders/*.py, api/app/services/renderer/html.py, web/src/generated/schema.ts, api/tests/test_builders.py, api/tests/test_html_renderer.py]`. Use the generated ULID everywhere below (placeholders `FEAT-01KZJ0FIELDROWS` in this plan are replaced by the real IDs `tracker new` assigns).

- [ ] **Step 2: Create the task entries**

```bash
tracker new task "FieldBlock group/icon schema + builders emit groups" --status DONE --note "Task 1-3: schema + all eight builders emit per-type field groups; profile social links carry icons." 
tracker new task "HTML renderer row grouping + social icons" --status DONE --note "Task 4: .field-row grouping and _SOCIAL_ICONS table in html.py."
tracker new task "Field-row verification (pytest, smoke, manual render)" --status DONE --note "Task 6: full suite + dev.sh --smoke + user-CV-shape render check."
```

Each task file: add `RELATIONS.part_of: [<feature ULID>]` and scoped `AFFECTS.files`.

- [ ] **Step 3: Close the feature with evidence**

```bash
tracker close FEAT-<feature-ULID> --resolution "Shipped: FieldBlock.group/.icon across schema + codegen; all builders emit per-type row groups; renderer wraps same-group fields in .field-row and renders social icons; verified by builder/renderer tests, full suite, and ./dev.sh --smoke."
```

- [ ] **Step 4: Rebuild and validate**

```bash
cd /home/riasat/Projects/aergia && tracker rebuild && tracker validate && tracker stats
```

Expected: 0 errors; the new feature/tasks count in `stats`. Refresh the counts + date lines in `AGENTS.md` and `tracker/README.md` from `tracker stats` (never hand-calculate).

- [ ] **Step 5: Commit**

```bash
git add tracker/ AGENTS.md tracker/README.md
git commit -m "tracker: field-row layout feature and task records"
```

---

## Task 6: End-to-end verification

- [ ] **Step 1: Full gates**

```bash
cd api && rm -f data/aergia.test.db && .venv/bin/pytest -q && .venv/bin/ruff check . && .venv/bin/python scripts/codegen_schema.py --check
cd web && npm run test -- --run && npm run build
cd /home/riasat/Projects/aergia && ./dev.sh --smoke
```

Expected: backend all pass + Ruff clean + codegen clean; frontend all pass + build clean; `SMOKE OK: modern/classic/minimal preview + PDF + built SPA`, exit 0.

- [ ] **Step 2: Confirm the row structure in a real render**

With a CV carrying a profile with social links, `GET /api/v1/cvs/{id}/preview` must contain:
- exactly one `.field-row` per group (main, subtitle, contact, social, summary),
- `<svg>` for known icons (`x`, `instagram`, …) inside `.f-icon` spans,
- `f-summary` AFTER `f-social_links.*` in document order,
- the same HTML in the exported PDF (identical render path).

- [ ] **Step 3: No commit needed unless a gate fails** — if a gate fails, fix at source (TDD), re-run, and amend/extend the relevant task's commit.

---

## Risk register

| Risk | Mitigation |
|---|---|
| Row grouping changes the look of skills tags (now flow in one wrapped row). | Deliberate and matches the "rows" ask; `skill_variant` inline/block remains a pre-existing no-op in the HTML renderer (declared FULL but unimplemented) — noted as follow-up, not fixed here. |
| `.field-row` inline styles duplicate the class CSS. | Inline styles are authoritative today (renderer convention); the class is the future template hook. |
| Icon path data for brand marks is approximate. | `github` uses the lucide path (source noted); generic glyphs hand-drawn; unknown names fall back to text — the fallback test locks that. |
| Existing tests assert exact field markup. | `_render_entry` now wraps fields in `.field-row` divs — any test doing exact-string HTML matching may need its assertion updated to search within rows. Grep `tests/test_html_renderer.py` for `entry` markup assertions during Task 4 and update. |
| Codegen drift: FieldBlock change regenerates `schema.ts`. | Task 1 Step 5 regenerates and `--check` verifies; `test_codegen.py` enforces lockstep. |

## Self-review (spec coverage)

- Row structure per section type: Tasks 2-3 (table + per-builder code). ✓
- Social icons with `icon` data: Task 2 (builder reads `link.icon`) + Task 4 (icon table + `.f-icon` markup). ✓
- Order fix (summary after social): builder order in Task 2 — summary appended after social_links. ✓
- Profile rows (name/contact/social/summary): Task 2 + Task 4 tests. ✓
- Per-field styling (`style.text[key]` → run styles) untouched: `apply_field_text_styles` walks `field.key`, unaffected by `group`/`icon`. ✓ (no task changes it)
- Tracker records + git commits: Tasks 5; commits at every task boundary. ✓
- PDF parity: same HTML render path; Task 6 verifies. ✓

---

## Revision 2 — alignment concept (accepted 2026-08-09)

Extends Option A. Adds one attribute and three renderer rules; no new model.

**1. Schema.** `FieldBlock` gains `align: Literal["right"] | None = None` (right-rail only; left/center come from the section's `text_align`).

**2. Revised group + align table** (replaces the Task 3 table):

| Section | Row 1 (left) | rail (`align="right"`) | Row 2 | Row 3 | Row 4 |
|---|---|---|---|---|---|
| experience | position | date | company | description | — |
| education | degree | date | institution | gpa | summary |
| projects | name | date | link | description, tech | — |
| research | title | date | link | description | — |
| certifications | name | — | meta | link | — |
| skills | category + tags (ONE row) | — | — | — | — |
| languages | language | proficiency | — | — | — |
| profile | name / subtitle / contact / social / summary (unchanged, centered) | — | — | — | — |

**3. Renderer rules** (`_render_field_row` / `_render_entry`):
- A row containing a field with `align="right"`: the first right-aligned field gets `margin-left:auto` (rail). Rail wins over section `text_align`.
- A row with no rail: `justify-content` mirrors `subsection.text_align` (center → center, right → right, else flex-start). This fixes the centering regression.
- `_render_entry` receives `section.subsection` (already does) and passes the resolved justify value down.

**4. Manual alignment gating (panel).** The per-section `text_align` select in CustomizePanel ("Block style (subsection)" disclosure) is rendered ONLY for `profile`, `skills`, `certifications`. All other sections use the default (left + date rail). Existing stored `text_align` on rail sections still renders (renderer emits it), but the rail's `margin-left:auto` wins — no conflict.

**5. Verification:** builder tests assert the new group/align assignments; renderer tests assert `margin-left:auto` on rail fields, centered rows for centered sections, skills single-row; panel test asserts the text_align select visibility per section type; full gates + `./dev.sh --smoke`.
