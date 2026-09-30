# Tailoring audit — 2026-09-30

Audited repository revision `04df13e`, protocol v9, and
`tailoring-evaluation-v2`. This is an implementation and integration audit.
Application code, public contracts, database structure, and skill behavior
were not changed. The report and tracker entries are the durable outputs.

## Findings summary

Found **12 issues: 7 P1 and 5 P2**. Here P1 means a significant correctness,
workflow, or confidentiality defect to address before release; P2 means a
bounded defect with a workaround or narrower impact. No P0 was identified.

The canonical rendering architecture, scoped agent authorization, and
explicit preview binding are sound in the ordinary sequential flow. The
largest gaps are owner draft recovery, frontend resource isolation, and
concurrent session/evaluation writes. Passing release checks do not cover
these cases.

| ID | Priority | Finding | Evidence |
| --- | --- | --- | --- |
| T01 | P1 | Deleting a draft permanently blocks new tailoring for that application | API reproduction |
| T02 | P1 | Editing a draft makes its advertised acceptance flow unusable | API reproduction |
| T03 | P1 | Application navigation retains and acts on the previous application's session | React/Chromium reproduction |
| T04 | P1 | Concurrent previews overwrite evaluation history | API reproduction with a render barrier |
| T05 | P1 | Concurrent creation permits multiple active sessions | API reproduction with a query barrier |
| T06 | P1 | Valid keyword visibility changes fail evaluation schema validation | Pure evaluator reproduction |
| T07 | P1 | Interactive code input echoes the one-time credential | PTY reproduction with terminal echo disabled |
| T08 | P2 | Owner review omits scanner review items | Source tracing |
| T09 | P2 | Stale acceptance rolls back the status needed to explain recovery | API reproduction |
| T10 | P2 | Helper never binds the supplied link to returned session IDs | Mock transport reproduction |
| T11 | P2 | Preview access failures are treated as repairable candidate errors | Mock transport reproduction |
| T12 | P2 | Matching documentation describes removed indexing infrastructure | Source/migration comparison |

## Detailed findings

### T01 — Deleted drafts cannot be dismissed or replaced

**Location:** `api/app/services/tailoring.py:1478`,
`api/app/services/tailoring.py:662`, and `api/app/services/cv.py:199`.

An unaccepted draft is visible through ordinary CV listing and can be deleted
through `DELETE /api/v1/cvs/{draft_id}`. Deletion makes the CV inactive but
leaves its tailoring session `draft_ready`. Acceptance then rejects the
missing draft, rejection fails because `delete_cv()` returns false, and
cancellation only permits `created`/`exchanged`. Session creation blocks on
the existing `draft_ready` row even after its capability has expired.

**Reproduction:** submit a valid candidate; delete the returned draft through
the ordinary CV endpoint; reject the session; try to start another session.
Deletion returned 204, both later operations returned 409, and status remained
`draft_ready`. This strands tailoring for the application without a normal
session recovery action.

**Recommendation:** reconcile ordinary draft deletion with its session, or
allow rejection to finish when the draft is already inactive/missing. Keep
quota release idempotent. Test deletion followed by reject and restart.

### T02 — Owner edits invalidate acceptance with no reevaluation path

**Location:** `api/app/services/tailoring.py:1397`,
`web/src/features/applications/components/detail/ApplicationCvPanel.tsx:111`,
and `web/src/features/builder/hooks/useBuilderPersistence.ts:85`.

The review panel offers **Open/Edit draft**, and the skill promises owner
review and editing. Normal saves change the persisted candidate. Acceptance
compares that candidate with the original submission and rejects every
material change with “review it again.” There is no owner endpoint to refresh
the draft's frozen candidate/evaluation binding. The builder only attaches
application scanner context when the CV is currently linked, so the unlinked
draft's editor does not provide that recovery path either.

**Reproduction:** submit a valid draft, change only its title through
`PATCH /api/v1/cvs/{draft_id}`, then accept. The edit returned 200; acceptance
returned 409 with “changed after submission.” Rejecting remains possible,
but the edited draft cannot complete the advertised review flow.

**Recommendation:** support explicit owner reevaluation and confirmation of
the edited draft while preserving immutable agent preview history. If edits
are intentionally unsupported before acceptance, align the UI and skill
promise with that decision. Do not simply remove the binding check.

### T03 — Session state leaks across application navigation

**Location:** `web/src/features/tailoring/hooks/useTailoringSession.ts:39`,
`web/src/features/tailoring/hooks/useTailoringSession.ts:151`, and
`web/src/features/applications/pages/ApplicationDetailPage.tsx:61`.

Changing `applicationId` starts a latest-session request but does not clear
the old session, result, or status. A 404 for the new application is swallowed,
leaving the previous session active in the UI. Review callbacks use that
retained session ID. The detail page also prefers
`currentApplication.id` over the route ID while the next application loads,
which increases the period during which requests target the previous resource.

**Reproduction:** mount the real hook with application A and a ready draft;
switch its prop to application B whose latest-session request returns 404;
invoke acceptance. A real React render in Chromium showed application B with
`sessionApplicationId: application-A`; the acceptance API mock received
`session-A`. This is a wrong-application action within the same owner account,
not a bypass of backend ownership checks.

**Recommendation:** key all session state to the route's application ID,
clear or hide mismatched state before rendering actions, and ignore stale
results from every asynchronous action. Cover navigation to an application
with no session and overlapping latest/create requests.

### T04 — Concurrent previews lose successful evaluations

**Location:** `api/app/services/tailoring.py:1168` and
`api/app/services/tailoring.py:952`.

Each request reads the JSON evaluation history and later replaces the entire
snapshot with a local copy plus one new evaluation. There is no lock,
revision comparison, or atomic append. Two requests can both pass the
five-preview check and render successfully, then overwrite each other's
history. One returned evaluation ID becomes unavailable for submission, and
the history length understates the number of successful previews.

**Reproduction:** hold two requests at the PDF render boundary until both have
read their context. Both preview responses returned 200 with different IDs;
the committed session contained only one evaluation. Repeating this pattern
can also weaken the five-preview resource budget.

**Recommendation:** atomically reserve preview slots and preserve every
successful evaluation. Use database concurrency control suitable for SQLite;
avoid holding its write lock throughout expensive rendering. Test overlapping
previews, selecting each returned ID, and the budget boundary.

### T05 — Single-active-session enforcement is a check/insert race

**Location:** `api/app/services/tailoring.py:662` and
`api/app/models/tailoring_session.py:91`.

Creation first queries active sessions and then inserts a new one. The model
has lookup indexes but no database invariant enforcing a single active
session for an application. Two browser tabs or overlapping requests can
both observe no active session. The latest-session UI then shows only one,
although both capabilities can be exchanged and produce drafts.

**Reproduction:** allow both active-session SELECTs to complete before either
inserts. Both creation requests returned 201 and the database contained two
`created` sessions for the same application.

**Recommendation:** serialize the check and insert or add an appropriate
database invariant with conflict handling. Account for expiry/stale cleanup
when choosing an index or transaction design. Test simultaneous creation.

### T06 — Exact-to-variant keyword changes crash evaluation

**Location:** `api/app/services/tailoring_evaluation.py:418` and
`api/app/http_schemas/tailoring_evaluation.py:22`.

`_classify_keyword()` can return `changed_needs_review`, including when
visibility moves from `exact` to `variant` or `normalized`.
`_transition_changes()` passes that value straight into
`TailoringPassChange.classification`. Its schema only accepts `fixed`,
`introduced`, `improved`, and `regressed`. A valid CV revision therefore
raises a Pydantic `ValidationError` while comparing previews. The route does
not translate this internal error into actionable candidate feedback.

**Reproduction:** evaluate a valid scan with `variant` keyword visibility
against a previous scan with `exact` visibility. Validation failed on the
pass-change classification. This can prevent the second preview despite a
structurally valid document and a recognized keyword alias.

**Recommendation:** map every transition classification into a supported
pass-change value while retaining the review explanation, or deliberately
revise the contract. Test the complete visibility transition matrix.

### T07 — One-time code input is echoed into terminal output

**Location:** `tailoring-skill/skills/aergia-tailor/scripts/session.mjs:82`
and `tailoring-skill/skills/aergia-tailor/SKILL.md:19`.

The instructions require non-echoing interactive stdin, but `readline.question`
uses stderr as its terminal output and performs its own input echo. Disabling
the terminal's ECHO flag is insufficient. An agent following the ordinary
interactive command can place the plaintext credential in its captured
terminal transcript before exchange completes.

**Reproduction:** run the CLI in a PTY with ECHO disabled, send a synthetic
one-time code, and inspect captured output. The complete synthetic code was
present. No real credentials were used.

**Recommendation:** implement masked/silent terminal input with reliable
restoration on exit, or provide a documented safe non-terminal stdin path.
Keep the capability in memory and never accept credentials as CLI arguments.
Test the actual interactive input path, which current helper tests bypass
through `options.code`.

### T08 — Required-conflict and ATS review findings are hidden

**Location:**
`web/src/features/applications/components/detail/ApplicationCvPanel.tsx:103`
and `api/app/services/tailoring_evaluation.py:621`.

The evaluator places conflicting/unverifiable requirements, quality warnings,
and ATS warnings in `evaluation.review_items`. The owner panel displays risk
findings, improvements/regressions, gaps, and recommendations, but never
`review_items`. A required qualification conflict can therefore be absent
from the “Review before accepting” panel. Its list truncation also provides
no expanded view of the omitted items. The normal application scanner drawer
describes the linked CV, not the unaccepted draft.

**Evidence:** traced every evaluation bucket from the service through the
frontend types and review JSX. `review_items` is declared in the type and
is not consumed by the panel.

**Recommendation:** expose prioritized draft review items, with a way to
inspect the complete candidate scan. Give required conflicts clear context
without turning advisory findings into an unauthorized acceptance gate.
Frontend follow-up: `$impeccable harden`.

### T09 — Stale acceptance status changes disappear on rollback

**Location:** `api/app/services/tailoring.py:1375` and
`api/app/db/session.py:23`.

Acceptance sets `status = stale`, flushes, then raises a service error. The
route translates it to an HTTP exception, causing `get_db()` to roll back the
status update. Status polling only checks context freshness for `created` and
`exchanged`, so a stale ready draft continues to appear ready. The response
tells the user to start a new session, but creation still blocks on it.

**Reproduction:** submit, change the saved profile, then accept. Acceptance
returned 409 directing restart; the next status request returned `draft_ready`.
Rejecting the existing draft is a workaround, but the error/state combination
does not explain it.

**Recommendation:** reconcile ready-draft staleness through a transaction that
can finish, such as status reconciliation returning normally, and define
draft/quota cleanup when a session becomes stale. Preserve the route-owned
commit/rollback rule. The UI should refresh status after review conflicts.

### T10 — Session link identity is discarded by the helper

**Location:** `tailoring-skill/skills/aergia-tailor/scripts/session.mjs:34`
and `tailoring-skill/skills/aergia-tailor/scripts/session.mjs:497`.

The link is parsed into an origin; its session ID is never compared with
`exchange.session_id` or `context.session_id`. If a user accidentally pairs
a valid code from session B with a same-origin link for A, the helper opens
B's job and dossier and can submit to B while the supplied link names A.
The scoped code still authorizes B, so this is a resource-consistency failure,
not access beyond the supplied capability.

**Reproduction:** use a link ending in `requested-session` and mocked exchange
and context responses naming `different-session`. The helper reached candidate
authoring and wrote the different session's context.

**Recommendation:** retain the parsed session ID and require agreement across
the link, exchange, and context before exposing any candidate material.

### T11 — Preview authentication failure does not stop the helper

**Location:** `tailoring-skill/skills/aergia-tailor/scripts/session.mjs:385`
and `tailoring-skill/skills/aergia-tailor/scripts/session.mjs:456`.

Submission handles access failures as terminal. Preview handles stale-context
and preview-limit responses, but sends 401/403/410 and revoked-capability
responses through the general “repair candidate.json” path. After cancellation
or expiry, the author can keep trying revisions that cannot succeed. This
contradicts the skill's instruction to stop when access expires or is revoked.

**Reproduction:** return 401 for preview. Status became
`candidate_or_preview_error`; another RENDER caused another HTTP request.
The helper remained alive until its local expiry deadline.

**Recommendation:** apply the terminal access-error classification to preview
as well as submit. Distinguish invalid CV payloads from revoked sessions.

### T12 — Documentation still promises removed candidate indexing

**Location:** `docs/matching-and-tailoring.md:34` and
`api/alembic/versions/v0w1x2y3_full_history_tailoring_v9.py:20`.

The document describes current persistent candidate index tables, Library
index updates, proposition workers, stale-source refresh, and scanner use of
the index. Protocol v9 removed that implementation, and its migration drops
the index/state/semantic tables and Library `row_ids`. The same document later
describes the current full-dossier workflow, leaving contradictory architecture
guidance in a primary reference.

**Recommendation:** rewrite the indexing passages around the current
implementation or explicitly label them historical. Align the skill-identity
section and page-use guidance with the current skill and scanner boundary.

## Frontend technical assessment

**Implementation integrity: fail for reliable session isolation and owner
review completion.** The feature structure and styling are coherent, but
T01–T03 and T08 are material problems in its task flow. The Impeccable
mechanical detector returned `[]`; that result does not detect these behavioral
defects. The architecture checker and fixtures passed.

These scores are a source-based assessment of the tailoring landing page and
review panel, not a full WCAG certification or a device/performance benchmark.
The browser reproduction exercised the hook with mocked API responses; it did
not assess production UI appearance.

| Dimension | Score / 4 | Evidence and limitation |
| --- | --- | --- |
| Accessibility | 3 | Native buttons/links, heading structure, labeled prompt, status/alert semantics; no complete keyboard or screen-reader audit |
| Performance | 2 | Lightweight landing page, but interval polling allows overlapping requests and repeatedly processes context/status without backoff |
| Responsive design | 3 | Fluid widths and wrapping controls; several compact actions lack generous touch areas; no full viewport matrix measured |
| Theming | 3 | Application tokens consistently used; white action text aligns with the supplied palette; no theme matrix measured |
| Implementation integrity | 1 | Confirmed resource state leak and broken advertised edit/review flow |
| **Total** | **12 / 20** | **Significant work needed; behavioral defects determine release priority** |

Recommended frontend order: `$impeccable harden` for resource isolation,
pending review actions, conflict recovery, and complete findings;
`$impeccable adapt` for touch targets after behavior is repaired;
`$impeccable polish` as the final bounded pass. These commands are suggestions;
no interface changes were made during the audit.

## Scope and ownership map

All files in the portable skill and `web/src/features/tailoring/` were read.
Associated integrations were followed through the following owners. Shared
subsystems were inspected at their tailoring boundary and tested where listed;
this does not claim an independent audit of every unrelated feature.

| Area | Files/folders covered |
| --- | --- |
| Portable skill | `tailoring-skill/AGENTS.md`, `README.md`, `skills/aergia-tailor/SKILL.md`, both reference documents, `scripts/session.mjs`, `tests/session.test.mjs` |
| Backend contracts/lifecycle | `api/app/routes/tailoring.py`, `http_schemas/tailoring.py`, `http_schemas/tailoring_evaluation.py`, `services/tailoring.py`, `tailoring_evaluation.py`, `tailoring_validation.py`, `tailoring_skill.py`, `models/tailoring_session.py` |
| Evidence and writes | Profile and Library services/models, CV service/routes, application service/routes and models, rich-text normalization, quota reservation, database dependencies |
| Scanner and renderer | `document_schema/capabilities.py`, document/wire models, scanner contract/scoring/freshness boundaries, PDF service, renderer pipeline/resolution, HTML output and links, Playwright singleton/lifecycle |
| Frontend | All tailoring API/domain/hooks/pages/types/entrypoint files, public agent route, application detail/CV panel/state, tailoring entrypoints in list/form/scanner drawer, builder save/application-context integration, shared API/security helpers, application tokens |
| Persistence/deployment | Tailoring migration history and v8/v9 cutover, test migration contracts, app middleware and route registration, Start `/api/*` gateway, `api/Dockerfile` skill packaging, release smoke script |
| Project knowledge | Closest repository instructions, related tailoring tracker history/ADRs, `docs/matching-and-tailoring.md` |

Personal installed skill copies were not modified. User databases and stored
CV/profile contents were not used. Reproductions used new temporary databases,
synthetic credentials, fixture scanner extraction, and mock PDFs where needed.

## Verification evidence

| Check | Result |
| --- | --- |
| Focused tailoring backend suite | 31 passed across lifecycle, contracts, evaluation, and migration tests |
| Associated scanner/renderer/security suite | 149 passed |
| Temporary API/evaluator audit reproductions | 6 passed: five test functions confirm defects and one confirms unchanged v9 acceptance succeeds |
| Helper suite | `node --test tailoring-skill/tests/*.test.mjs` exited 0; file contains 13 declared tests; reporter summarized one passing test file |
| Additional helper checks | Session-ID mismatch and preview-401 continuation reproduced with mock transport; interactive code echo reproduced in a PTY |
| Frontend behavior reproduction | Real React hook executed in Chromium; wrong-session acceptance reproduced with mocked API |
| Frontend lint | Passed with 9 existing hook-dependency warnings in BuilderPage/RichTextToolbar |
| Typecheck | Passed |
| Frontend architecture fixtures/check | Passed |
| Codegen consistency | Passed |
| Impeccable detector | No mechanical findings on the tailoring feature and application CV panel |
| `./dev.sh --smoke` | Passed after rerunning with local network access; isolated server/database, SSR, CSP, cookie and gateway checks |
| Tracker validation | 0 errors; 7 existing fork warnings |

The first smoke attempt could start the local server but could not reach it
under restricted networking. The rerun with local access completed with
`SMOKE OK`. Backend test warnings concerned the test JWT key length and runtime
deprecations; they were not failures or new production-secret findings.

The full backend suite, production model loading, external provider calls,
installed-agent compatibility, dependency vulnerability scan, and exhaustive
responsive/accessibility tests were not performed. Sequential smoke success
does not validate the races reproduced here. The existing integration test
changes its draft to protocol v8 before owner acceptance; the temporary audit
also verified unchanged protocol-v9 acceptance directly.

Temporary reproduction artifacts remain under `/tmp` for this workspace:
`aergia_tailoring_audit_test.py`, `aergia_tailoring_helper_audit.mjs`,
`aergia_tailoring_frontend_bundle.mjs`, and
`aergia_tailoring_frontend_audit.py`. They assert the observed defects and are
not implementation fixes or permanent regression tests. The API script runs
from `api/` with
`PYTHONPATH=.:tests .venv/bin/pytest -p conftest -c pyproject.toml -q -s /tmp/aergia_tailoring_audit_test.py`.

## Follow-up tracking

Audit task: `TASK-01M3T1XBAA6W4NC1ZB1YY13W81`.

| Findings | Open tracker issue |
| --- | --- |
| T01, T02, T09 | `BUG-01M3T1XBF2CD74C3M9J9YNGXSE` |
| T04, T05 | `BUG-01M3T1XBM7SFG5WP850T0BJBEN` |
| T06 | `BUG-01M3T1XBRS0N6S8X5CARQW19MB` |
| T03 | `BUG-01M3T1XBXRWSBCTZAHHXBF2GSZ` |
| T07, T10, T11 | `BUG-01M3T1XC1VTAX6M5C778Q7A3BS` |
| T08 | `BUG-01M3T1XC6Q19KZQQZTVV1PCTAP` |
| T12 | `BUG-01M3T1XCBYDC9FH6PG3N6XGD3S` |

Repair draft deletion/review recovery and wrong-application state first,
then protect concurrent writes and correct evaluation classification. Fix
interactive credential handling before recommending ordinary terminal
installation/use. Complete the remaining feedback, access, and documentation
repairs, then promote the reproductions into meaningful permanent regression
coverage and rerun the release gate.
