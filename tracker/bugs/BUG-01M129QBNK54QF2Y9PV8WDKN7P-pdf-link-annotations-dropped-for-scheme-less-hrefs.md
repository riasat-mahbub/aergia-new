---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M129QBNK54QF2Y9PV8WDKN7P
TYPE: bug
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-09T21:47:12.176520+00:00'
UPDATED_AT: '2026-08-09T21:47:12.176520+00:00'
---

# PDF link annotations dropped for scheme-less hrefs

## Background

Symptom: exported PDF showed link text + arrow but no clickable links (0 /Subtype /Link annotations). Root cause: Chromium print silently drops <a href> annotations without a scheme; user CV stored scheme-less values (github.com, asdgasdg, paper) that bypassed the frontend urlSchema. normalize_url_scheme existed in builders/_utils.py for this exact quirk but was dead code. Fix: projects/research/certifications builders normalize the URL before emitting the anchor. Verified: re-exported the exact CV -> /Subtype /Link + /URI present for all links. Tests: test_builders.py normalization cases.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from BUG-01KZM7WZXG19G1NHKDT2C71WHM during the schema-4 cutover. -->
