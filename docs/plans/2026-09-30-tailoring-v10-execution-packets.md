# Tailoring v10 execution packets

Status: planned. These are assignments for later execution, not completed work.

Read the [implementation plan](2026-09-30-tailoring-v10-implementation.md)
first, especially its contract, quota, review, and compatibility decisions.
The [audit](../tailoring-audit-2026-09-30.md) supplies defect evidence.
Paths marked “new” below are proposed; verify the current checkout before work.

## Coordinator instructions

Use this spawn configuration later, with a self-contained message:

```json
{
  "task_name": "tailoring_pNN",
  "model": "gpt-6-luna",
  "reasoning_effort": "max",
  "fork_turns": "none",
  "message": "Use the packet template below with the actual PNN scope."
}
```

Do not execute this while writing the plan. Root plus three children is the
maximum. Every assignment must identify an isolated checkout or shared-tree
ownership. The coordinator reviews and integrates each packet before its
dependents begin. Agents must not spawn children, expand contracts, edit
another packet's files, merge to master, or publish changes themselves.

### Assignment message template

> Implement PNN only, using `gpt-6-luna` with max reasoning. Repository/check-out:
> [absolute path]; base revision: [revision]; tracker ID: [ID].
>
> Read the root AGENTS.md, the closest subsystem AGENTS.md, the implementation
> plan's relevant sections, this packet, and [specific audit findings]. Search
> tracker context and affected files before editing. Use apply_patch for hand
> edits. The agreed feature changes authorize v10 behavior described by the
> plan; preserve other product behavior and the canonical renderer.
>
> Own only [explicit file list]. Shared contracts are frozen at [revision].
> Report a required adjustment to the coordinator and continue independent
> work; do not silently change the contract. Do not spawn agents or write
> tracker history. Do not use real candidate data, credentials, or capabilities
> in fixtures, files, logs, commits, or reports.
>
> Finish the bounded implementation and its meaningful focused regressions.
> Return changed files, a commit if working in an isolated checkout, exact
> verification commands/results, evidence for each acceptance condition,
> proposed tracker updates, and concrete remaining risks. If all requested
> work cannot fit the packet, propose a separately owned follow-up.

### Shared-file order

| Files | Ownership order |
| --- | --- |
| `api/app/services/tailoring.py` | P04 → P05 → P07 |
| `api/app/routes/tailoring.py` | P05 → P07; final protocol wiring by coordinator |
| `api/app/http_schemas/tailoring.py`, evaluation DTO, new fit-review DTO | P00 only; later changes require coordinator approval |
| ORM definitions, Alembic revision | P03 only; coordinator-approved schema corrections return to P03 |
| `scripts/session.mjs`, existing helper tests | P02 → P08 |
| Frontend tailoring types/API | P00; coordinator applies a necessary correction |
| `useTailoringSession.ts`, `ApplicationDetailPage.tsx` | P09 → P10 |
| Skill prose and local guide | P12; independent-review reference belongs to P08 |
| Tracker history, generated schema, final integration fixture changes | Coordinator |

Each packet should put new regressions in its own test file where practical.
Avoid having several worktrees independently rewrite `test_tailoring.py` or
`session.test.mjs`. The coordinator assigns any additional discovered file
explicitly before edits begin.

## P00 — Freeze v10 contracts and compatibility

**Depends on:** fresh baseline review. **Audit:** all, especially T02/T04/T09.

**Own:** backend HTTP tailoring/evaluation DTOs; new
`api/app/http_schemas/tailoring_fit_review.py`; frontend tailoring types/API;
new contract fixtures and ADR. Version declarations can advance on the
integration branch; release cutover waits for the complete feature. Do not
deploy intermediate commits whose lifecycle implementation is incomplete.

**Deliver:** exact DTO field shapes from plan §3; error codes; fit-review
string/array bounds; historical optionality; owner acceptance concurrency
tokens; reservation replay semantics; API declarations and reusable synthetic
fixtures. Document how protocol 4–9 responses remain readable. Define the
database field/index blueprint for P03 and the service interfaces needed by
P04/P05/P06/P07/P08. Update this plan only for reviewed corrections.

**Verify:** focused contract tests for every new payload and historical
result, rejected extra review metadata, verdict-free unavailable reports,
bad hash/ID formats, and OpenAPI schema. Frontend typecheck against fixtures.

**Done when:** backend and frontend agree on one shape and the coordinator
has reviewed it; dependent agents can implement without choosing API policy.

## P01 — Correct evaluator transitions and gap wording

**Depends on:** baseline; coordinate DTO assumptions with P00. **Audit:** T06.

**Own:** `api/app/services/tailoring_evaluation.py`,
`api/tests/test_tailoring_evaluation.py`, new evaluator fixtures if needed.

**Deliver:** distinguish internal keyword classifications from the permitted
pass-change kinds. Define semantic direction for every actual visibility-state
pair; preserve the comparison meaning and existing evaluation-v2 fields.
Replace overconfident qualification-gap copy with CV-visibility wording.
Preserve severity and genuinely actionable review items.

**Verify:** parameterized transition matrix, exact → variant/normalized,
unchanged states, keyword regressions, required conflicts, and missing evidence
wording. Run the focused evaluator suite.

**Done when:** valid input cannot generate an invalid pass-change enum, and
feedback does not claim the scanner established a candidate's true inability.

## P02 — Protect helper input and session identity

**Depends on:** baseline. **Audit:** T07/T10/T11.

**Own:** `tailoring-skill/skills/aergia-tailor/scripts/session.mjs`, existing
`tailoring-skill/tests/session.test.mjs`, new PTY harness if needed.

**Deliver:** parse and retain the URL session ID; validate exchange and context
IDs before exposing evidence. Implement non-echoing TTY and pipe input with
terminal restoration on errors/EOF/interruption. Treat preview 401/403/410 and
revoked/expired access as terminal. Preserve separate stale, preview-limit,
candidate-error, and transient transport handling.

This packet can retain the existing exchange payload until P08 adds v10's
required `session_id`; enforce returned ID consistency now. Add no credential
CLI flag or environment variable. Do not log remote bodies containing secrets.

**Verify:** real PTY capture and piped stdin, synthetic code absent from all
captured output, terminal restored, mismatched IDs expose no evidence files,
and access failures issue no subsequent render/submit request. Run Node tests.

**Done when:** each reproduced helper defect has a permanent regression.

## P03 — Add storage and the coordinated migration

**Depends on:** P00. **Audit:** T04/T05 and historical recovery in T01/T09.

**Own:** tailoring session/CV ORM definitions and new evaluation, preview
reservation, and replacement reservation models; model registration; one
new Alembic revision; new migration tests. No service behavior in this packet.

**Deliver:** the frozen P00 blueprint, partial uniqueness for blocking
sessions and pending reservations, immutable evaluation identity, PDF bytes
and digest storage, owner review storage, internal quota-counted provenance.
Migration reconciles duplicate active sessions, preserves draft CVs/results,
backfills normal counts, and grants no retrospective free allowance. Handle
existing protocols explicitly and retain legacy columns needed for reading.

**Verify:** migration from a fresh DB and a populated historical DB with
duplicate sessions, soft-deleted CVs, ready drafts, and counter discrepancies.
Exercise indexes through independent async sessions. Verify downgrade behavior
or document why backup restore is required for destructive reversal.

**Done when:** storage supports every frozen service contract without a second
agent inventing a column or migration. The coordinator reviews the SQL.

## P04 — Freeze useful evidence and allow the professional headline

**Depends on:** P00/P03. **Own:** context/normalization portions of
`api/app/services/tailoring.py`; `api/app/services/pdf.py`;
`api/app/document_schema/capabilities.py`; new context regression tests.

**Deliver:** immutable authoring snapshot, readable labeled source-CV
supplement, separate live target guard, and manifest-based PDF service entry
through the existing renderer. Avoid broad staleness on unrelated Library,
profile, or template updates. Preserve authoritative contact normalization
but allow profile `data.title`. Distinguish no-op saves from meaningful source
changes through P06's CV revision behavior.

**Verify:** blind-stage fixtures remain job-only; context includes CV-only
facts after release; frozen data and preview manifest survive unrelated
mutations; relevant source/job changes conflict; profile headline survives;
contacts remain server-owned; resolver stays pure. Coordinator runs codegen
and commits generated output if required.

**Done when:** authoring has the missing source information and a stable
snapshot, with precise guards against overwriting changed application work.

## P05 — Make sessions and preview selection reliable under concurrency

**Depends on:** P03/P04. **Audit:** T04/T05.

**Own:** session creation/exchange/evaluation/preview portions of
`api/app/services/tailoring.py`; reservation/preview adapters in
`api/app/routes/tailoring.py`; new concurrency test file. P03 owns schema fixes.

**Deliver:** DB-backed single active session, URL session-ID validation before
code consumption, reservation acquire/release,
lease fencing, immutable ledger selection, five-successful-preview budget,
private byte-identical replay, cleanup, and bounded expected-conflict codes.
Use separate short reservation transactions; no service commits or write
lock across rendering. Owner actions later use a separate evaluation path.

**Verify:** wrong-session code rejected without consuming it; barriers with
two real DB sessions for creation and reservation;
timeout retry; expired lease; late completion; render failure and release;
sixth successful preview; choosing any saved evaluation; byte-identical
replay; no evaluation JSON overwrite. Check route-owned transactions.

**Done when:** races neither create extra active sessions nor lose selectable
evaluations, exceed budget, or duplicate successful preview identity.

## P06 — Make replacement quota an atomic allowance

**Depends on:** P03 and P00 service interface. **Own:**
`api/app/services/quotas.py`, `api/app/services/cv.py`,
`api/app/services/application.py`, new quota regression tests. Do not edit
`tailoring.py`; expose the operations P07 will call.

**Deliver:** counted versus allowance CV creation/deletion, reservation and
transfer primitives, atomic counter updates without rolling back callers'
pending work, meaningful CV revisions, and guards on clone/manual-link/app
deletion. A no-op document save must not invalidate a source guard. Preserve
normal standalone limits and transaction ownership.

**Verify:** normal limit reached, eligible replacement allowed, first CV
still blocked, invalid/shared source denied allowance, clone requires slot,
manual-link conflict, app/source deletion cleanup, double delete and concurrent
transfer/release. Test pending unrelated writes survive quota operations.

**Done when:** at most one allowance exists per application and every entry
point preserves counter/provenance consistency. P07 can use public service
operations rather than bypassing quota checks.

## P07 — Reevaluate owner edits and recover lifecycle states

**Depends on:** P05/P06/P08. **Audit:** T01/T02/T09.

**Own:** owner review/submit/lifecycle portions of
`api/app/services/tailoring.py`; relevant tailoring routes; draft-context
adapter in `api/app/routes/cvs.py` if that is the current route module; new
owner lifecycle tests. Confirm the actual CV router path before assignment.

**Deliver:** separate immutable submission/current owner evaluation;
persisted-draft reevaluation; current render/contact basis; revision/hash-aware
accept; atomic replacement transfer; idempotent discard of missing/stale
drafts; deletion reconciliation; owner access after capability expiry; new
pending-draft context. Validate and store P08's advisory review during submit,
and mark it historical after owner edits. Keep legacy review readable.

Return expected stale outcomes normally so a 409 response can commit intended
reconciliation; preserve rollback for unexpected failures. Never mark a
review current solely because a result once existed.

**Verify:** every lifecycle case in plan §8 item 1; competing accept/reject/
delete/edit; changed render basis; false-positive “current” review; no source
and replacement source; capability scope cannot invoke owner endpoints;
permanent unmodified-v9 acceptance regression; report verdict stays advisory.

**Done when:** advertised owner editing can be accepted after reevaluation,
and no missing/stale/expired draft strands the application or quota.

## P08 — Add the portable independent PDF review workflow

**Depends on:** P00/P02/P05. **Own:** helper `scripts/session.mjs`; new
`scripts/fit-review.mjs`; new `references/independent-review.md`; helper
review/reservation tests; new `api/app/services/tailoring_fit_review.py` and
focused validation tests. P00 owns DTOs; P07 owns service integration.

**Deliver:** v10 exchange ID and reservation API integration; request identity
retained across preview retries; REVIEW package from selected immutable
attempt; allowlisted job/PDF/manifest export; bounded report reading and
in-memory freeze; exact selection/report binding; honest unavailable/explicit
skip behavior; advisory backend validation callable by P07. The host's skill
instructions request a fresh PDF reviewer; this helper does not hardcode a
vendor or launch a chat app itself.
Prefer frozen machine-readable error codes over message matching for v10
conflicts. A lease/in-progress conflict is not an instruction to repair CV text.

**Verify:** package field/file audit, no dossier/ideal/notes/scores/capability,
exact SHA over returned PDF bytes, stale report rejected, selecting an older
attempt, one review plus one optional follow-up, unavailable and generic
results accepted, retries preserve the frozen candidate/report, revoked
reservation/preview access is terminal. Run all helper tests and validator tests.

**Done when:** an agent host can perform a real independent assessment of the
actual selected PDF, with honest limitations and no favorable-verdict gate.

## P09 — Fix application navigation and asynchronous session state

**Depends on:** P00 contracts; independent of backend implementation.
**Audit:** T03. **Own:** `useTailoringSession.ts`,
`applications/pages/ApplicationDetailPage.tsx`, new hook/browser regressions.

**Deliver:** route ID as authority, full state reset, request generation guards,
poll cleanup/no overlap, stale response suppression, fresh prompt protection,
and suppression of unusable hydrated copy prompts. Keep public route adapters
and feature boundaries intact.

**Verify:** real hook mounted through a browser harness with mocked API;
A → B/404, late A GET/action, late latest response after start, unmount during
poll, and duplicate actions. Do not only test a pure helper mirroring code.

**Done when:** B cannot display or act on A's session and new one-time prompt
material cannot be overwritten by older hydration.

## P10 — Expose full review and owner recovery in the application panel

**Depends on:** P00/P09/P01; live verification waits for P07.
**Audit:** T08 plus frontend consequences of T01/T02/T09.

**Own:** `applications/components/detail/ApplicationCvPanel.tsx`; tailoring
presentation helpers; owner-action extension of `useTailoringSession.ts` and
`ApplicationDetailPage.tsx`; new frontend behavior fixtures/tests.

**Deliver:** separate scanner, fit-review, and notes sections; complete
expandable lists; visible review items; current/earlier/not-run review labels;
Reevaluate, version-bound Accept, Discard, and restart affordances. Prevent
duplicate actions, announce loading/errors accessibly, and hide invalid code
prompts. Use public tailoring exports for additional components.

**Verify:** keyboard access, narrow viewport, all review items reachable,
generic/unavailable verdicts, historical null fields, saved-versus-pending
revision, stale/deleted/expired cases, action races. Run lint/type/architecture
checks and targeted browser behavior tests.

**Done when:** the owner can see the actual complete feedback and resolve each
supported state without an unusable button or hidden required warning.

## P11 — Connect pending draft editing to its real application

**Depends on:** P00/P09; live verification waits for P07.

**Own:** `builder/hooks/useBuilderApplicationContext.ts`, builder header/page
wiring as needed, a feature-local pending-review hook if useful, and public
`features/tailoring/index.ts` exports. Coordinate header/page ownership before
splitting additional files. Do not change builder persistence internals
unless the coordinator explicitly assigns a necessary integration change.

**Deliver:** resolve owned pending-draft context through the frozen API, show
draft-specific scanner/review state, invalidate the current-review badge
after a real save, and wait for save completion before reevaluation. Preserve
the existing linked-CV scanner path for ordinary CVs.

**Verify:** unlinked pending draft versus unrelated/unlinked ordinary CV;
linked source scan never masquerades as draft scan; failed/pending save;
draft delete during editing; no cross-feature deep import or second renderer.

**Done when:** Open/Edit draft is a coherent continuation of owner review,
and the builder evaluates the CV actually being edited.

## P12 — Revise skill prose, guides, and packaging

**Depends on:** P00 for prose; P08/P07 for final packaging and accuracy.
**Audit:** T12. **Own:** SKILL.md, relevant existing writing/CV references,
`tailoring-skill/AGENTS.md`, `tailoring-skill/README.md`,
`docs/matching-and-tailoring.md`, focused skill identity/bundle assertions.
Read `api/app/services/tailoring_skill.py` and `api/Dockerfile`; change either
only if packaging verification exposes a concrete missing asset/path.

**Deliver:** concise ideal-first/inference-friendly author guidance; useful
examples; bounded factual check preserving framing; visibility-aware scanner
guidance; purposeful iteration; fresh reviewer invocation/fallback; honest
reporting and candidate selection; v10 local contract guide and architecture
documentation. Keep reusable details in references. No obsolete indexing
story, extra inference audits, automatic ranking, or mandatory positive review.

**Verify:** every referenced asset is in the deterministic installable ZIP;
bundle header/helper/backend protocol agree; Docker contains new files;
stage-zero restrictions and secrets policy remain accurate. Existing dynamic
bundle discovery already includes scripts/references: do not rewrite it just
to add files. Coordinator executes semantic author/reviewer checks in P13.

**Done when:** a fresh installed agent can follow the complete workflow using
the shipped skill alone. Personal installed skills remain untouched.

## P13 — Integrate, inspect semantic output, and run release gates

**Depends on:** all previous packets. **Owner:** coordinator, with later Luna
subagents for bounded read-only audits and synthetic author/reviewer runs.

**Own:** integration fixtures, approved contract wiring, generated outputs,
final protocol constants/prompts, and tracker transitions. Avoid speculative
cleanup outside the feature.

**Deliver:** integrated feature branch, all audit fixes reproduced as fixed,
coherent v10 cutover/migration/bundle, three synthetic baseline-versus-revised
comparisons, fresh PDF reviews, and an execution report with actual evidence.
Check every plan §8 behavior and resolve concrete failures. Do not substitute
the old defect-asserting temporary tests for regressions.

**Verify:** required repository gates in the implementation plan; full backend
suite, smoke, web checks, Node tests, codegen, tracker rebuild/validate. Inspect
the complete diff and verify no credentials/capabilities/real CV evidence
entered fixtures or reports. Preserve documented pre-existing warnings.

**Done when:** every mapped bug and new behavior has evidence, all required
gates pass, no packet's promised work is left implicit, and the implementation
is ready for the normal regular-merge cutover. Record incomplete work honestly
if a required external constraint remains; do not call the feature complete.

## Audit finding ownership

| Finding | Implementation packet | Final verification |
| --- | --- | --- |
| T01 deleted draft | P06/P07 | Lifecycle and quota API regressions |
| T02 edited draft | P07/P10/P11 | Save → reevaluate → accept browser/API flow |
| T03 wrong application | P09 | Real React/browser navigation and late-response tests |
| T04 lost preview history | P03/P05/P08 | Independent-session concurrency and retry tests |
| T05 duplicate active sessions | P03/P05 | Barrier creation test and DB invariant |
| T06 keyword transition | P01 | Full transition matrix |
| T07 echoed code | P02 | PTY and pipe capture |
| T08 hidden review items | P10 | Complete accessible owner report |
| T09 rolled-back stale state | P07 | Persisted conflict/recovery API test |
| T10 wrong session code/link | P02/P05/P08 | Client checks and pre-consumption server check |
| T11 preview auth continues | P02/P08 | Terminal preview/reservation access tests |
| T12 obsolete docs | P12 | Docs match integrated source and migration |

P13 verifies the entire mapping. Closing a bug requires integrated behavior
and actual test evidence, not just a packet's implementation claim.

## Tracker registry

All entries below are PLANNED. Existing audit bugs remain open.

| Scope | Tracker entry |
| --- | --- |
| Feature | [FEAT-01M3T3Z9FBY8M2EAXQVC5AZMZP](../../tracker/features/FEAT-01M3T3Z9FBY8M2EAXQVC5AZMZP-tailoring-v10-relevance-independent-pdf-review-and-recoverable-drafts.md) |
| P00 | [TASK-01M3T3Z9HZNMHFY5Z02XR2BV9P](../../tracker/tasks/TASK-01M3T3Z9HZNMHFY5Z02XR2BV9P-tailoring-p00-freeze-v10-contracts-and-compatibility.md) |
| P01 | [TASK-01M3T3Z9MMJ8BP58FGCNM38PJ5](../../tracker/tasks/TASK-01M3T3Z9MMJ8BP58FGCNM38PJ5-tailoring-p01-correct-evaluator-transitions-and-gap-wording.md) |
| P02 | [TASK-01M3T3Z9Q62N779WSBJEXP542D](../../tracker/tasks/TASK-01M3T3Z9Q62N779WSBJEXP542D-tailoring-p02-protect-helper-input-and-session-identity.md) |
| P03 | [TASK-01M3T3Z9SRGX5XM9032WDB8D3P](../../tracker/tasks/TASK-01M3T3Z9SRGX5XM9032WDB8D3P-tailoring-p03-add-storage-and-coordinated-migration.md) |
| P04 | [TASK-01M3T3Z9W8FW2TXV33PCRFWRXF](../../tracker/tasks/TASK-01M3T3Z9W8FW2TXV33PCRFWRXF-tailoring-p04-freeze-evidence-and-allow-professional-headline.md) |
| P05 | [TASK-01M3T3Z9YM588VYKT4282WW963](../../tracker/tasks/TASK-01M3T3Z9YM588VYKT4282WW963-tailoring-p05-make-session-and-preview-concurrency-reliable.md) |
| P06 | [TASK-01M3T3ZA14R7SWNCJD9R7MV21Z](../../tracker/tasks/TASK-01M3T3ZA14R7SWNCJD9R7MV21Z-tailoring-p06-implement-atomic-replacement-quota-allowance.md) |
| P07 | [TASK-01M3T3ZA3PCSBCRQS405B0HC78](../../tracker/tasks/TASK-01M3T3ZA3PCSBCRQS405B0HC78-tailoring-p07-reevaluate-owner-edits-and-recover-lifecycle-states.md) |
| P08 | [TASK-01M3T3ZA65G24SYN8WASENH9CQ](../../tracker/tasks/TASK-01M3T3ZA65G24SYN8WASENH9CQ-tailoring-p08-add-portable-independent-pdf-review.md) |
| P09 | [TASK-01M3T3ZA8J0528X078077XQK22](../../tracker/tasks/TASK-01M3T3ZA8J0528X078077XQK22-tailoring-p09-fix-application-navigation-and-session-races.md) |
| P10 | [TASK-01M3T3ZAAZ09JEGQHAN6PRJAJE](../../tracker/tasks/TASK-01M3T3ZAAZ09JEGQHAN6PRJAJE-tailoring-p10-expose-complete-review-and-owner-recovery.md) |
| P11 | [TASK-01M3T3ZADCFTVD5Z2FJ8BNWPTE](../../tracker/tasks/TASK-01M3T3ZADCFTVD5Z2FJ8BNWPTE-tailoring-p11-connect-pending-draft-builder-context.md) |
| P12 | [TASK-01M3T3ZAFS5CF37MWHNVVQK0XC](../../tracker/tasks/TASK-01M3T3ZAFS5CF37MWHNVVQK0XC-tailoring-p12-revise-skill-guidance-docs-and-packaging.md) |
| P13 | [TASK-01M3T3ZAJ7KWQ3HZ6SDCQH7E6Y](../../tracker/tasks/TASK-01M3T3ZAJ7KWQ3HZ6SDCQH7E6Y-tailoring-p13-integrate-semantic-checks-and-release-gates.md) |
