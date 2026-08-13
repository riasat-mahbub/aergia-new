---
SCHEMA: 3
FORMAT: project-tracker
ID: FEAT-01KZY50AER3VD0ZMJDG9FT4J08
TYPE: feature
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: M
OWNER: riasat
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - FEAT-01KZY2QN02VNF4XK7H5SQFB2KD
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-13T18:08:59.864532+00:00'
UPDATED_AT: '2026-08-13T18:08:59.864532+00:00'
---

# FEAT-01KZY2QN02VNF4XK7H5SQFB2KD

## Background

Follow-up 3 (commit 3aa99f4, 2026-08-13): Profile polish — three visual fixes from comparing against /home/riasat/Downloads/CV.pdf. (1) Pipe | separator between contact fields via CSS ::before pseudo-elements on adjacent siblings. (2) Smaller social labels (split out of the contact rule into their own 0.83rem rule). (3) Smaller social icons (0.9em -> 0.75em, margin-right 0.3em -> 0.25em). All CSS-only, apply to all three seed templates. Profile builder: all social links now share key='social' (was 'social_links.{i}') so the CSS class is valid and the rule applies. doc: docs/profile-vs-golden.md documents the side-by-side comparison and the remaining name-size regression (f-name: 1.5rem ships 18pt; golden is 15pt). Out of scope for this commit; flagged as a known issue.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
