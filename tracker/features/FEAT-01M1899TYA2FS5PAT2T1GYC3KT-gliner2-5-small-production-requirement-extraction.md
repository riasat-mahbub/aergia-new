---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M1899TYA2FS5PAT2T1GYC3KT
TYPE: feature
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: L
OWNER: null
CONFIDENCE: Medium
TAGS:
- gliner2
- requirements
- extraction
RELATIONS:
  depends_on:
  - TASK-01M182ASVXYVVW5BGP5MZAGH0H
AFFECTS:
  files:
  - api/app/services/requirement_extractor.py
  - api/app/services/relevance.py
  - api/app/schemas/application.py
  - api/app/services/application.py
  - api/app/services/cv.py
  - api/app/routes/applications.py
  - api/app/routes/cvs.py
  - api/app/config.py
  - api/app/models/application.py
  - api/pyproject.toml
  - api/Dockerfile
  - api/tests/conftest.py
  - api/tests/test_requirement_extractor.py
  - api/tests/integration/test_gliner2_model.py
  - api/scripts/gliner2_evaluate.py
  - api/scripts/gliner2_jobs.json
  - dev.sh
  - web/src/lib/api/applications.ts
  - web/src/components/applications/RelevanceDrawer.tsx
  - docs/plans/2026-08-29-gliner2.5-production.md
  - README.md
  - DEPLOY.md
LINKS:
  plan: docs/plans/2026-08-29-gliner2.5-production.md
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-30T02:52:12.106721+00:00'
UPDATED_AT: '2026-08-30T02:52:12.106721+00:00'
---

# GLiNER2.5-small production requirement extraction

## Background

Replace production requirement extraction with pinned GLiNER2.5-small plus deterministic enrichment while preserving downstream relevance matching, Library selection, CV generation, and SQLite persistence.

## Investigation

The application flow already had a canonical `JobRequirement` contract and
deterministic relevance/Library selection path. The integration therefore
keeps the old fields for compatibility while adding source spans, concepts,
tri-state importance, structured constraints, confidence, and extractor
metadata. The former `requirement-v2` parser remains an explicit test and
comparison helper only; production extraction is GLiNER2.5-small and does not
silently fall back.

The pinned CPU image was benchmarked with `fastino/gliner2.5-small-v1` at
revision `cab1bddfd30fda7b803a4691c41f90378a2d517a`. In an 8GB/2-vCPU
container, cold loading took about 6.2 seconds, warm short postings took
2.7–3.6 seconds, load peak RSS was about 1.13GB, and a 4,160-word native
long-document case took about 91.7 seconds with a 1.64GB peak RSS.

## Decision

Ship GLiNER2.5-small as the sole production requirement extractor. Keep
deterministic logic authoritative for explicit years, degree/certification,
required/preferred, negation, and work-eligibility signals. Use an 8GB RAM,
2+ vCPU host as the preferred deployment target; approximately 3GB/1 vCPU is
only a constrained serialized lower bound. Do not add embeddings or redesign
downstream relevance in this change.

## Implementation

Added lazy process-local `AutoExtractor` loading, a serialized inference lock,
native long-document extraction with source-aware normalization and a manual
sentence/section chunk fallback, normalization/deduplication, boilerplate
exclusions, deterministic enrichment, and a compatibility adapter into the
existing matcher. Model failures surface a stable API extraction error.

The production Docker image installs CPU-only PyTorch, pins the model revision,
preloads the artifact at build time, and retains lazy runtime initialization.
The frontend change is additive and only displays unknown/required/preferred
importance correctly. No Library JSON, rendering, CV generation behavior, or
database migration was introduced.

## Verification

The mocked boundary and legacy relevance contracts pass `25 passed, 1 skipped`
without loading the real model. The final production image builds successfully
and the representative four-case evaluation reports 16/19 matched
requirements, 0.889 precision, 0.842 recall, 100% importance/constraint
accuracy, and zero false required qualifications. The long-document case
completed through the native long path.

The frontend production build passes. Repository-wide frontend lint remains
blocked by 77 pre-existing `no-explicit-any` errors. The normal DB-backed pytest
integration run was not usable in this environment because the existing
Python/aiosqlite setup hangs while opening the test database; model-free tests
and the real container evaluation were used instead.

## Follow-up

Run `scripts/gliner2_evaluate.py` with manually annotated real job postings
before changing thresholds or adding fallback/shadow infrastructure. Revisit
long-posting latency and event-loop offloading if production traffic shows a
need for asynchronous inference scheduling.
