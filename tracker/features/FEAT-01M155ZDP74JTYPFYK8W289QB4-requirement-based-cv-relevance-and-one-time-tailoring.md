---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M155ZDP74JTYPFYK8W289QB4
TYPE: feature
STATUS: PLANNED
PRIORITY: High
SEVERITY: null
EFFORT: XL
OWNER: riasat
CONFIDENCE: Medium
TAGS:
- applications
- relevance
- tailoring
- library
RELATIONS:
  depends_on:
  - FEAT-01M153EFMSAFDAYC8A1ZS3FSJ0
  related:
  - FEAT-01M0ZV14S8SD5NVG5G2MH37CMQ
AFFECTS:
  files:
  - docs/plans/2026-08-28-requirement-based-cv-relevance-and-one-time-tailoring.md
  - api/pyproject.toml
  - api/app/models/application.py
  - api/app/models/library.py
  - api/app/schemas/application.py
  - api/app/services/application.py
  - api/app/services/cv.py
  - api/app/services/library.py
  - api/app/services/relevance.py
  - api/app/routes/applications.py
  - api/app/routes/cvs.py
  - api/alembic/versions/
  - api/tests/test_applications.py
  - api/tests/test_applications_generation.py
  - api/tests/test_library.py
  - api/tests/test_relevance.py
  - api/tests/test_smoke_live.py
  - web/src/lib/api/applications.ts
  - web/src/lib/store/applicationStore.ts
  - web/src/components/applications/RelevanceDrawer.tsx
  - web/src/components/applications/applicationPresentation.ts
  - web/src/pages/ApplicationDetailPage.tsx
  - web/src/pages/ApplicationsPage.tsx
  - web/src/pages/BuilderPage.tsx
  - web/src/pages/__tests__/
LINKS:
  plan: local://2026-08-28-requirement-based-cv-relevance-and-one-time-tailoring.md
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-28T21:56:21.831208+00:00'
UPDATED_AT: '2026-08-28T21:56:21.831208+00:00'
---

# Requirement-based CV relevance and one-time tailoring

## Background

Replace keyword-frequency relevance with deterministic JD requirement extraction, explainable weighted requirement coverage, Library-based content ranking, and one-time materialized tailored CV generation. Relevance may be recomputed after job or Builder edits without regenerating or rewriting the generated CV.

## Investigation

The current `keyword-v1` implementation extracts arbitrary n-grams, weights
keyword frequency, selects Library rows using per-kind relative thresholds,
and stores copied payloads in generated CVs. The application already has the
right orchestration boundary in `ApplicationService`, and the HTML-first
renderer can continue consuming ordinary materialized CV sections.

The Library is a generation-time source, not a live CV reference system. A
generated CV must remain a standalone editable snapshot. Existing and
manually edited CVs must continue to be scoreable even when their content is
not present in the Library.

## Decision

Replace keyword-frequency scoring with `requirement-v1`: deterministic JD
requirement extraction, taxonomy/alias and constraint matching, FTS5/BM25
retrieval for free text, bounded RapidFuzz fallback, weighted requirement
coverage, and greedy marginal-coverage selection of Library content.

Generation remains one-and-done. It uses the current job, profile, and
Library to create a materialized editable CV, records selected-source
provenance, and never automatically regenerates or rewrites that CV. After
generation, application/job edits and Builder saves may recompute relevance
against the current CV, but Library changes affect only future generation.

The new result is requirement-centric and explainable: each requirement has
required/preferred state, type, weight, match method, strongest evidence, and
coverage status. Existing `keyword-v1` rows remain readable and are migrated
or recomputed explicitly rather than silently changing historical scores.

## Implementation

Deliver in independently verifiable steps:

1. Define requirement/result contracts, score semantics, freshness behavior,
   algorithm versioning, and compatibility handling.
2. Add bounded deterministic parsing for headings/bullets, required/preferred
   language, taxonomy concepts and aliases, years-of-experience, and degree
   constraints.
3. Flatten Library rows/bullets into SQLite FTS5 documents and use exact,
   alias, constraint, BM25, and bounded fuzzy matching in that order.
4. Implement strongest-evidence matching, weighted requirement coverage, and
   greedy content selection with deterministic tie-breaking and existing
   page-fit safeguards.
5. Integrate one-time generation, provenance, post-generation score
   recomputation, and explicit handling of applications without a generated
   CV.
6. Replace the relevance drawer's keyword view with requirement-level
   evidence and update application/Builder save flows.
7. Add migrations, index rebuild/backfill, legacy-result compatibility,
   adversarial fixtures, lifecycle tests, full smoke coverage, and a small
   benchmark corpus.

For every implementation step, make the focused code commit first, then run
`tracker update FEAT-01M155ZDP74JTYPFYK8W289QB4 --status IN_PROGRESS --note
"..."`, run `tracker rebuild && tracker validate`, and commit the tracker
entry separately with a `tracker:` prefix. Do not squash implementation and
tracker commits. Preserve unrelated dirty-worktree changes.

## Verification

The focused gate covers parser and negation cases, aliases and technical
formatting, quantitative and degree constraints, FTS ranking, fuzzy-match
thresholds, duplicate-coverage suppression, required/preferred scoring,
strongest-evidence output, deterministic greedy selection, one-time
generation, post-generation Builder recomputation, job edits without CV
rewrites, Library edits without existing-CV rewrites, legacy result handling,
and old `keyword-v1` data.

The full gate is `pytest`, Ruff, frontend Vitest, ESLint, production build,
`npm run codegen:check`, and `./dev.sh --smoke` when Chromium prerequisites
are available. The benchmark corpus must record expected requirements,
coverage, evidence, and selected content for representative jobs.

## Follow-up

After rollout, evaluate false positives/negatives from the benchmark corpus
before considering semantic models. A future “generate new tailored version”
action is explicitly outside this feature; it must create a new CV/version
instead of mutating the one-and-done generated snapshot.
