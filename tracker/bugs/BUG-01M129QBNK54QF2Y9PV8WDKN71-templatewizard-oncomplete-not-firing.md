---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M129QBNK54QF2Y9PV8WDKN71
TYPE: bug
STATUS: DONE
SUMMARY: Wizard callback was not invoked after completing the final step
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- template-wizard
- callback
- phase-5
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:09:35.576554+00:00'
UPDATED_AT: '2026-08-01T16:09:35.576554+00:00'
---

# TemplateWizard onComplete not firing

## Background

Wizard callback was not invoked after completing the final step

The `onComplete` callback on the TemplateWizard component was not being
invoked after the user completed the final review step. This prevented
the parent component from saving the template data.

*Migrated from SCHEMA 2 entry 005-templatewizard-callback.md (status CLOSED) on 2026-08-01.*

## Investigation


## Decision


## Implementation

Fixed the callback wiring in the TemplateWizard component to properly
invoke `onComplete` when the wizard reaches the end state.

### Commit
`8106396` — fix: TemplateWizard onComplete callback, fix ZoneLayoutBar row height bar removal

## Verification


## Follow-up

<!-- Migrated from BUG-01KYZ1D22R68NT6BAN8AEY9VPV during the schema-4 cutover. -->
