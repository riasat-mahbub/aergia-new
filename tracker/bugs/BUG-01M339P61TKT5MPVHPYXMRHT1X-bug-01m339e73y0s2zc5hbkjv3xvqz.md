---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M339P61TKT5MPVHPYXMRHT1X
TYPE: bug
STATUS: DONE
PRIORITY: High
SEVERITY: High
EFFORT: L
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - BUG-01M339E73Y0S2ZC5HBKJV3XVQZ
AFFECTS: null
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-22T00:54:08.187007+00:00'
UPDATED_AT: '2026-09-22T00:54:08.187007+00:00'
---

# BUG-01M339E73Y0S2ZC5HBKJV3XVQZ

## Background

Audit and harden scanner PDF text recovery, structural order, headings,
entries, contacts, links, severity, Unicode tokenization, render freshness,
and persisted-result remediation. Public PDF analysis and score versions
remain unchanged.

## Investigation

Focused tests confirmed H1–H18 as implementation issues or partially
confirmed design issues. The previous analyzer compared generic persisted CV
flattening with PDF text, used a word-order scan that stopped at missing
tokens, followed persisted rather than resolved renderer order, expected the
hidden Profile heading, omitted project/institution entry fallbacks, treated
0/0 contacts as pass, used non-occurrence-aware heading/entry matching,
compared unnormalised links, discovered arbitrary URL-shaped metadata,
allowed any failed check to veto the document, applied one threshold to
different check types, omitted PDF/render inputs from cheap freshness, and
used ASCII-centric tokenisation. The old AlayaCare 15% order result was a
combination of source/storage order, non-rendered social metadata, and the
early-termination word matcher; it was not a faithful measure of the rendered
document's structural order. In the AlayaCare CV, persisted flattening put
the summary before social labels while the resolved renderer placed social
labels before the summary, and flattening added internal `linkedin`/`github`
tokens that were not visible. The greedy matcher eventually reached the
missing social token and stopped at 52, producing the 15% result.

Chromium smoke passes in the approved runtime. The ordinary pytest run has
one environment-only Playwright driver failure; the same test passes in the
Chromium-capable runtime.


## Decision

Use the canonical renderer's resolved model as the PDF recovery expectation
source. Keep semantic Job Fit, lexical matching, tailoring, and the public
`aergia-pdf-recovery-v2` / `pdf-recovery-score-v1` versions unchanged.
Structural checks expose actionable expected/recovered/missing/affected
items. Critical text/order/contact failures can fail the analysis; headings,
entries, partial contact recovery, and link annotation loss produce warnings.
Force-rescan current
application results rather than patching stored numbers.


## Implementation

`pdf_recovery.py` now derives visible text, effective headings, entry anchors,
contact fields, link runs, and ordered structural anchors from the resolved
renderer model. It formats dates and honors hidden/disabled section policy,
uses project-name and education-institution fallbacks, canonicalizes hrefs,
matches duplicate occurrences one-for-one, compares structural anchors with
an LIS-based order check, and uses Unicode-aware technical-token matching.
Freshness fingerprints include render inputs and optional PDF bytes;
application routes, backfill, and audit pass the current template manifest.
The result contract carries expected/recovered/missing/affected items. A
forced backfill replaced all 28 current scanner results without touching
legacy relevance or tailoring snapshots.


## Verification

Focused PDF/scanner suites: 75 passed. Full API suite: 654 passed, 1
skipped, 1 failure in the unprivileged environment (`test_smoke_render`;
Playwright driver connection closed); the isolated test passes in the
approved Chromium runtime. Ruff passes. Frontend typecheck, architecture
fixtures/checks, codegen check, and lint complete; lint retains 9 existing
hook-dependency warnings and no errors. Chromium/PDF smoke: all four stages
pass. Forced backfill: 28 scanned, 0 failed, 0 unscannable. Final audit:
28 current, 0 stale, 0 missing; PDF pass=17, warning=11, fail=0.

AlayaCare before/after PDF recovery:

| Check | Before | After | Explanation |
| --- | --- | --- | --- |
| Text retention | 334/346 (96.5%) | 361/361 (100%) | rendered visible text replaces raw persisted traversal |
| Reading order | 52/346 (15.0%, fail) | 10/10 anchors (pass) | resolved renderer order + missing-token-safe structural comparison |
| Contacts | 2/2 | 2/2 | unchanged |
| Headings | 4/5 (warning) | 4/4 (pass) | hidden Profile title excluded |
| Entries | 4/4 | 6/6 | project anchors and renderer-defined labels included |
| Links | 4/5 | 4/5 (warning) | canonical rendered link expectations; one annotation remains absent |
| Overall | fail | warning | only non-critical link annotation loss remains |

Job Fit remained 51.25%, classification 87.5%, evidence-evaluable 100%, and
lexical visibility 30.77%; semantic branches were not changed.


## Follow-up

Investigate the remaining 11 warning PDFs (especially link annotation and
layout-order details) as a separate calibration task. Keep legacy relevance
and tailoring migration unchanged until their scheduled cutover. The
unprivileged full-suite Playwright failure is environmental, not a scanner
regression.
