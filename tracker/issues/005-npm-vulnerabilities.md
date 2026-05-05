---
ID:             005
TYPE:           issue
NAME:           NPM vulnerabilities in vite/vitest/esbuild
SUMMARY:        5 OSV-scanner findings fixed by upgrading vite, vitest, esbuild
STATUS:         CLOSED
TAGS:           security, deps
LINKS:          fix=code-quality-phase-6
---

## Description

Five npm vulnerabilities were detected by osv-scanner:
- `esbuild@0.21.5` — GHSA-67mh-4wv8-2f99
- `vite@5.4.21` — CVE-2026-39365 (GHSA-4w7w-66w2-5vf9)
- `vite@5.4.21` — CVE-2026-53571 (GHSA-fx2h-pf6j-xcff)
- `vite@5.4.21` — CVE-2026-53632 (GHSA-v6wh-96g9-6wx3)
- `vitest@2.1.9` — CVE-2026-47429 (GHSA-5xrq-8626-4rwp)

## Resolution

Upgraded to vite 6.4.3, esbuild 0.28.1, vitest latest. All 5 findings
resolved. `npm audit` reports 0 vulnerabilities.
