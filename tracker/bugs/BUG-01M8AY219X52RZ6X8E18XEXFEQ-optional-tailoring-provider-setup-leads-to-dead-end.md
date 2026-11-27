---
SCHEMA: 4
FORMAT: project-tracker
ID: BUG-01M8AY219X52RZ6X8E18XEXFEQ
TYPE: bug
STATUS: DONE
PRIORITY: High
SEVERITY: Medium
EFFORT: M
OWNER: null
CONFIDENCE: High
TAGS:
- frontend
- tailoring
- providers
RELATIONS: null
AFFECTS:
  files:
  - web/src/features/tailoring/api/providers.ts
  - web/src/features/tailoring/hooks/useTailoringProviders.ts
  - web/src/features/tailoring/components/TailoringProviderSettings.tsx
  - web/src/features/applications/components/detail/ApplicationCvPanel.tsx
  - api/app/routes/tailoring.py
  - docs/plans/2026-11-25-gmail-monitor-private-doc-pilot.md
LINKS: null
VERIFIED_BY: codex
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-11-26T03:23:18.205452+00:00'
UPDATED_AT: '2026-11-26T03:51:32.984783+00:00'
---

# Optional tailoring provider setup leads to a dead end

## Background

The application detail offers ChatGPT and Gemini tailoring and directs users to provider settings when availability cannot be loaded. The Settings panel offers Retry and a Gemini skill download.

## Investigation

1. Sign in to a production build from commit `78f71d2` and open any application.
2. Follow **Open provider settings** under either provider.
3. In **Optional AI providers**, select **Retry**, then try **Download the Aergia skill**.

**Actual.** Provider status and the skill download return HTTP 404. Retry leaves the same error message and there is no working setup path. The frontend references the provider endpoints, while the backend tailoring router has no matching provider routes in this revision.

**Expected.** Setup is actionable when supported. If providers are unavailable on this deployment, the application gives one clear availability state and only offers actions it can complete.

## Verification

Chromium verified the unsupported deployment through the same-origin gateway, a real coding-agent session start, and one local retry on both status surfaces. Simulated account states and OAuth responses verified the provider controls. The mounted review harness verified an existing Gemini draft remains reviewable with provider entry points unavailable.

Reproduced in Chromium through TanStack Start and FastAPI with a disposable account. Observed HTTP 404 for both `GET /api/v1/tailoring/providers` and `GET /api/v1/tailoring/providers/skill.zip`.
