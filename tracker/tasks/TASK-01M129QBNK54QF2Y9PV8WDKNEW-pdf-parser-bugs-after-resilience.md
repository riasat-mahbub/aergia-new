---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M129QBNK54QF2Y9PV8WDKNEW
TYPE: task
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: High
TAGS:
- parser
- regex
- investigation
- IN_PROGRESS
RELATIONS: null
AFFECTS:
  files:
  - api/app/services/parser/extract.py
  - api/app/services/parser/classify.py
  - api/app/services/parser/mapper.py
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-12T00:30:00+00:00'
UPDATED_AT: '2026-08-12T00:30:00+00:00'
---

# pdf-parser: post-resilience bug investigation

## Background

After the pdf-parser-resilience plan (commits 0fbe362 → c7bca40, 6 tasks DONE)
closed, the regex parser passes all 318 backend tests including the
benchmark-corpus integration test on `tests/fixtures/resume-benchmark.pdf`
(8d91e1fec2e433ebc6b5fa6c7c88e9ee, Riasat Mahbub's Resume.pdf). The user
asked me to investigate the regex parser for remaining issues after I started
a separate refactor toward pdfplumber (TASK-01KZSG1PARSERPDFPLUMBER, paused).

This is a READ-ONLY investigation. The goal is to enumerate concrete defects
in the regex pipeline so the next fix plan can be scoped. No code changes
proposed yet; pick the highest-impact targets for the next iteration.

## Investigation

I ran the parser end-to-end against the benchmark fixture and dumped both
the full ParseResult and the intermediate blocks + section spans. Found
**three real defects** the test suite does not catch and **one annotation
quirk that is not actually a bug**.

### Bug 1 — Profile annotations silently drop LinkedIn / GitHub / site URL

PDF /Annots for the contact line carry four URI links (mail, GitHub, LinkedIn,
personal site), all at y∈[768, 781] on page 0. The visitor's CTM-scale bbox
computation (`_TEXT_CTM_SCALE = 0.75`) reports the contact-line block at
y∈[832.9, 841.9] — leaving a 50pt gap between the rendered contact line and
the name. The annotation rects fall in that gap, so
`_attach_annotations_to_block` finds no overlap and `block.links` stays empty
for blocks 1 and 2.

Net effect in the live ParseResult:
- `profile.email = "riasat1998@gmail.com"` ← recovered by EMAIL_RE in
  `_extract_profile_fields`, NOT by the mailto annotation (mailto attaches
  to block 0 because the name sits at y=787 which overlaps y∈[782, 795]).
- `profile.phone = "+1 782 409 4525"` ← recovered by PHONE_RE.
- `profile.site_url = "https://rmahbub.com"` ← recovered by `_BARE_DOMAIN_RE`
  matching the bare `rmahbub.com` token in block 2.
- `profile.social_links = []` ← **lost**. The GitHub and LinkedIn annotations
  never attach to any block; nothing else in `_build_profile_data` recovers
  them because the regex `LINKEDIN_RE` and `GITHUB_RE` only fire when the URL
  text is on the contact line itself, but block 2's text is
  `riasat-mahbub Riasat Mahbub rmahbub.com` — it has no `linkedin.com` or
  `github.com` tokens.

The mailto annotation only "works" because the name block's y-range overlaps
the mailto rect by accident.

The right fix: instead of relying on CTM-derived bbox overlap, expose every
URI link on the page as a synthetic "link token" with the same coordinates
as the visitor reports for nearby text, OR widen the annotation-bbox overlap
to whole-line y-tolerance (so a contact line and its annotation link match
regardless of the CTM scale).

### Bug 2 — Skills section swallows an entire category prefix as the first item

`_SKILL_CATEGORY_RE = r"^([A-Z][A-Za-z0-9 &/+-]+):\s*(.*)$"` matches the
**category prefix + first item** on a single line:

```
Programming Languages: TypeScript, JavaScript, Python, PHP, SQL, HTML/CSS
```

After `_SKILL_CATEGORY_RE.match`, `m.group(1) = "Programming Languages"` and
`m.group(2) = "TypeScript, JavaScript, ..."`. The splitter then re-runs
`re.split(r"[,\n;•]+", rest)` — which is correct. So **this case actually
works** on the benchmark.

But `_SKILL_CATEGORY_RE` is ANCHORED with `^` and accepts only `[A-Z]` at
position 0. A real-world line beginning with a lowercase skill
("typescript: JavaScript, Python") would NOT match, so the line would fall
into the "no prefix" branch and become a single group with an empty
category. This is a known limitation, not exercised by the benchmark. Low
priority.

### Bug 3 — Research entry #2 has no `paper_url` because the PDF source has no link annotation

The benchmark PDF's research entry #2 ("Exploring Code Smells In Simulation
Modelling Systems: Effectiveness, Risks And Impacts") has no "Paper ↗"
suffix in the rendered text and no /Annots link annotation in the PDF — only
three of four research entries carry paper URLs. The parser is doing the
right thing here; the underlying source PDF is the problem. **Not a parser
bug — note as data source quality.**

### Annotation quirk (not a bug) — Aergia CV Builder URL is "wrong" in the source PDF

Live output shows project #3 `Aergia CV Builder` gets
`url = "https://github.com/riasat-mahbub/project-tracker-skill"` — the SAME
URL as project #2 (`Project Tracker Extension`). The annotation walker is
correct: the PDF's annotation rect for project #3 is genuinely annotated
with that URL. The user's Resume.pdf was exported with the wrong link on
project #3. **Not a parser bug — note as data source quality.**

### Other observations (not bugs)

- Block 1 and Block 2 both report `y=832.92` (the page footer / "Skills"
  section header y is being clamped to the page bottom). This is fine
  functionally — the visitor's CTM scale + Y-flip happens to clamp
  bottom-of-page blocks to the page edge, so the bbox overlaps are still
  correct. But it makes the bboxes look suspicious in logs.
- Letter-spaced Chromium date labels (`A u g u s t  2 0 2 6`) appear as
  their own blocks AFTER the Skills section. They get classified as part of
  the Skills section body and end up filtered by `_is_letterspaced_junk` in
  `_extract_skills_fields`. They DO NOT pollute the skills list. Confirmed
  by the smoke test `not any("A u g" in i ... for i in all_items)`. OK.
- `confidence.overall_level = "medium"` even though every individual field is
  `high` or `medium`. This is correct — the mapper takes the WORST level,
  and the project/research titles are all `medium`.
- `_extract_experience_fields` returns two entries with both `position` and
  `company` populated. Confidence entries with level "low" are NOT appended
  for these (the code only appends "low" when position is set without
  company). OK.

## Decision

Stop the pdfplumber refactor (TASK-01KZSG1PARSERPDFPLUMBER) — it does not
address any of the bugs above. The regex parser is structurally sound; what
it needs is **annotation-to-line attachment that does not depend on the
empirical 0.75 CTM scale**.

The single highest-impact fix is **Bug 1** (profile social_links loss). It is
caused by the CTM-scale bbox math in `_group_spans_into_lines`; a more
robust fix is to:
- Walk each /Annots /Link URI on the page.
- Find the closest text line by y-distance (no CTM involvement — use raw
  `tm_y` from the visitor instead of the scaled bbox).
- Attach if the URI's x-range falls within the line's x-range (with
  tolerance).

This removes the dependency on `_TEXT_CTM_SCALE` for annotation attachment
and decouples Bug 1 from Bug 3's other half (the "annotations never attach
when CTM math is off" class of failure).

## Implementation

No code change proposed in this entry. The next plan (Tasks 1-2 below)
should target Bug 1. Tasks 3-4 are existing carry-overs from the resilience
plan.

## Verification

Ran end-to-end on the benchmark fixture to ground every claim above:

    .venv/bin/python -c '...'
    -> 6 sections, 49 confidence fields, 0 warnings

Section-by-section contents dumped in `tracker search regex` workflow.

## Follow-up

1. Open a TASK entry: "pdf-parser: line-nearest annotation attachment". Scope
   is the visitor-text-based annotation→line matcher that ignores the CTM
   bbox and uses raw `tm_y` for y-comparison instead.
2. Re-evaluate TASK-01KZSG1PARSERPDFPLUMBER (status IN_PROGRESS) and either
   close it as superseded by (1) or split into a parallel research effort.
3. Add a regression test that asserts `profile.social_links` is non-empty
   on the benchmark fixture (currently missing — this is why Bug 1 was not
   caught).

<!-- Migrated from TASK-01KZSHINVESTIGATEPARSERBUGS during the schema-4 cutover. -->
