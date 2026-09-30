# Tailoring protocol v10 contract

Status: P00 contract freeze, 2026-09-30. The executable DTO definitions are
in `api/app/http_schemas/tailoring.py`,
`api/app/http_schemas/tailoring_evaluation.py`, and
`api/app/http_schemas/tailoring_fit_review.py`. The frontend mirrors them in
`web/src/features/tailoring/types/index.ts`. Service validation, route
adapters, and storage implementation are owned by later packets.

## Compatibility boundary

- Protocol 10 is the only version that may be created, exchanged, or resumed
  by the new authoring helper. Code exchange includes the URL's `session_id`;
  the server checks that it matches the one-time code before consuming it.
- Owner status and review continue to parse protocols 4–9. Their existing
  `result` payload remains a historical dictionary, and additive
  `draft_review` is absent or null. In particular, protocol 8 editorial
  review data remains readable. Evaluation-v2 field names and structure are
  unchanged.
- Legacy owner accept may omit its request body. Protocol 10 acceptance must
  include `expected_cv_revision` and the `candidate_hash` from a current owner
  review. A v10 request without either token is invalid; legacy requests keep
  their previous acceptance behavior.
- The existing `tailoring_sessions.result` column remains available for
  historical rows. New submissions use immutable `submission_result`; status
  serialization must not rewrite the submitted candidate when owner review
  changes.
- `CV.revision` already exists. Its update semantics become meaningful
  document revisions: a no-op save does not increment it. Owner CV responses
  expose the revision so the builder can send the saved value during
  reevaluation. `CVResponse.revision` defaults to 1 when validating older
  response fixtures.

## HTTP contracts

All paths below are below `/api/v1`. Capability-scoped calls send
`X-Aergia-Tailoring-Capability`; owner calls use the existing authenticated
session and CSRF handling.

### Exchange and frozen authoring context

`POST /tailoring/exchange` accepts:

```json
{
  "protocol_version": 10,
  "session_id": "<UUID from the supplied session URL>",
  "code": "<one-time code>"
}
```

The response keeps the existing `session_id`, `expires_at`, and in-memory
capability contract. A wrong session ID fails before code consumption.

`GET /tailoring/context` returns the immutable writer context. In addition to
the existing job, dossier, templates, selected template, capabilities, and
evaluation version, protocol 10 returns:

- `source_cv_revision: integer | null`;
- `scanner_context` with `schema_version: "scanner-v1"`, frozen scanner
  versions, requirement extraction, and optional source scan;
- a stable 64-character lowercase hexadecimal `context_hash` for the frozen
  context.

The dossier contains the profile, Library history, and (when present) a
clearly labeled readable source CV. `context_hash` identifies this immutable
snapshot. It is not the live target guard: application ownership, target job
and instructions, linked source CV identity/revision, and compatible
renderer/scanner contract are checked separately. Unrelated Library, profile,
or template edits do not silently replace the snapshot.

### Preview reservation and immutable PDF

`POST /tailoring/preview-reservations` accepts:

```json
{
  "context_hash": "<64 lowercase hex characters>",
  "candidate": { "title": "...", "template_id": "...", "sections": [], "customizations": {} },
  "request_id": "<UUID generated once for this attempt>"
}
```

It returns `reservation_id` (UUID), the canonical normalized
`candidate_hash`, and `expires_at`. The lease lasts up to 120 seconds and is
capped by capability expiry. Acquisition is a short transaction; Chromium
and scanner work runs after the transaction releases its database write
lock.

`POST /tailoring/preview` now also requires `reservation_id`; it retains the
existing `context_hash` and complete `candidate`. Its response retains the
canonical candidate, exact PDF bytes as base64, page count, evaluation ID,
candidate hash, scanner result, evaluation-v2 report, and render warnings. It
adds `pdf_sha256`, the lowercase SHA-256 digest of those exact returned PDF
bytes.

`POST /tailoring/preview-reservations/{reservation_id}/release` releases an
uncompleted lease idempotently. It returns one of `released`,
`already_released`, or `completed`; releasing a completed evaluation does not
remove it.

Reservation/replay rules:

- A session has at most one `active` uncompleted reservation. A competing
  request gets `preview_in_progress` and can retry.
- `(session_id, request_id)` identifies one normalized candidate and context.
  Repeating it with the same values returns the existing reservation or
  completed result. Reusing it with altered input returns
  `request_id_reused`.
- An expired lease can be reclaimed atomically. Completion is fenced against
  the original lease, so a late renderer cannot finish a reclaimed attempt.
- A failed render can release its lease without spending a successful preview
  slot. Only five successful agent evaluations may be stored per session.
- Completed retries replay the stored PDF bytes and digest. The server never
  rerenders and claims newly generated bytes have the old digest.

### Submit and advisory fit review

`POST /tailoring/submit` retains `context_hash`, `evaluation_id`,
`candidate_hash`, canonical `candidate`, and `review_notes`. It adds nullable
`fit_review`. Missing or null means **Not run**; it is not a success verdict.
The backend accepts an absent report and never creates one.

`fit-review-v1` has a strict, closed shape with no extra metadata:

| Status | Required fields |
| --- | --- |
| `completed` | `version`, `evaluation_id`, `candidate_hash`, `pdf_sha256`, `mode: fresh_agent \| manual_external`, `verdict: tailored \| partially_tailored \| generic`, `rationale`, `strong_connections`, `weak_or_missing_connections`, `recommended_changes` |
| `unavailable` | The three bindings, `status`, and a short `reason`; no verdict or findings |
| `skipped_explicitly` | The three bindings, `status`, and a short `reason`; no verdict or findings |

All reports use `version: "fit-review-v1"`. The IDs and SHA-256 values have
fixed formats. A rationale/reason is at most 1,200/500 characters. Finding
strings are at most 500 characters; strong connections and weak/missing
connections have at most five items each, and recommended changes at most
three. Empty finding arrays are valid. Backend services verify that all
three values bind to the selected immutable preview. Schemas validate shape;
they do not claim a report is independent or judge its quality. A
`generic` verdict, an unavailable report, and an explicit skip are all
advisory and never block submission or acceptance.

The helper exports the explicitly selected saved preview as `candidate.pdf`
using those exact stored bytes, `job.json` containing only `company`, `role`,
and `description`, and a manifest containing `evaluation_id`,
`candidate_hash`, and `pdf_sha256`. It excludes the dossier, ideal CV, author
history, application notes, scanner scores, source identifiers, and
capabilities. The review prompt is a separate reference and uses a separate
review directory and fresh conversation. This workflow separation is not an
OS sandbox when the installed agent host shares filesystem access. The author
does not label self-assessment as independent. Use `unavailable` when the
host cannot delegate or inspect PDFs. Use `skipped_explicitly` only when the
user explicitly instructs skipping; elapsed waiting is not an instruction.
The helper's `REVIEW` action writes `output/fit-review.json`, validates that
its three bindings match the current `selection.json` attempt, and freezes
that report in memory for submission. A report from another attempt must be
rejected even if filenames are reused.

### Owner status, reevaluation, and builder context

`GET /tailoring/sessions/{session_id}` retains its lifecycle fields and adds
nullable `draft_review` for v10. It is null for historical rows and can be
`unavailable` if the pending draft no longer exists.

`draft_review` contains:

- `state: current | needs_reevaluation | unavailable`;
- current persisted `cv_revision` and canonical `candidate_hash`;
- `render_basis_hash` for the current review basis when available;
- current owner `evaluation_id`, evaluation-v2 report, scanner result,
  warnings, and `pdf_sha256`;
- the submitted `fit_review` and
  `fit_review_applicability: current | earlier_version | not_run`.

When `state` is `current`, the evaluation, scanner result, warnings, and PDF
digest apply to the current `cv_revision`, `candidate_hash`, and render basis.
When `state` is `needs_reevaluation`, those current-evaluation fields are null
or empty; the current CV revision/hash remain available for the reevaluation
request. A recorded fit review remains bound to its original agent preview:
`current` means that exact candidate and PDF digest still match;
`earlier_version` means the report is retained for context but does not
describe the current PDF; `not_run` means no report was recorded. For
`unavailable`, all review fields are null/empty and applicability is
`not_run`.
For `unavailable`, all review fields are null/empty and applicability is
`not_run`.

`POST /tailoring/sessions/{session_id}/reevaluate` accepts
`{"expected_cv_revision": integer}`. It evaluates the persisted draft and
returns `session_id`, `application_id`, `draft_cv_id`, current `draft_review`,
canonical PDF base64, and page count. It uses current templates and
authoritative identity/contact values. It prepares normalization and renders
in memory, then conditionally writes only if the persisted CV revision still
matches; a racing edit returns an actionable conflict and is never
overwritten. This owner operation does not spend the agent preview budget.

V10 `POST /tailoring/sessions/{session_id}/accept` requires
`{"expected_cv_revision": integer, "candidate_hash": "<64 lowercase hex>"}`.
Both values must match a current owner review and are checked atomically with
the expected application source/job basis. Advisory warnings and fit-review
verdict do not affect the acceptance guard.

`GET /cvs/{cv_id}/tailoring-context` returns 404 for ordinary CVs. For an
owned pending draft it returns only protocol version, `session_id`,
`application_id`, `draft_cv_id`, `draft_review`, the saved session `job`, and
`scanner_context` (`scanner-v1` versions and requirement extraction). It
deliberately omits `source_scan`, so the linked source CV's scanner output
cannot be displayed as the draft's result. A deleted or non-owned CV does
not reveal its tailoring session.

### Conflict envelope

Tailoring conflicts return the established HTTP status meaning plus the
bounded top-level JSON shape `{"code": "...", "detail": "..."}`. The
human-readable `detail` is not a client control signal. Codes are:

`stale_target`, `edited_draft`, `preview_in_progress`, `preview_limit`,
`quota`, `inactive_capability`, `invalid_session`, `context_mismatch`,
`reservation_expired`, `reservation_conflict`, `request_id_reused`,
`candidate_invalid`, `evaluation_mismatch`, `draft_unavailable`,
`review_not_current`, `source_changed`, and `application_unavailable`.

The existing status classes remain: 401 for invalid/revoked capability, 410
for expired capability, 404 for missing or inaccessible resources, 409 for
stale/conflict/quota outcomes, and 422 for invalid candidate input. Rate
limiting remains 429. `inactive_capability` is the shared machine code for
401/410 while the status keeps the invalid-versus-expired distinction.

## Service interface blueprint

These are the agreed operations and payloads for later service/router
packets. `TailoringService` continues to flush but never commits; route
dependencies own commit and rollback. Names are normative where called out.

```python
exchange_code(data: TailoringCodeExchange) -> TailoringExchangeResponse
context(capability: str | None) -> TailoringContextResponse
reserve_preview(
    capability: str | None,
    data: TailoringPreviewReservationRequest,
) -> TailoringPreviewReservationResponse
release_preview_reservation(
    capability: str | None,
    reservation_id: str,
) -> TailoringPreviewReservationReleaseResponse
candidate_preview(
    capability: str | None,
    data: TailoringPreviewRequest,
) -> TailoringPreviewResponse
submit(capability: str | None, data: TailoringSubmitRequest) -> TailoringSubmitResponse
reevaluate_draft(
    session_id: str,
    user_id: str,
    data: TailoringReevaluateRequest,
) -> TailoringReevaluateResponse
accept_draft(
    session_id: str,
    user_id: str,
    data: TailoringAcceptRequest | None = None,
) -> TailoringReviewResponse
draft_context(cv_id: str, user_id: str) -> TailoringDraftContextResponse
```

Existing create/status/cancel/reject service methods keep their names and
ownership rules. V10 code exchange checks session identity before consuming
the code. Fit-review binding checks occur in the service at submit. Owner
reevaluation renders before its conditional revision write. Reservation
transactions remain short and lease-fenced.

## Database and index blueprint for P03

Keep existing columns and historical data. Add these v10 fields to
`tailoring_sessions`:

| Field | Type / purpose |
| --- | --- |
| `source_cv_revision` | Nullable integer captured with the frozen source CV |
| `target_guard_hash` | 64-character digest for the separately checked live target |
| `submission_result` | Immutable JSON submission (candidate, scanner/evaluation, fit report, review notes and bindings); no PDF bytes |
| `owner_review_state` | Nullable `current | needs_reevaluation | unavailable` |
| `owner_cv_revision` | Nullable current meaningful draft revision |
| `owner_candidate_hash` | Nullable canonical current candidate hash |
| `owner_render_basis_hash` | Nullable owner render basis digest |
| `owner_evaluation_id` | Nullable pointer to latest owner evaluation record |
| `owner_pdf_sha256` | Nullable exact current owner PDF digest |

`context_snapshot` stores the complete frozen profile, Library, readable
source-CV snapshot and revision, job/instructions, template manifests,
capabilities, and scanner basis. Existing `context_hash` is the stable digest
of that immutable context; `target_guard_hash` is checked separately.

Add `TailoringEvaluationRecord` / `tailoring_evaluations` as the immutable
evaluation ledger. It stores `id`, `session_id`, `kind` (`agent_preview` or
`owner_review`), nullable `reservation_id`, `candidate_hash`, canonical `candidate` JSON,
`scanner_result` JSON, evaluation-v2 JSON, `render_warnings` JSON,
`page_count`, `pdf_sha256`, nullable private `pdf_bytes`, and `created_at`.
The nullable reservation key is unique: each agent evaluation belongs to one
preview reservation, while owner evaluations leave it null. Preview
completion must use the original lease's compare-and-swap/savepoint so a
late completion cannot leave an orphan evaluation or consume budget.
Rows retain binding metadata if PDF bytes are pruned. The selected agent PDF
is retained for pending owner review; unselected PDF bytes are dropped on
submit. Terminal cleanup drops all session PDF blobs but keeps small binding
records and reports. When a newer owner review replaces an older owner
review, prune the superseded owner PDF bytes so reevaluations do not
accumulate blobs. The selected agent PDF can remain separately bound to its
submission while that draft is pending.

Add `TailoringPreviewReservation` /
`tailoring_preview_reservations` with `id`, `session_id`, UUID `request_id`,
`context_hash`, canonical `candidate_hash`, lease `expires_at`, state
`active | released | completed | expired`, nullable `evaluation_id`, and
timestamps. Add a unique index on `(session_id, request_id)` and a partial
unique index allowing one `active` reservation per session. Only `active`
holds the per-session lock. Keep lease state separate from expensive render
work.

Add these unique invariants:

- one blocking session per application for statuses `created`, `exchanged`,
  or `draft_ready`;
- one active preview reservation per session and one reservation row per
  `(session_id, request_id)`;
- one `pending` replacement reservation per application and one pending
  allowance per source CV.

Add `CV.quota_counted` (boolean, default true) as internal provenance; never
infer quota authority from editable metadata. `CV.revision` is already
present and remains the monotonic meaningful-content token. Add
`TailoringReplacementReservation` /
`tailoring_replacement_reservations` with `id`, `application_id`,
`source_cv_id`, `draft_cv_id`, state `pending | transferred | released`, and
timestamps. A successful acceptance transfers the allowance and old source
atomically; reject/discard releases it without changing the normal CV count.
Existing CVs backfill as counted, and historical drafts receive no
retrospective allowance.

SQLite partial indexes and migration reconciliation must match repository
connection behavior. Services use savepoints/conditional updates for expected
uniqueness races, perform flushes only, and do not hold a write lock across
Chromium or scanner work.

## Frontend and implementation handoff

`web/src/features/tailoring/api/tailoring.ts` starts sessions with protocol
10, provides owner reevaluation and draft-context calls, and sends acceptance
tokens when supplied. Its optional empty accept body exists only for
historical 4–9 drafts; the v10 owner UI must supply both tokens. The new API
functions need to be exported from the feature public `index.ts` when the
owner UI/builder packets wire them. `TailoringDraftContextResponse` gives the
builder the saved job/requirements and current review state, with no dossier
or source scan. Saving an owner edit makes that review stale; reevaluation
uses the CV response's saved revision after the save succeeds.

Keep API modules thin and service validation out of Pydantic shapes. Do not
change renderer architecture, public session URL, evaluation-v2 fields, or
historical results as part of implementing these contracts.
