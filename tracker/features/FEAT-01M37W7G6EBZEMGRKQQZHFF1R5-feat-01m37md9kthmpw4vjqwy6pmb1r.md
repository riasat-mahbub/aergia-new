---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M37W7G6EBZEMGRKQQZHFF1R5
TYPE: feature
STATUS: IN_PROGRESS
PRIORITY: High
SEVERITY: null
EFFORT: L
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - FEAT-01M37MD9KTHMPW4VJQWY6PMB1R
AFFECTS:
  files:
  - api/app/http_schemas/tailoring.py
  - api/app/routes/tailoring.py
  - api/app/services/candidate_evidence.py
  - api/app/services/tailoring.py
  - api/tests/test_candidate_evidence.py
  - api/tests/test_tailoring.py
  - tailoring-skill/skills/aergia-tailor/SKILL.md
  - tailoring-skill/skills/aergia-tailor/scripts/session.mjs
  - tailoring-skill/skills/aergia-tailor/references/candidate-propositions.schema.json
  - tailoring-skill/tests/session.test.mjs
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-23T19:35:07.726544+00:00'
UPDATED_AT: '2026-09-23T19:35:07.726544+00:00'
---

# FEAT-01M37MD9KTHMPW4VJQWY6PMB1R

## Background

Validate an isolated, job-blind proposition extractor against the real Convverge Library, then use only its validated presentation-blind projection for fresh v6 composition. Keep v5 available and defer later recovery, regression review, and page fitting.

## Investigation


## Decision

Isolated LLM proposition extraction works for this evidence sample and is ready to support the next v6 milestone. Keep GLiNER as an optional semantic cue source; no separate LLM fallback is needed because the isolated LLM is now the primary narrative proposition producer. Retain deterministic source/hash/quote/schema/relation validation. Track the single missed end-to-end scope and moderate grouping/relation-array variation in future evaluations; do not hide these limitations with a late recovery pass.


## Implementation

Added versioned v6 proposition submission/source DTOs and deterministic source validation, preserving existing evidence groups, structured facts, provenance, and presentation-blind projection. Added per-source session orchestration with a fresh context-isolated child and a dedicated proposition schema. V5 behavior is unchanged. The output contract limits proposition size, requires explicit support and source excerpts, restricts relation vocabulary, and has deterministic validation resolve exact excerpts to authoritative offsets and hashes before the composer projection is built.


## Verification

Focused API tests: 13 passed. Ruff passed on the changed Python files. Portable skill tests: 3 passed. `git diff --check` passed. Real-model benchmark and six-form invariance audit used the configured GLiNER2.5-small runtime for supporting cues and isolated live Codex subagents for propositions. Both Convverge PDFs were rendered and scanned under the same frozen requirement extraction; both were one page. The initial composer context was inspected for leakage before composition.


## Follow-up

Proceed to late raw-Library source recovery, then deterministic source-to-candidate transitions and isolated regression interpretation. Keep scanner-guided correction bounded, followed later by marginal-value page optimization and a broader v5/v6 benchmark. Revisit relation normalization and the single missed end-to-end scope during that work. Preserve the earlier GLiNER-only failure audit in the superseded tracker entry; it remains the reason GLiNER is cue-only.
## Investigation

Replaced GLiNER-only narrative proposition generation in v6 with one fresh Codex subagent per narrative source (`fork_turns="none"`). Each child receives only one Library source, its structured identity/context, the current GLiNER concept cues, and the extraction contract. No job, strategy, old CV, or scanner state is included. GLiNER remains a secondary cue detector; structured Library values still bypass narrative extraction. The session flow stages and removes source files so the main composer receives only the candidate evidence projection.

The exact 21-entry Convverge snapshot had 11 narrative fields: 2 experience, 4 projects, and 5 research. Manual audit found 46 meaningful explicit propositions. The extractor recovered 45 (97.8% recall); no unsupported proposition was found. Exact source excerpt/offset/hash validation passed for all claims, all relation endpoints resolved, and no cross-entry provenance contamination occurred. The one missed proposition was the Aergia CV Builder scope that implementation was end-to-end; its technology stack was preserved in structured Library facts. The validated evidence contains 45 propositions and 87 local relations across 21 groups, including structured facts. Brain Station propositions recovered web/mobile feature development with Angular/Laravel/Ionic, Agile/Scrum, Linux provisioning, container deployment with Docker/Git/CI/CD, Moodle/WordPress plugin development, Ionic/Moodle HTML parsing, and unit/integration testing across legacy/new codebases with reliability and technical-debt outcomes.

No source text explicitly supports developer/designer collaboration, documentation, Azure, or Microsoft experience. Those were not extracted as candidate facts. GLiNER supplied 64 supporting cues across the sample (37 technologies, 5 artifacts, 4 outcomes, 9 quantitative-scope cues, 1 collaboration cue, and 8 domain cues); cue confidence was not treated as proposition quality.

Six real isolated LLM runs covered original, reordered, merged, finely split, prose, and paraphrased Brain Station forms. Every form preserved the same factual core and tool/action relationships. Claim counts varied from 6 to 8. Related plugin/HTML claims were sometimes combined and sometimes separated; Agile was sometimes standalone and sometimes attached to feature delivery; in one run the relation array was empty although the claim itself retained its tool context. Relation arrays otherwise ranged from 17 to 20. This is semantic fact invariance with moderate granularity/serialization variation, not byte-level determinism.

The fresh composer received the job-only target strategy, a presentation-blind projection (21 groups/45 claims), structured candidate data, template, and renderer capabilities. It did not receive raw Library prose, previous CV, or source scanner results. The accepted v5 result represented Brain Station as four source-like topics: development/Agile, testing, deployment, and plugins/HTML parsing. V6 used three bullets: development with Angular/Laravel/Ionic; testing across legacy/new codebases with reliability/debt outcomes; and Agile/Scrum with container deployment and Docker/Git/CI/CD. It omitted low-value plugin/HTML-parser details, retained Linux in skills, and regrouped delivery evidence. The first three broad themes and their order still overlap with v5, but the bullet count and conceptual grouping changed, and one source topic disappeared. No unsupported Brain Station claims were found in the corrected v6 CV. Across the broader CV, a draft claim that the candidate built research pipelines was corrected to say they used those pipelines; the Library supports the latter only.

V5 and v6 both rendered to one page with the same renderer/template conditions and frozen 22-requirement extraction. Scanner results were: Job Fit 0.5314 → 0.4854; term visibility 0.6313 → 0.5196; PDF Recovery 0.9673 → 0.9877. Three requirement states changed from partial to not evidenced: Microsoft technologies, Microsoft-cloud interest, and specific Azure/MS-product prior experience. These changes remove unsupported/weak source hints rather than lose supported facts. ATS had 1 warning in v5 and none in v6. Resume Quality had three informational action-only findings in v5 and three informational findings plus one warning for the co-authored-paper accomplishment in v6. That warning merits later editorial review; it does not justify inventing an action. Important supported evidence did not regress in the audited transitions.
