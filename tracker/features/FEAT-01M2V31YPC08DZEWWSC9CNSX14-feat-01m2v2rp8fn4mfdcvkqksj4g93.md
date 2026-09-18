---
SCHEMA: 4
FORMAT: project-tracker
ID: FEAT-01M2V31YPC08DZEWWSC9CNSX14
TYPE: feature
STATUS: IN_PROGRESS
PRIORITY: High
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - FEAT-01M2V2RP8FN4MFDCVKQKSJ4G93
AFFECTS:
  files:
  - web/src/features/home/HomePage.tsx
  - web/src/features/home/HomePage.css
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-18T20:24:18.380219+00:00'
UPDATED_AT: '2026-09-18T20:24:18.380219+00:00'
---

# FEAT-01M2V2RP8FN4MFDCVKQKSJ4G93

## Background

Replacing the table-like two-column index/process treatment with border-light editorial lists, renumbering the main sections from 01 through 04, and removing redundant 03A–03E process labels.

## Investigation

The two-column rule exposed the section index and application process as
bordered tables. Their small labels also introduced a redundant 03A–03E
numbering layer, while the primary section sequence incorrectly began at 00.

## Decision

Keep the maximum-two-column content rule, but use light editorial separators
instead of cell borders. Reserve numbering for the four primary sections and
start that sequence at 01.

## Implementation

Converted the section index and process strip to border-light lists, changed
the primary labels to 01 / THE SYSTEM through 04 / PURSUE, and removed the
03A–03E process markers while retaining the five process labels.

## Verification

Passed frontend lint (nine pre-existing hook warnings), TypeScript
type-checking, production build, and browser rendering. Desktop and mobile
renders report 01–04 section/index labels, zero process marker elements, no
horizontal overflow, and no console errors.

## Follow-up
