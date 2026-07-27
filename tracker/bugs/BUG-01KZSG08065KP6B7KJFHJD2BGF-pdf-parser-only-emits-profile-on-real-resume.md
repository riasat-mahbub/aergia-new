---
SCHEMA: 3
FORMAT: project-tracker
ID: BUG-01KZSG08065KP6B7KJFHJD2BGF
TYPE: bug
STATUS: PROPOSED
PRIORITY: High
SEVERITY: High
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- parser
- regex
- fix
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-11T22:44:59.526731+00:00'
UPDATED_AT: '2026-08-11T22:44:59.526731+00:00'
---

# pdf-parser-only-emits-profile-on-real-resume

## Background

Uploading a real-world CV (Riasat Mahbub's resume, ~/Downloads/Resume.pdf) to /api/v1/cvs/import/pdf returns a ParseResult with only the profile section. Experience, Education, Projects, Research, and Skills are silently dropped. Root cause: _infer_font in extract.py flags a line as bold only when line == line.upper(); real-world resumes use mixed-case headers and Chromium-generated PDFs embed Type0 subset fonts whose BaseFont names never match the size-hint regex. The page-median threshold (10 * 1.15 = 11.5) is then never met because _extract_font_dict returns {} for Type0 subsets. _detect_sections returns [] and the mapper falls back to a single profile entry from the page-1 pre-section fallback. Tracked here; fixed by TASK-01KZS8Y4... (six tasks, commit plan in docs/plans/2026-08-11-pdf-parser-resilience.md).

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
