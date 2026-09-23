---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M3847XC1RXZKDFNKZB5JBJN1
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
  - FEAT-01M3846H9KJFPJPT30CYM6QY5Q
AFFECTS: null
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-23T21:55:09.825569+00:00'
UPDATED_AT: '2026-09-23T21:55:09.825569+00:00'
---

# FEAT-01M3846H9KJFPJPT30CYM6QY5Q

## Background

Added the frozen 29-job corpus, pinned Small/Base full-corpus outputs, two provisional seed oracles, a reproducible GLiNER runner/scorer, six-form Convverge invariance inputs/results, and a deterministic NuExtract Convverge diagnostic. Small and Base each match all 38 provisional seed source units; Base adds no discovery gain and is 2.3x slower on this CPU. Merged/split source forms change both models output counts from 22 to 13/39, identifying source-unit segmentation sensitivity shared by both models. NuExtract returned three headings and zero valid Convverge requirements. NuNER/PP-UIE remain unrun due Python 3.14 dependency/runtime incompatibilities. Production is unchanged; the task remains in progress pending independent gold review and supported model runs.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
