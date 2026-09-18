---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M2V3PDFDFAB9510E6ECGVF0N
TYPE: bug
STATUS: DONE
PRIORITY: Medium
SEVERITY: Medium
EFFORT: XS
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS: null
AFFECTS:
  files:
  - web/src/features/home/HomePage.css
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-18T20:35:28.877084+00:00'
UPDATED_AT: '2026-09-18T20:35:28.877084+00:00'
---

# Homepage color alternation after simplification

## Background

The simplified homepage removed the section index and premise, but retained the old dark-background sequence. Restore alternating section surfaces and readable contrast for the system map.

## Investigation

Removing the section index and premise left the dark page root directly
adjacent to the system map and authoring section. The map had no explicit
surface of its own, so it inherited the same dark background as the hero and
the following feature zone. Its diagram styles also still used dark-surface
contrast values, which would have been incorrect on a light band.

## Decision

Make the system map the first light band after the dark hero. Keep the
existing authoring, Library, applications, trust, tour, and final palette
roles so the simplified page has a clear dark/light rhythm without restoring
removed content.

## Implementation

Applied an explicit light background to the system map, switched its diagram
nodes, labels, arrows, and borders to light-surface contrast values, and kept
the existing dark/light feature section sequence intact.

## Verification

Frontend lint and typecheck passed; architecture checks, codegen check, and
production build passed. Lint reports only the repository's existing nine
React hook dependency warnings.

## Follow-up
