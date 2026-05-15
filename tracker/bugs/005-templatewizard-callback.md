---
ID:             005
TYPE:           bug
NAME:           TemplateWizard onComplete not firing
SUMMARY:        Wizard callback was not invoked after completing the final step
STATUS:         CLOSED
TAGS:           template-wizard, callback, phase-5
LINKS:          fix-commit=8106396
---

## Description

The `onComplete` callback on the TemplateWizard component was not being
invoked after the user completed the final review step. This prevented
the parent component from saving the template data.

## Resolution

Fixed the callback wiring in the TemplateWizard component to properly
invoke `onComplete` when the wizard reaches the end state.

### Commit
`8106396` — fix: TemplateWizard onComplete callback, fix ZoneLayoutBar row height bar removal
