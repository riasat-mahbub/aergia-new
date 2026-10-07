---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M4BXMQHJT56A8C43KXTQZZYR
TYPE: feature
STATUS: PLANNED
PRIORITY: High
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS:
- minimal
- templates
- ats
RELATIONS: null
AFFECTS:
  files:
  - docs/plans/2026-10-07-minimal-template-readability.md
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-10-07T19:32:29.362142+00:00'
UPDATED_AT: '2026-10-07T19:32:29.362142+00:00'
---

# Improve Minimal template readability while preserving ATS extraction

## Background

Plan scoped Minimal body typography and independent section/entry/field spacing, inherited inspector hints, and real-PDF verification. Execution assignments use gpt-6-luna with max reasoning. Product implementation has not started.

## Investigation

Reviewed Minimal seed, template schema, resolver and HTML cascade, inspector
inheritance, copied per-CV layouts, PDF regressions, and render freshness.
The audit's Minimal fixtures passed structural extraction but used 9 pt body
text and zero section/entry spacing. A GPT-6 Luna max-reasoning subagent
reviewed the proposed architecture read-only and confirmed its feasibility.

## Decision

Plan optional manifest body typography and independent entry/field gap
defaults, populated only for Minimal. Target 10.5 pt body, 1.4 line height,
16 px section gaps, 8 px entry gaps, and 4 px field gaps. Keep name/heading
hierarchy, explicit overrides, single renderer, existing zones, and sibling
template visuals. Four later Luna max assignments have explicit ownership,
dependency gates, and real-PDF acceptance criteria.

## Implementation

Execution-ready plan created at
docs/plans/2026-10-07-minimal-template-readability.md. No product changes
implemented, deployed, or merged by the planning task.

## Verification

Source feasibility review and delegated architecture review completed.
Implementation verification remains required by the plan: schema/codegen,
override inheritance, actual PDF typography and parsing, scanner freshness,
frontend checks, and release smoke.

## Follow-up

Execute P01 first; coordinator reviews schema/cascade and regenerates types.
P02 and P03 may then run concurrently; P04 reviews integrated evidence.
Complete required gates and tracker updates before any authorized cutover.
