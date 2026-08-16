---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M129QBNK54QF2Y9PV8WDKNA7
TYPE: feature
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: M
OWNER: riasat
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - FEAT-01M129QBNK54QF2Y9PV8WDKNA5
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-13T17:33:32.320400+00:00'
UPDATED_AT: '2026-08-13T17:33:32.320400+00:00'
---

# FEAT-01KZY2QN02VNF4XK7H5SQFB2KD

## Background

Follow-up (commit d672b1d, 2026-08-13): The user asked for the per-field gap in the minimal template to be 'almost none'. The SPACING_TOKEN_VALUES['minimal'] second value dropped from 8px to 2px in api/app/services/renderer/tokens.py. The change propagates everywhere via var(--spacing-subsection, 16px) — the two-column left/right column internal gaps AND the stack entry per-field gap both tighten. Section-to-section gap (--spacing-section, 16px) is unchanged. test_resolve.py: test_minimal_spacing_maps_to_legacy_vars now asserts 2px.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from FEAT-01KZY2ZCS0TVSHSSTD6GPJCAHQ during the schema-4 cutover. -->
