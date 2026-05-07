---
SCHEMA: 3
FORMAT: project-tracker
ID: TASK-01KYZ1XGBV9JW9CK98079H4B6J
TYPE: task
STATUS: DONE
SUMMARY: '5 OSV-scanner findings fixed by upgrading vite, vitest, esbuild'
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- security
- deps
RELATIONS: null
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:18:34.491822+00:00'
UPDATED_AT: '2026-08-01T16:18:34.491822+00:00'
---

# NPM vulnerabilities in vite/vitest/esbuild

## Background

5 OSV-scanner findings fixed by upgrading vite, vitest, esbuild

Five npm vulnerabilities were detected by osv-scanner:
- `esbuild@0.21.5` — GHSA-67mh-4wv8-2f99
- `vite@5.4.21` — CVE-2026-39365 (GHSA-4w7w-66w2-5vf9)
- `vite@5.4.21` — CVE-2026-53571 (GHSA-fx2h-pf6j-xcff)
- `vite@5.4.21` — CVE-2026-53632 (GHSA-v6wh-96g9-6wx3)
- `vitest@2.1.9` — CVE-2026-47429 (GHSA-5xrq-8626-4rwp)

*Migrated from SCHEMA 2 entry 005-npm-vulnerabilities.md (status CLOSED) on 2026-08-01.*

## Investigation


## Decision


## Implementation

Upgraded to vite 6.4.3, esbuild 0.28.1, vitest latest. All 5 findings
resolved. `npm audit` reports 0 vulnerabilities.

## Verification


## Follow-up
