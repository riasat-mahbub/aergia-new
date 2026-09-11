---
SCHEMA: 4
FORMAT: project-tracker
ID: ADR-01M29BGP0TN064SDB93RKRW7ST
TYPE: adr
STATUS: PROPOSED
PRIORITY: High
SEVERITY: null
EFFORT: L
OWNER: null
CONFIDENCE: Medium
TAGS:
- tailoring
- architecture
- protocol
RELATIONS:
  related:
  - FEAT-01M29BGP4579KM0SJF6PCMH94G
  - FEAT-01M21CKCN8SKGD0XV0MG3HQZGB
AFFECTS:
  files:
  - api/app/http_schemas/tailoring.py
  - api/app/models/tailoring_session.py
  - api/app/services/tailoring.py
  - api/app/services/tailoring_facts.py
  - api/app/services/tailoring_policy.py
  - api/app/document_schema/models.py
  - api/app/document_schema/capabilities.py
  - api/app/services/renderer/resolution/sections.py
  - api/app/services/renderer/resolution/context.py
  - api/app/routes/tailoring.py
  - api/alembic/versions/
  - api/tests/test_tailoring.py
  - api/tests/test_tailoring_contracts.py
  - tailoring-skill/skills/aergia-tailor/SKILL.md
  - tailoring-skill/skills/aergia-tailor/scripts/
  - tailoring-skill/skills/aergia-tailor/references/
  - web/src/features/tailoring/
  - web/src/features/applications/components/detail/GeneratedCvPanel.tsx
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-11T23:05:49.850208+00:00'
UPDATED_AT: '2026-09-11T23:05:49.850208+00:00'
---

# Replace tailoring patches with complete generated CV drafts

## Background

Record the decision to replace the patch-oriented LLM tailoring protocol with complete candidate generation, first-class editable customization state, preview, and user acceptance.

## Investigation

The current protocol already accepts a complete ``replace_candidate`` value,
but wraps it in a patch contract and requires pooled evidence references,
fact checks, operation provenance, and an AI relevance self-assessment. It
creates and immediately links the result instead of leaving the existing
application CV in place for review. Section styles and document customizations
are mutable, but ``SectionInstance.style`` and
``Customizations.per_section`` overlap and the candidate schema treats
customizations as an untyped dictionary.

## Decision

Use whole-document generation as the only tailoring write protocol. The
existing CV is an optional read-only source; a session can also start without
one. The agent returns a complete CV candidate with canonical document
customizations, section-local styles, template, and layout. The server applies
only mechanical schema, ownership, size, URL, template, and renderer checks,
then saves an unlinked draft. The authenticated user accepts or rejects that
draft in the application UI.

Customization ownership is singular: document-wide fonts, accent, spacing,
alignment, flags, zones, and instance placement live in
``Customizations``; section-local typography, subsection/layout hints, policy,
and field text styles live in ``SectionInstance.style``. Remove
``Customizations.per_section`` after migrating its values into matching
section styles, with its current higher precedence winning conflicts.

The server owns protected profile identity and injects it into the candidate.
The model may freely compose or omit other content, research linked public
material, make reasonable technical inferences, select a supported template,
and modify all supported customization data. Heuristic fact checks are
advisory review warnings; only mechanical integrity and security constraints
block draft creation. No evidence citations, operation reasons, provenance,
gap report, or AI relevance self-score are required.

The external capability can create and preview a draft but cannot accept it.
Only the authenticated application owner may accept or reject. Acceptance
compare-and-swaps the application's current CV link so a stale review cannot
replace a CV selected after the session began.

## Implementation

Implementation is tracked by ``FEAT-01M29BGP4579KM0SJF6PCMH94G``. The
cutover removes protocol-v1 patch routes and helper contracts as part of the
v2 rollout; v1 sessions are expired during migration.

## Verification

The feature's completion entry records test and migration results.

## Follow-up

If claim warnings prove useful in review, improve semantic discovery and
confidence presentation without turning those warnings into submission gates.
