# Tailoring v10 implementation plan

Date: 2026-09-30. Status: planned; implementation has not started.

Baseline: `04df13e`, the [tailoring audit](../tailoring-audit-2026-09-30.md),
and the subsequent discussion about inference, the ideal CV, and independent
PDF review. Recheck the checkout before execution; this is a design plan,
not a claim that the proposed APIs or files already exist.

## 1. Intended outcome

Produce a CV that makes a convincing connection to the target job, using
the candidate's actual experience and reasonable professional inference.
Keep the blind ideal CV stage. Add a fresh assessment of the actual PDF,
make owner edits reviewable, and fix every finding T01–T12 from the audit.

The ideal CV is a useful creative scaffold. Its effectiveness remains a
working hypothesis to check with representative examples; the implementation
must not quietly replace it with an evidence-first workflow.

### Authoring and review decisions

1. **Keep stage zero blind.** Expose only the existing allowlisted job fields
   and user instructions. The author writes a complete fictional
   `ideal-target.md` before the helper exposes candidate evidence.
2. **Provide better evidence afterward.** The dossier contains the profile,
   all Library history, and a clearly labeled readable source CV when one
   exists. CV-only details supplement the Library. Keep role and source
   boundaries clear; neither source wins conflicting fixed facts silently.
3. **Reconstruct for relevance first.** Carry over useful framing from the
   ideal CV through direct evidence, ordinary inference, transferable
   examples, and selective future-facing language. An incomplete dossier is
   not proof that a candidate lacks an ability.
4. **Check facts without flattening the prose.** A subsequent pass preserves
   the useful job connection while correcting or qualifying unsupported
   claims. Preserve employers, historical official titles, dates, degrees,
   certifications, identity, URLs, completed actions, and exact metrics.
   Do not introduce an exhaustive claim ledger or inference audit.
5. **Make iteration purposeful.** Review every canonical PDF. Use another
   preview when there is a meaningful improvement to make; remove any
   instruction requiring an arbitrary substantive second edit. Retain the
   five-preview budget and the one-page preference, allowing readable
   justified exceptions.
6. **Separate feedback purposes.** The scanner reports visible requirement,
   keyword, ATS, and parsing evidence. A fresh reviewer assesses whether the
   PDF reads as deliberately tailored. The owner makes the final decision.
7. **Keep all judgments advisory.** A low score, factual concern, or a
   reviewer verdict of `generic` does not automatically block acceptance.
   Mechanical validity, authorization, ownership, and version binding still
   protect the document being accepted.

Examples for the revised guidance:

| Sparse evidence | Useful framing | Unsupported extension |
| --- | --- | --- |
| Automated tests run through GitHub Actions | Automated testing and CI workflows | Enterprise release ownership or deployment metrics |
| A group project | Collaboration and coordination in that project | Management of a professional team or client delivery |
| Explaining an analysis to project partners | Communicating technical findings | Presenting to executive clients unless supplied |

Do not automatically turn reasonable supported inference into “willing to
learn.” Use future-facing language for actual growth areas, without implying
that the work was already completed.

## 2. Architecture and scope

Keep the existing AST → resolver → render model → Python HTML → Chromium
pipeline and Playwright singleton. React remains the editor. Preserve the
public `/agent/tailor/$sessionId` route and the same-origin Start gateway.
The scanner continues to assess the CV presented to it; this does not add
Library indexing, retrieval workers, opportunity ranking, or another renderer.

Use **protocol v10** for the changed authoring contract. Preserve historical
owner review for protocols 4–9. Keep `tailoring-evaluation-v2` and its existing
wire field names unless contract preparation discovers a genuine structural
incompatibility; wording and a corrected transition mapping do not need a
new evaluation version.

The independent reviewer is supplied by the installed agent host, or by an
explicit manual external review. This plan does not introduce a hosted model
provider, provider credentials, or backend calls to a chat service. The Luna
model setting in the execution packets is for implementation agents later;
it is not a product requirement for users' tailoring agents.

The following instructions currently forbid these changes and must be updated
as part of the authorized feature: `tailoring-skill/AGENTS.md` pins v9 and
forbids any additional review artifact or marker. Replace those restrictions
with a narrowly scoped advisory fit-review contract. Retain the prohibitions
on factual audit gates, token persistence, and automatic preview ranking.
Do not modify either personal skill installation under `~/.codex/skills`.

## 3. Contract to freeze before implementation

P00 must turn the decisions below into DTO definitions, fixtures, and an ADR.
Use the existing `/api/v1` prefix; the table omits it for readability. The
coordinator approves the contracts before dependent packets begin. An agent
must report a necessary contract adjustment instead of inventing a second
shape in its own subsystem.

| Surface | v10 decision |
| --- | --- |
| Code exchange | Require `session_id` alongside code and protocol. Verify it before consuming the one-time code. |
| Context | Retain `dossier`; include labeled source CV text there. Add `source_cv_revision: int \| null`. Return frozen templates, capabilities, scanner basis, and a stable `context_hash`. |
| Preview reservation | New capability-scoped `POST /tailoring/preview-reservations`, with `context_hash`, `candidate`, and UUID `request_id`. Return `reservation_id`, canonical `candidate_hash`, and `expires_at`. |
| Preview | Retain `POST /tailoring/preview`; require `reservation_id`. Return existing fields plus `pdf_sha256`. |
| Reservation release | Capability-scoped `POST /tailoring/preview-reservations/{reservation_id}/release`; idempotent release of an uncompleted reservation. |
| Submit | Retain the frozen candidate, `context_hash`, `evaluation_id`, and `candidate_hash`. Add nullable advisory `fit_review`. Absence means no review was recorded, never an implied success. |
| Owner status | Add `draft_review`, containing `state`, `cv_revision`, `candidate_hash`, `render_basis_hash`, current evaluation, warnings, and advisory review applicability. |
| Owner reevaluation | New authenticated `POST /tailoring/sessions/{session_id}/reevaluate`, with `expected_cv_revision`. Evaluate the persisted draft; return current owner review and canonical PDF. |
| Owner acceptance | v10 requires `expected_cv_revision` and `candidate_hash` from the current owner review. Keep legacy accept behavior for historical protocol rows. |
| Draft builder context | New authenticated `GET /cvs/{cv_id}/tailoring-context`; return only an owned pending draft's application/session identity, review state, and scanner context. Return 404 for ordinary CVs. |
| Expected conflicts | Preserve HTTP status meanings; add a bounded machine-readable `code` beside human-readable `detail`. Distinguish stale target, edited draft, preview in progress, preview limit, quota, and inactive capability. |

`draft_review.state` is `current`, `needs_reevaluation`, or `unavailable`.
It is separate from the existing session lifecycle status. Additive status
fields are optional for historical rows. Shared fixtures cover null source
CV, missing review, owner edits, and historical results.

### Independent fit review

Use a small `fit-review-v1` report. For a completed review, require:

- `evaluation_id`, `candidate_hash`, and `pdf_sha256` matching the selected
  immutable preview;
- `status: completed`, `mode: fresh_agent | manual_external`, and
  `verdict: tailored | partially_tailored | generic`;
- a short rationale; at most five strong connections, five weak or missing
  connections, and **three** recommended changes;
- bounded strings and arrays, with no arbitrary metadata or model secrets.

For `unavailable` or `skipped_explicitly`, require the same version binding
and a short reason; omit verdict and findings. Explicit skipping follows a
user instruction, not elapsed waiting time. If the host cannot delegate or
inspect PDFs, record `unavailable` and continue. Do not label the author’s
own assessment as independent. A missing report remains visibly “Not run.”

The helper exports a review package for an explicitly selected saved preview:
`candidate.pdf`, `job.json`, and a manifest with the three binding values.
`job.json` contains only company, role, and description. A separate reviewer
reference supplies the prompt. Exclude the dossier, ideal CV, author history,
application notes, scanner scores, source identifiers, and capabilities.
Use a separate review directory and a fresh conversation. File allowlisting
and fresh context establish workflow isolation; do not claim they are an OS
security sandbox when the host shares filesystem access.

The reviewer must inspect the PDF and answer:

1. Does this read as deliberately tailored to this job?
2. Which responsibilities are convincingly addressed?
3. Which connections are generic, weak, or missing?
4. What are the three highest-impact changes?

The author checks suggestions against the dossier and applies credible ones.
Plan one initial review and at most one follow-up after a consequential
revision. Reserve preview capacity for that revision where useful. The final
selection has a matching review or a recorded unavailable/explicit-skip
reason. The backend accepts an absent report but never invents one; helper
guidance and tests enforce honest workflow completion rather than a positive
verdict gate. Backend validation verifies report shape and version binding,
not the quality or claimed independence of the reviewer.

Keep `ideal-target.md` local. Introduce `REVIEW` and `output/fit-review.json`
only for this advisory workflow. On REVIEW, use `selection.json` to export
the corresponding immutable attempt, including its exact returned PDF bytes.
Freeze the selected report in memory with the submission payload. Reusing a
report for a different evaluation/PDF must fail even if filenames look alike.

## 4. Backend implementation decisions

### A. Frozen authoring context and relevant invalidation

Persist the complete authoring snapshot when the session is created: profile,
Library history, readable source CV, template manifests, capabilities, job
and instructions, and scanner interpretation. Build later context responses
from that snapshot rather than rereading mutable Library or template rows.

Separate its immutable digest from the **live target guard**: application
ownership, target job fields and user instructions, linked source CV identity
and meaningful document revision, and compatible renderer/scanner contract.
Ordinary unrelated Library, profile, or template edits do not invalidate an
in-flight authoring session. A changed job or replaced/edited linked CV does.
No-op saves should not increment meaningful CV revision.

Render author previews from the selected frozen manifest through the existing
pipeline. Add a manifest-taking service entrypoint; do not change the pure
resolver to read the database. Owner editing continues to use current
templates and current authoritative contact details. If their render basis
differs from the submitted preview, mark owner review as needing reevaluation
and visibly show the previous independent review as applying to an earlier
version. Do not present a stale PDF verdict as a verdict on the edited CV.

Allow candidate-authored profile `data.title` as the professional headline.
Keep CV list `title`, profile headline, and historical employment titles
distinct. Keep fixed identity/contact fields server-owned. Update the
capability vocabulary and any generated outputs through codegen.

### B. Session and preview concurrency

Add a database uniqueness invariant for one blocking session per owned
application (`created`, `exchanged`, `draft_ready`). Use short atomic inserts
or compare-and-swap updates, with savepoint handling for expected uniqueness
conflicts. A stale draft does not hold the active-session lock; quota rules
below still bound outstanding replacement drafts.

Replace mutable JSON evaluation history with immutable evaluation rows. A
reservation row records session, request UUID, canonical candidate hash,
lease deadline, state, and eventual evaluation identity. Enforce at most one
uncompleted reservation per session and at most five completed agent
evaluations. Concurrent requests receive a recoverable `preview_in_progress`
response rather than losing history or exceeding the budget. Successful
evaluations remain selectable regardless of response arrival order.

Reservation acquisition/release are separate short HTTP transactions. Never
hold a database write lock across Chromium or scanner work, and never call
`commit()` from a service. Set the lease to 120 seconds, capped by capability
expiry; allow a 90-second preview request timeout. Expired leases can be
reclaimed atomically. Fence late completions against their original lease.
Failed renders do not consume a successful-preview slot. Retries reuse the
same request/reservation identity and normalized candidate; altered input
with that identity is a conflict.

Store canonical candidate, scanner result, evaluation, render warnings,
PDF digest, and private PDF bytes for completed previews so a lost response
can be replayed with the same PDF bytes. Do not rerender and pretend a newly
generated PDF has the original digest. Bound storage to five evaluations per
session. On submission retain the selected PDF for pending owner review and
drop unselected PDF blobs; on terminal cleanup drop PDF blobs while retaining
the small binding records and reports. Add lazy cleanup for expired abandoned
sessions without adding a worker. Snapshot, evaluations, and PDFs are private
owner data and must not enter logs.

### C. Replacement draft quota

Keep the normal account limit unchanged. Permit **one pending replacement
allowance per application** when the source is an active, solely linked,
owned, quota-counted CV that will be replaced on acceptance. An application
without such a source uses a normal slot.

Use an internal database flag such as `CV.quota_counted`, plus a unique
replacement reservation keyed to the application and source CV. Do not encode
quota authority in user-editable metadata. Acceptance atomically retires the
old source and makes the replacement counted, leaving the total unchanged.
Rejection/deletion of an allowance draft does not decrement the normal count.
Cloning that draft requires a normal reservation.

Check all bypasses: ordinary CV creation, duplication, manual application
linking, source deletion, application deletion, stale sessions, and concurrent
accept/reject/delete. Manually linking a pending draft returns an actionable
conflict directing the owner to the review flow. A second pending replacement
cannot obtain another allowance: the owner first discards the earlier one.
Deleting the application cleans up its pending draft and reservation; it must
not turn into an unlimited free standalone CV. Fix quota reservation helpers
that roll back unrelated pending mutations. Route dependencies still own
commit/rollback; services only flush.

### D. Owner edits, acceptance, and recovery

Separate the immutable agent submission from the latest owner evaluation.
Evaluate the persisted draft, its current meaningful revision, target job,
authoritative identity/contact fields, and actual current render basis.
Publish the new PDF and scanner findings. Ordinary owner reevaluation does
not consume the agent's five-preview budget; rate-limit it as an owner action.
If contact normalization changes the persisted draft, save that normalization
and advance its meaningful revision atomically; return the resulting revision
and let the builder refresh it. Acceptance also checks that the live contact
and render basis still match the reviewed basis.
Prepare normalization in memory and render before the final conditional write;
do not hold a write lock during owner reevaluation either. If the persisted
revision changes during rendering, discard the computed result and return a
conflict rather than overwriting the newer edit.

An unchanged submission can start with a current owner review if its full
render basis matches. Editing or changing that basis makes it need
reevaluation. Accept only the exact reviewed revision/hash, with an atomic
guard on the application's expected source CV and job basis. Advisory
warnings and fit verdicts do not affect this guard. A racing edit produces an
actionable reevaluate response; do not silently accept an unreviewed revision.

Rejection/discard is idempotent when the draft has already been deleted.
Deletion reconciles the session and releases a reservation in the same
transaction. Stale drafts remain inspectable and discardable. Job or source
changes require discard/restart for replacement; do not silently rebase the
application target. Expiry ends agent access, not owner review of a submitted
draft. Terminal and missing-draft states cannot permanently block new work.

When reconciliation changes state, return a normal typed service outcome so
the route can return a 409 JSON response **without raising an exception that
rolls back the intended state change**. Retain rollback on unexpected errors.
Owner status also reconciles missing drafts and stale targets on a successful
response. Avoid scattered service commits as a workaround.

## 5. Scanner feedback and frontend behavior

Fix keyword transition classification without changing the permitted
`fixed`, `introduced`, `improved`, and `regressed` wire vocabulary. Exercise
all actual visibility-state pairs, especially exact → normalized/variant.

Replace claims of “genuine qualification gap” based solely on absent CV text
with “This CV does not demonstrate …”. Retain the existing bucket field
names; explain their scope in user-facing copy and author guidance. This
change must not make the scanner pretend it read the Library. Show required
conflicts, parsing issues, ATS warnings, and all evaluation review items.

In the frontend:

- Key state and request identity to the route's application ID; reset session,
  errors, prompt, timers, and pending actions on navigation. Ignore late
  responses from the previous application. Do not use a previous store
  application's ID as a fallback for the current route.
- Prevent old latest-session responses from replacing a freshly created
  session and its one-time prompt. A hydrated session with no code cannot
  offer a usable copy prompt. Handle polling overlap and action races.
- Show scanner feedback, independent fit review, and author notes as distinct
  sections. Label an absent review and a review of an earlier version clearly.
  Use expandable complete lists; summary limits must not hide the full report.
- Add owner reevaluation, revision-aware Accept, idempotent Discard, and
  actionable stale/expired/deleted recovery. Disable duplicate pending
  actions, provide accessible loading/error feedback, and refresh the current
  application after successful actions.
- Give an unlinked pending draft its real tailoring application context in
  the builder. Fetch through a feature public entrypoint. Saving an edit marks
  review stale; reevaluation waits for successful save and uses that revision.
  Do not show the linked source CV's scanner results as the draft's results.
- Keep existing editor preferences, routes, and normal CV controls unchanged.

## 6. Migration, compatibility, and rollout

Use one coordinated additive migration after the current Alembic head. Add
evaluation/reservation storage, owner-review fields, quota flags/reservations,
and partial uniqueness indexes. P03 owns all migration files. Verify against
fresh and populated databases using the repository's actual SQLite behavior;
do not assume foreign-key cascades run where connection settings disable them.

Before creating the active-session index, reconcile existing duplicates
deterministically: retain the newest `draft_ready` if present, otherwise the
newest active session; mark others stale and revoke agent access. Preserve
their CVs/results and owner discard paths. Existing CVs remain counted;
backfill counters from active counted rows. Do not retrospectively grant free
replacement allowances to historical drafts.

At cutover invalidate in-flight v9 `created`/`exchanged` capabilities with a
clear restart response. Preserve submitted historical drafts and legacy
owner endpoints, adding recovery where safe. Do not attempt to resume a v9
helper using the v10 DTO. Test legacy results with absent v10 fields.

Update backend protocol declarations, helper, frontend API/types and prompt,
bundle headers/tests, portable skill guides, and protocol documentation as one
release. Recheck skill bundle paths and Docker copying; extend the bundle to
include new review reference/helper modules. Do not manually edit generated
schema files. Existing personal installations are upgraded later by their
normal installation process.

The coordinator prepares one integration feature branch. Preserve unrelated
working-tree changes and the audit/tracker artifacts. Use a regular merge
commit into `master` as the cutover, after actual execution and verification.
No merge or deployment is part of creating this plan. Back up the database
before migration. After v10 writes exist, application rollback requires
restoring a compatible application/database pair; a source-code-only rollback
is not a recovery plan.

## 7. Execution with Luna 6 max later

See the [execution packets](2026-09-30-tailoring-v10-execution-packets.md)
for scope, owned files, dependencies, tests, and acceptance criteria.

- Do not start agents while preparing this plan.
- Later use `model: gpt-6-luna`, `reasoning_effort: max`, `fork_turns: none`.
  Give each agent its packet, the frozen contracts, relevant guide, tracker
  context, and the needed audit findings. Do not rely on this chat being inherited.
- Maximum concurrency: coordinator plus three subagents. Use fewer when
  dependencies or shared files require it. Do not let children spawn agents
  without coordinator scheduling.
- Prefer isolated worktrees after the baseline is safely captured. Integrate
  commits in dependency order. If using a shared tree, enforce the packet's
  file ownership strictly. Never have two agents edit `services/tailoring.py`,
  its router, the same migration, or `scripts/session.mjs` at once.
- The coordinator owns tracker transitions and integration checks. Agents
  report proposed tracker updates, changed files, exact commands/results,
  acceptance evidence, and remaining risks. They do not mark unresolved bugs
  done or rewrite tracker history.
- Keep each packet bounded. If a packet reveals additional work, split a
  follow-up with explicit ownership instead of expanding into another packet's
  files. Review changes at packet boundaries before starting dependents.

Suggested waves, respecting the three-child limit:

| Wave | Packets | Gate |
| --- | --- | --- |
| 1 | P00 contracts; P01 evaluator; P02 helper safety | Coordinator freezes contracts and reviews focused fixes. |
| 2 | P03 storage/migration; P09 frontend state | Schema/migration established; route races fixed independently. |
| 3 | P04 frozen context/headline; P06 quota; P12 prose/docs draft | Distinct file ownership; P12 stops before final packaging. |
| 4 | P05 session/preview ledger; P10 owner panel; P11 builder | Frontend works from frozen API fixtures; central backend edits are serial. |
| 5 | P08 independent-review helper | Reservation API ready; helper safety changes already integrated. |
| 6 | P07 owner lifecycle; finish P12 packaging/docs | Advisory validator exists; quota and preview work integrated. |
| 7 | P13 integration and semantic checks | All packets integrated; release gate and final audit. |

P12 is deliberately paused between prose/docs and packaging. Do not schedule
its packaging assertions before P08 establishes the actual shipped assets.
P10/P11 may use contract fixtures before P07; live integration waits for P07.

## 8. Verification and completion

Promote the synthetic audit reproductions into permanent regression tests
that assert **correct behavior**. Some `/tmp` audit tests currently assert the
defect; passing those unchanged does not prove a fix. Do not depend on those
temporary files surviving until execution.

Required behavior coverage:

1. T01/T02/T09: edit → save → reevaluate → accept; racing edit rejected;
   delete → discard → restart; stale target persists and can be discarded;
   expiry after submission still permits owner review; v9 unchanged acceptance.
2. T03: A → B navigation, B has no session, late A responses, pending A
   actions, overlapping polls, and late hydration cannot affect B or erase a
   new prompt. Run a real React/browser reproduction.
3. T04/T05: simultaneous session creates yield one active row; preview
   reservations, timeout retries, expired leases, late completion, sixth
   preview, submit replay, and cleanup never lose evaluations or double count.
4. T06/T08: all keyword transition pairs produce valid schemas; complete
   review items are accessible; wording accurately describes CV visibility.
5. T07/T10/T11: actual PTY and piped code input cannot echo secrets; restore
   terminal state on EOF/interruption; wrong link/code session is rejected
   before consuming/exposing evidence; preview 401/403/410 is terminal.
6. Snapshot/headline: source-CV-only facts appear after the ideal gate;
   unrelated Library/profile/template edits do not alter frozen authoring
   data; relevant target/source changes fail safely; headline survives while
   contacts stay authoritative; changed owner render basis invalidates review.
7. Quota: at the normal limit replacement succeeds, first-CV creation still
   fails; accept/reject/delete/clone/manual-link/application deletion and
   races preserve counters and cannot accumulate allowance drafts.
8. Fit review: package contains only allowlisted files/fields; reviewer
   report binds to exact canonical bytes; old report cannot follow a new
   selection; unavailable/explicit skip/missing review are honest; `generic`
   remains advisory; edited owner version loses the current review badge.
9. Migration/bundle: populated duplicate/historical sessions migrate without
   deleting CVs; no missing new asset; protocol headers and helper agree.

Also run a small semantic check with **synthetic** incomplete dossiers for
three roles: software/CI, analytical communication, and collaborative project
work. Capture the baseline skill and references from `04df13e` before prose
changes. Use the same model, dossier, job, templates, and canonical renderer
for both arms. Compare those v9 prompts with the revised workflow in fresh
author contexts (six runs total), using a synthetic fixture harness rather
than trying to exchange v9 capabilities with the new server. Preserve the
blind stage in the harness.

Schedule six initial fresh PDF reviews: three assessments of the baseline
outputs and three reviews within the revised workflow. The latter feed the
author's normal improvement step. Allow at most three additional follow-up
reviews, one per revised case, when the chosen final version changes. Inspect
the final chosen PDFs in the coordinator's comparison. Keep orchestration
within the three-child limit;
do not have authors spawn reviewers while all slots are occupied.

Record specificity, convincing job connection, ordinary inference retained,
unsupported fixed facts introduced, and the usefulness of reviewer changes.
Use human-readable evidence and a coordinator review; do not pretend exact
string tests establish prose quality. This small check informs prompt tuning,
not a statistically validated claim about model bias. Tune only to resolve
observed failures, then stop optional testing.

Final required repository gates:

```bash
./dev.sh --smoke
(cd api && .venv/bin/pytest)
(cd web && npm run lint && npm run typecheck && npm run architecture:test)
(cd web && npm run architecture:check && npm run codegen:check)
node --test tailoring-skill/tests/*.test.mjs
tracker rebuild && tracker validate
```

Run these commands from the repository root. The
full backend suite remains required: the audit ran focused subsets. Existing
lint warnings and seven tracker fork warnings are known baseline observations;
record actual final results and do not hide new failures among them. The smoke
may need local network permission in a restricted execution environment.

Completion means all T01–T12 fixes and new workflow behaviors are implemented,
contracts/migrations/bundle/UI agree, semantic examples have been inspected,
required gates pass, and tracker records contain truthful verification. It
does not mean every reviewer must give a favorable verdict.
