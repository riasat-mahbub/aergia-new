---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M8AYCJG9TJQVK0JN6RKAYA44
TYPE: task
STATUS: DONE
PRIORITY: High
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: High
TAGS:
- frontend
- tailoring
- error-states
RELATIONS:
  related:
  - BUG-01M8AY219XR582DZAG8Y4S8CVH
  - TASK-01M8AY219XV55JCZZ8B84QANVK
AFFECTS:
  files:
  - web/src/shared/api/client.ts
  - web/src/features/tailoring/api/tailoring.ts
  - web/src/features/tailoring/hooks/useTailoringSession.ts
  - web/src/features/builder/hooks/useBuilderApplicationContext.ts
LINKS: null
VERIFIED_BY: codex
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-11-26T03:29:03.497697+00:00'
UPDATED_AT: '2026-11-26T03:51:32.984783+00:00'
---

# Handle expected empty tailoring reads without toasts

## Background

Implementation plan for [BUG-01M8AY219XR582DZAG8Y4S8CVH](../bugs/BUG-01M8AY219XR582DZAG8Y4S8CVH-empty-tailoring-lookups-show-error-toasts.md).

## Investigation

The Axios interceptor sends a global toast before rejecting a failed request. The application silently handles an empty latest-session lookup and the builder falls through to ordinary CV context when its first draft-context lookup returns 404. Both users still see the global error. The same API functions also serve session-conflict recovery and pending-draft refresh, which handle a missing result differently.

## Decision

Use request-scoped notification control. An expected status should still reject with the original Axios error so the owning workflow can interpret it. Keep the default reporting behavior for other requests.

## Implementation

1. In `shared/api/client.ts`, add a typed request option that suppresses error toasts for specified statuses or lets the caller report the error locally. Read it only when deciding whether to call the global error reporter. Leave error rejection and session refresh intact.
2. Add opt-in 404 suppression to the two tailoring API wrappers. Pass it from initial application session hydration and the initial builder draft-context probe only. Keep all other callers on their existing reporting path, including session-conflict recovery and pending-draft refresh.
3. Keep the builder's existing ordinary-CV and linked-application fallback. Preserve route identity and generation checks. A real missing CV continues to be reported by its document fetch. An expired or deleted pending draft continues to use the builder's draft-unavailable path.
4. Keep shared-client test coverage around the interceptor itself. The mounted builder and tailoring harnesses mock the feature API wrappers, so their checks alone cannot establish that the global toast was suppressed.

## Verification

Chromium exercised the real client, response interceptor, and global toast reporter. Initial optional 404s stayed quiet while 403 and 503 errors still showed feedback. Ordinary and linked CVs rendered and a truly missing CV still reported its load error. Mounted session and builder suites passed recovery and route-transition cases.

- With the real browser client, return 404 for latest-session hydration and the first draft-context lookup. Confirm a usable application and ordinary CV with no error toast. Repeat with a CV linked to an application and verify scanner context still loads.
- On the same routes, return 403 or 503 and verify ordinary error reporting. Verify a missing CV still shows its document-load error and a pending draft removed after load still reaches the appropriate recovery state.
- Confirm a failed auth refresh still takes its existing path. Run the mounted tailoring-session and builder scenarios to cover conflict recovery, draft refresh, and navigation during pending reads.
