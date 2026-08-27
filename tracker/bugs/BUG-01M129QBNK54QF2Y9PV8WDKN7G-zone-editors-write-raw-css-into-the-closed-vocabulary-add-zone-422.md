---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M129QBNK54QF2Y9PV8WDKN7G
TYPE: bug
STATUS: PROPOSED
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
CREATED_AT: '2026-08-09T17:34:46.051261+00:00'
UPDATED_AT: '2026-08-09T17:34:46.051261+00:00'
---

# Zone editors write raw CSS into the closed vocabulary (Add Zone 422)

## Background

ZoneCreationModal and ZoneStyleEditor emitted legacy raw CSS (width: '30%', padding: '24px', background-color, font, color) which the closed ZoneStyle (width/background/padding tokens, extra=forbid) rejects. Latent while the backend dropped customizations.layout; surfaced as 'layout.zones.N.styles.padding Input should be none/tight/comfortable/loose' once layout became a real field. Fix: both editors quantize to width/padding tokens and write background under the canonical key; drop font/text-color controls not in the vocabulary.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up

<!-- Migrated from BUG-01KZKSERS3ERMGG3YQJBDTYA3Y during the schema-4 cutover. -->
