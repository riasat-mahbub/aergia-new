---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M14K1E63VC3EZ971AYEQETS5
TYPE: feature
STATUS: PLANNED
PRIORITY: High
SEVERITY: null
EFFORT: XL
OWNER: null
CONFIDENCE: Medium
TAGS:
- ui
- design-system
- dashboard
- applications
- settings
- security
RELATIONS:
  depends_on:
  - FEAT-01M12QBNXW4AZ2YNM3YEAMEEJS
  - FEAT-01M0X607K4MWVGGCVZWWMSKJHE
  - FEAT-01M13ASSHCVZAM08G77R8VM8J3
AFFECTS:
  files:
  - web/src/styles/tokens.css
  - web/src/styles/tokens.ts
  - web/src/index.css
  - web/index.html
  - web/src/main.tsx
  - web/src/components/common/AppLayout.tsx
  - web/src/pages/CvListPage.tsx
  - web/src/pages/ApplicationsPage.tsx
  - web/src/pages/ApplicationDetailPage.tsx
  - web/src/components/cv-list/CvCard.tsx
  - web/src/components/cv-list/ImportCvButton.tsx
  - web/src/components/builder/LLMKeyDialog.tsx
  - web/src/pages/SettingsPage.tsx
  - web/src/lib/store/authStore.ts
  - api/app/routes/auth.py
  - api/app/schemas/auth.py
  - api/app/services/auth.py
  - api/tests/test_auth.py
  - api/tests/unit/test_schemas.py
LINKS:
  plan: local://2026-08-28-aergia-ui-consistency-and-workspace-redesign.md
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-28T16:25:24.931768+00:00'
UPDATED_AT: '2026-08-28T16:25:24.931768+00:00'
---

# Application UI design system and workspace redesign

## Background

Unify the application palette around emerald/off-white tokens, add favicon support, redesign the dashboard around CVs/library/applications, move application-generated CV ownership into the Applications experience, redesign application cards, consolidate account and LLM settings, and remove the current-password change flow as requested.

## Investigation

The UI currently combines three styling strategies: proof-sheet tokens with a
blue accent, Library-only emerald tokens, and hard-coded Tailwind gray/blue
classes across shared screens. The dashboard also combines CVs, a Library
summary, and generated application CVs, while the Applications page owns the
actual application records and generation lifecycle. Account Settings and the
LLM import-key dialog are exposed by separate settings icons. The current
password field is transient reauthentication rather than stored plaintext, but
the requested removal requires removing the entire password-change flow unless
a password-reset system is introduced.

## Decision

Use a single emerald/off-white application chrome palette with semantic roles:
primary `#059669`, secondary/info `#41658A`, soft accent `#DAFFEF`, canvas
`#FCFFFD`, and ink `#2F4550`. Keep error/warning colors semantic and keep
user-selected CV document accents separate from application chrome. Make the
dashboard an overview, give Applications ownership of application-generated
CV actions, consolidate LLM key management under Settings, and remove the
password-change feature rather than weakening reauthentication.

## Implementation

See `docs/plans/2026-08-28-aergia-ui-consistency-and-workspace-redesign.md`.
The plan is executed as six implementation steps plus a final verification
step. Each step ends with focused tests, an implementation commit, an
append-only tracker update, `tracker rebuild && tracker validate`, and a
separate tracker commit. Commits remain regular commits and are not squashed.

## Verification

Pending implementation.

## Follow-up

Add a password-reset/recovery flow before restoring any password-change UI.
Replace the favicon asset later without changing the application layout.
