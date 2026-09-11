---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M29C3WCXWJQZTBQBGDAHY778
TYPE: feature
STATUS: IN_PROGRESS
PRIORITY: High
SEVERITY: null
EFFORT: XL
OWNER: null
CONFIDENCE: Medium
TAGS:
- tailoring
- draft
- customization
- protocol
RELATIONS:
  supersedes:
  - FEAT-01M29BGP4579KM0SJF6PCMH94G
  depends_on:
  - ADR-01M29BGP0TN064SDB93RKRW7ST
  related:
  - FEAT-01M2179Z63ZGQ1VDV23BC5ZF2S
  - FEAT-01M28VJCQQ59N33SZ9M45Q6XMZ
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
  - api/alembic/versions/k6l7m8n9o0p1_move_section_overrides_into_instances.py
  - api/tests/test_tailoring.py
  - api/tests/test_tailoring_contracts.py
  - api/tests/test_section_style_migration.py
  - web/src/generated/schema.ts
  - tailoring-skill/skills/aergia-tailor/SKILL.md
  - tailoring-skill/skills/aergia-tailor/scripts/
  - tailoring-skill/skills/aergia-tailor/references/
  - tailoring-skill/tests/
  - web/src/features/tailoring/
  - web/src/features/applications/components/detail/GeneratedCvPanel.tsx
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-11T23:16:18.973250+00:00'
UPDATED_AT: '2026-09-11T23:16:18.973250+00:00'
---

# Generate and review complete tailored CV drafts

## Background

Replace patch-based local-agent tailoring with whole-document generation into a reviewable unlinked CV draft; expose and accept complete canonical styling and layout customization data.

## Investigation

The protocol grew from targeted field patches into a whole-candidate operation,
but still carries the original patch operations, citation requirements,
heuristic fact blockers, provenance, and model self-scoring. Successful
submission creates a new CV and changes the application's linked CV in the
same transaction, so the user sees the model's result only after it has
already become active. The document model also stored section-level overrides
in both ``SectionInstance.style`` and ``Customizations.per_section``.

## Decision

Replace the patch protocol with v2 complete-candidate generation and
review-before-acceptance. The previous CV is optional context only. The model
returns a full document and a complete canonical ``Customizations`` object;
the server does not merge hidden styling defaults from the previous CV.
Expose template manifests, current customizations, and resolved styles so the
model can understand the starting appearance. Let it change section content,
structure, template, document layout, and all section-specific styles.

The server injects protected profile identity and blocks malformed, unsafe,
unrenderable, or resource-excessive candidates. New claims and inferences may
be shown as advisory review notes, but evidence references and heuristic
fact-check results do not gate generation. Candidate relevance is computed
deterministically for the application; there is no required model-generated
relevance score.

Create a normal unlinked CV draft attached to the tailoring session. The
application stays linked to its previous CV until the user reviews and accepts
the draft. Acceptance uses a compare-and-swap against the source CV link;
rejection soft-deletes the draft and releases its CV quota. The scoped agent
cannot accept, reject, or change application linkage.

Document-level customizations own global appearance and layout. Section-local
``SectionInstance.style`` owns section-specific values. Migrate
``Customizations.per_section`` into the matching section's ``style`` and
remove that duplicate persistence path.

## Implementation

Deliver in coherent commits: (1) ADR and v2 contracts, (2) canonical
customization ownership and data migration, (3) session state/database and
backend generation/draft lifecycle, (4) v2 skill and preview loop, (5)
application review/acceptance UI, and (6) remove v1 patch machinery and finish
the cutover. The protocol change is atomic at the release boundary; no
long-term dual-version API remains.

Step 2 is implemented: ``Customizations.per_section`` is removed from the
canonical schema and generated TypeScript; a data migration moves old values
to matching section styles, preserving the old override precedence; renderer
overlay code is removed. Pure schema/renderer/migration test functions passed
directly and Ruff/codegen checks pass. Async API integration tests are not
available in the current Python 3.14 environment because test DB initialization
hangs; rerun on the supported Python 3.12 runtime.

## Verification

Acceptance requires a no-source-CV session, full-candidate styling/layout
changes, template selection, profile identity injection, preview/persisted
render parity, repeatable preview and single draft creation, no application
link change before acceptance, acceptance conflict handling, reject cleanup
and quota release, and absence of protocol-v1 write operations. Test both the
Alembic migration of section styles and existing database/session safety.

## Follow-up

Run the full async API integration and smoke gates on the supported Python
3.12 runtime; the current Python 3.14/aiosqlite environment hangs during
database initialization.
