---
SCHEMA: 3
FORMAT: project-tracker
ID: BUG-01KZ08THKAY2S6T6W2N3XMYWZX
TYPE: bug
STATUS: IN_PROGRESS
PRIORITY: High
SEVERITY: High
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- firefox
- datepicker
- regression
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-02T03:38:31.914066+00:00'
UPDATED_AT: '2026-08-02T03:38:31.914066+00:00'
---

# firefox-month-input-no-picker

## Background

Symptom: clicking the Start Date / End Date inputs in Firefox does nothing — no picker opens, no focus feedback, no way to set a date. The X-clear button was the regression in the previous step (which assumed a Chrome-style chevron at the right edge); in Firefox the input is a plain text field, so the X overlapped nothing and the picker was never going to work anyway.

Root cause: <input type="month"> only renders a native picker in Chromium/Safari/WebKit. Firefox ignores the type and shows a plain text input. Per MDN, showPicker() is also not supported for type=month in Firefox.

Fix: replace <input type="month"> with two native <select> elements (year + month) so the control works in every browser. The value is still a "YYYY-MM" string so formatDateRange and the rest of the data model are unchanged. Keep the existing visible affordances (calendar icon, clear X) so the visual is consistent with the other UX work.

Acceptance:
- Selecting a year and a month updates the field's YYYY-MM value.
- Clearing the field resets both selects to placeholder.
- The picker is operable in Firefox, Chrome, Safari.
- Existing date renderer tests still pass.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
