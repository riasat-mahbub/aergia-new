---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M8AYCJG9Z3K4CF44B1GF4G5S
TYPE: task
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: High
TAGS:
- frontend
- tailoring
- providers
RELATIONS:
  depends_on:
  - TASK-01M8AYCJG9TJQVK0JN6RKAYA44
  related:
  - BUG-01M8AY219X52RZ6X8E18XEXFEQ
  - TASK-01M8AY219XV55JCZZ8B84QANVK
AFFECTS:
  files:
  - web/scripts/test-tailoring-providers.mjs
  - web/scripts/test-tailoring-review.mjs
  - web/src/features/tailoring/api/providers.ts
  - web/src/features/tailoring/hooks/useTailoringProviders.ts
  - web/src/features/tailoring/components/TailoringProviderSettings.tsx
  - web/src/features/applications/pages/ApplicationDetailPage.tsx
  - web/src/features/applications/components/detail/ApplicationCvPanel.tsx
LINKS: null
VERIFIED_BY: codex
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-11-26T03:29:03.497697+00:00'
UPDATED_AT: '2026-11-26T03:51:32.984783+00:00'
---

# Gate optional tailoring provider setup by availability

## Background

Implementation plan for [BUG-01M8AY219X52RZ6X8E18XEXFEQ](../bugs/BUG-01M8AY219X52RZ6X8E18XEXFEQ-optional-tailoring-provider-setup-leads-to-dead-end.md).

## Investigation

The provider status endpoint is absent in the audited deployment. The hook handles every failure as retryable, the application details repeat the error for both providers, and Settings offers the Gemini download before capability is known. The Settings OAuth callback also runs independently of the status lookup.

## Decision

Use the authenticated provider status request to distinguish an unsupported deployment, a transient load failure, and a supported deployment with per-provider statuses. Keep the existing coding-agent action available under its current session rules. Enable external setup only after its backend contract and provider workflow have been verified.

## Implementation

1. In `providers.ts`, use the request-level error reporting option from the tailoring toast plan. Classify an endpoint 404 as unsupported for this lookup. Let the local provider UI own other lookup errors so each failure produces one actionable message. Keep ordinary authentication refresh behavior.
2. In `useTailoringProviders.ts`, expose a status that distinguishes loading, unsupported, failed, and loaded. Clear old availability when a refresh starts and preserve the generation guard against late responses. Supply the same states to Settings and application details.
3. On an unsupported deployment, omit optional provider buttons and setup links from the application. In Settings, show a short deployment availability message without Retry, connection controls, or the skill download. For a transient failure, show one status and Retry on the affected surface. Keep provider actions out of the pending and failed states.
4. For a successful response, use each provider's declared status. Enable runs only for ready accounts and only when the current session rules allow it. Offer connection or reconnect for supported accounts that need it. Show Gemini setup instructions and download only when the supported backend offers that setup. Keep unavailable accounts free of dead actions.
5. Keep the existing OAuth query cleanup. Submit a captured callback only after support is known, once per callback. If support is absent, surface one local message and discard the captured values. Keep callback values in memory and leave them out of logs and error text.

## Verification

Chromium passed the real unsupported route, transient status retry in Settings and application detail, a real coding-agent session start, per-provider synthetic states, and single OAuth callback delivery after retry. The existing review harness covers provider-origin draft recovery with setup unavailable. Provider transport remains subject to independent production enablement verification.

`node web/scripts/test-tailoring-providers.mjs` passed on WSL Chromium, including callback deduplication under React StrictMode and Gemini setup gating.

- Through the production gateway, return 404 for the status path. Both pages should render without provider action links or a global error toast. The local agent can still start a session.
- With an intercepted 503 followed by a valid 200, verify one retryable message, no duplicate toast, and the correct controls after Retry. Verify a late response cannot restore obsolete availability.
- Mount the disconnected, setup-required, reconnect, unavailable, and ready states. Verify buttons, the skill link when offered, and a blocked new run while a session is active.
- Test OAuth callback cleanup and single submission with a supported backend response using fictional inputs. Before production enablement, verify connect, callback, disconnect, download where offered, start, and draft review against the actual integration. Use the [Canadian Gemini pilot](../../docs/plans/2026-11-25-gmail-monitor-private-doc-pilot.md) before enabling Gemini.
