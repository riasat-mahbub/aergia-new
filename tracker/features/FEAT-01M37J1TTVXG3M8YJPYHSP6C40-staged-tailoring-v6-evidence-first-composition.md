---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M37J1TTVXG3M8YJPYHSP6C40
TYPE: feature
STATUS: IN_PROGRESS
PRIORITY: High
SEVERITY: null
EFFORT: L
OWNER: null
CONFIDENCE: Medium
TAGS:
- tailoring
- architecture
RELATIONS: null
AFFECTS:
  files:
  - api/app/http_schemas/tailoring.py
  - api/app/routes/tailoring.py
  - api/app/services/candidate_evidence.py
  - api/app/services/requirement_extractor.py
  - api/app/services/tailoring.py
  - api/tests/test_candidate_evidence.py
  - api/tests/test_requirement_extractor.py
  - api/tests/test_tailoring.py
  - tailoring-skill/skills/aergia-tailor/SKILL.md
  - tailoring-skill/skills/aergia-tailor/references/target-strategy.schema.json
  - tailoring-skill/skills/aergia-tailor/scripts/session.mjs
  - tailoring-skill/tests/session.test.mjs
  - web/src/features/tailoring/api/tailoring.ts
  - web/src/features/tailoring/hooks/useTailoringSession.ts
  - web/src/features/tailoring/types/index.ts
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-23T16:37:16.251239+00:00'
UPDATED_AT: '2026-09-23T16:37:16.251239+00:00'
---

# Staged tailoring v6 evidence-first composition

## Background

Implement the first staged-tailoring milestone while retaining protocol v5: share the GLiNER runtime, build job-blind candidate evidence with internal provenance and a presentation-blind projection, separate candidate-blind strategy and evidence context DTOs, and delay v6 candidate context exposure in the session helper until target strategy is written. Follow-on source recovery, deterministic regression review, page optimization, real-model benchmarking, and v5/v6 comparative quality evaluation remain future work.

## Investigation

Protocol v5 returned job, profile, full Library, previous CV, and scanner data in one response and wrote them into the session workspace immediately. That made a later prose instruction insufficient to keep initial composition blind to prior presentation. Existing GLiNER requirement extraction also owned runtime loading and inference mechanics directly.

## Decision

Introduce protocol v6 as an opt-in staged path while preserving v5. Share a process-local GLiNER runtime; keep requirement normalization job-side and add a separate job-blind evidence extractor. Give v6 distinct strategy and presentation-blind evidence DTOs, and have the portable helper wait for a job-only target strategy before fetching candidate evidence. The first milestone does not expose raw Library or previous-CV content in v6.

## Implementation

Added the shared runtime and candidate evidence extraction with exact internal source spans, content hashes, confidence and extractor versions, nearby concept relations, deterministic structured-field projection, and sorted source-presentation-blind groups. Added v6 context DTOs/routes, kept v5 as the API default, opted the browser into v6, and updated the portable skill/session helper for staged contexts with a v5 compatibility path. V6 requires an empty workspace to prevent stale source or candidate files from entering its early pass. Added tests for split/merged/reordered source prose, provenance, structured fields, context leakage, and v5 compatibility.

## Verification

Focused API suites: 26 passed; Ruff passed; portable skill tests: 3 passed; frontend typecheck passed; `git diff --check` passed. Runtime/extraction behavior is exercised with model doubles because `gliner2` is not installed in the workspace; real-model recall, precision, and the Convverge end-to-end comparison remain unverified.

## Follow-up

Benchmark real GLiNER evidence extraction and source-boundary invariance, then add late Library recovery and deterministic source-to-candidate regression findings. Later milestones should add isolated regression interpretation, bounded scanner correction, page-budget optimization, and representative v5/v6 quality comparison before considering v6 cutover.
