# Local-agent CV tailoring

## Goal

Add a local-agent tailoring flow without running generative AI on Aergia or
storing provider credentials on the Aergia server.

The first implementation is a protocol, not an LLM feature. Aergia creates a
short-lived, narrowly scoped tailoring session; the web application shows a
copyable prompt and an installed coding-agent skill exchanges the session
code, downloads a sanitized evidence packet, and submits a structured patch.
The server remains the final validator and applies changes atomically.

## Architectural decisions

- The boundary is specifically generative AI: generative inference and its
  credentials remain under the user's control outside Aergia production.
- Existing server-side GLiNER requirement extraction remains allowed. Phase 1
  uses the application's stored requirement snapshot for scoring rather than
  extracting the job description again.
- The agent never receives a normal Aergia access or refresh token and never
  receives database access.
- The first target is an application's existing linked/generated CV. Arbitrary
  CV selection is deferred.
- The agent receives task-scoped JSON evidence, not a production database
  dump. Source files are evidence and are not agent-editable.
- No database synchronization, chat UI, generic agent framework, or automatic
  agent adapter is part of the first version.

## Phase 1 — Protocol spike

No Career-Ops, LLM, or agent reasoning is required.

### Flow

```text
web creates tailoring session and shows a skill prompt
  → installed coding-agent skill exchanges one-time code
  → skill fetches sanitized evidence packet
  → skill submits fixed test patch
  → server validates session, target, and operation
  → server applies patch atomically
  → server evaluates stored requirements against the updated CV
```

### Minimal session API

Proposed boundaries (names may follow the existing route conventions):

- Browser-authenticated `POST` to create a session for an owned application
  with a linked CV.
- Code exchange endpoint that returns a short-lived capability limited to the
  exact session/application/CV.
- Capability-authenticated evidence `GET`.
- Capability-authenticated patch `POST`.

The session record should contain the user, application, CV, expiry, a hash of
the exchange secret, status, and bounded attempt/submission state. Never log
the code or capability. Use rate limits and a one-time exchange; avoid making
the code itself a reusable normal bearer token.

### Protocol v1

The first patch supports only:

- `replace_rich_text`: replace a plain-string description or summary on an
  existing CV target identified by explicit section and entry IDs. The server
  may retain `replace_description` as a compatibility alias for the fixed
  protocol fixture.
- `report_gap`: record an unsupported job requirement for the submission; it
  does not modify the CV or score directly.

The Phase 1 description operation should reject structured rich text rather
than expanding the spike into a rich-text migration. All fields, IDs, lengths,
operation counts, and gap text are bounded by the server.

The evidence packet contains only the tailoring task data needed by the fixed
patch test: job data, current CV data, relevant profile/Library data, and
protocol metadata. It must omit authentication data, unrelated user records,
secrets, and internal database metadata.

### Stored-requirement scoring

Add a relevance helper that accepts the already-persisted application
requirements and calls the deterministic evaluator. Do not route Phase 1
through the current refresh paths that call `extract_requirements()` again.
The server ignores any client-provided score or relevance result.

### Acceptance test

An integration test must prove:

```text
create session
  → exchange code
  → fetch evidence
  → submit fixed patch
  → apply description change
  → recompute relevance from stored requirements
  → return updated score and gap state
```

Failure at any validation step must leave both CV and application unchanged.

## Phase 2 — Patch semantics, concurrency, and policy

Extend the closed operation set with:

- `rewrite_rich_text`
- `remove_bullet`
- `reorder_bullets`
- `remove_entry`
- `reorder_entries`
- `add_library_entry`

Use explicit IDs rather than array positions. Library additions carry a
server-owned Library entry ID; the server copies the authoritative row and
assigns fresh CV IDs.

Add:

- a protected-field policy for profile, experience, education, project,
  skills, language, certification, and research data;
- a base CV hash/revision captured with the evidence packet;
- stale-patch rejection with no partial write;
- entry-level provenance and an allowed evidence scope for each rewrite;
- atomic validation, application, and relevance persistence.

Protected facts include identities, employers, titles, institutions, dates,
degrees, certifications, publication metadata, URLs, and verified numeric
claims. Descriptive prose may be edited only within the later fact-validation
boundary. Styles, customizations, IDs, and unrelated metadata are not patchable.

Define strict JSON Schema contracts in `contracts/` with protocol version 1,
closed operation discriminators, maximum sizes, and valid/invalid fixtures.
Server and local skill validators must test the same fixtures.

## Phase 3 — Career-Ops safety tools

Adapt the useful behavior from Career-Ops after the patch protocol is stable:

- JD requirement-section detection, noise filtering, skill extraction, and
  explicit inconclusive results;
- fact checks for metrics, percentages, currencies, counts, employer/title
  claims, technology claims, markup normalization, and number normalization;
- tailoring instructions that require full-JD/CV/Library review, supported
  evidence selection, gap reporting, patch validation, and fact validation.

Adapt the source model to Aergia's CV AST and Library provenance rather than
copying assumptions about markdown files. Add shared fixtures for rich text,
numeric normalization, false employer/title/technology claims, and unrelated
Library evidence. The server must perform the final important checks itself;
local validation is advisory.

Retain the Career-Ops MIT copyright and license notice in a third-party
attribution file and preserve source headers for substantially adapted code.

## Phase 4 — Agent workspace and installed skill

Have the installed skill create a temporary, permission-restricted workspace containing:

```text
workspace/
├── SKILL.md
├── source/
│   ├── job.json
│   ├── cv.json
│   ├── library.json
│   └── protected-facts.json
├── output/
│   └── tailoring-patch.json
└── tools/
    ├── jd-check.mjs
    ├── verify-cv-facts.mjs
    └── validate-patch.mjs
```

Support Codex manually first by printing instructions for `codex .`; do not
spawn or automatically select an agent. Document how Claude Code and OpenCode
can be used with the same workspace. Source files should be read-only to the
agent process where practical, and cleanup must run on success, failure, and
interruption. Validation and any repair attempts must have a bounded limit.
There is no Aergia CLI to install, invoke, or maintain.

## Phase 5 — UI lifecycle and hardening

Add the user-facing lifecycle around the protocol:

- session expiry and cancellation;
- retry/restart after failure;
- stale-CV handling;
- success result and applied changes;
- reported gaps;
- before/after relevance and score explanation;
- safe copy/display of the skill prompt, session link, and one-time code.

Add end-to-end coverage for session ownership, replay, expiry, rate limits,
malformed patches, protected-field attempts, stale CVs, atomic rollback,
rich-text facts, and successful relevance refresh.

## Effort

| Phase | Estimate |
|---|---:|
| Protocol spike | 2–3 days |
| Patch semantics, concurrency, and policy | 2–3 days |
| Career-Ops adaptation and fact fixtures | 2–4 days |
| Agent workspace and skill | 1–2 days |
| UI lifecycle, tests, and hardening | 2–3 days |
| **Total** | **9–15 focused engineer-days** |

A useful internal prototype should be possible after the first 4–6 days,
provided it remains limited to a linked CV, two operations, fixed test data,
and no LLM invocation.

## Open implementation checks

- Confirm the exact evidence DTO and ensure it cannot expose `extra_metadata`,
  credentials, or unrelated application data.
- Decide the final route names and capability exchange format.
- Add a dedicated stored-requirements relevance path before implementing the
  Phase 1 acceptance test.
- Keep the current relevance/extractor worktree changes isolated while adding
  the protocol.
- Run the focused protocol tests independently before attempting the full
  smoke gate, because the current environment has known database/test-runtime
  instability.

## Full implementation execution plan

The prototype is the protocol boundary. The remaining work should be delivered
in independently testable slices, with each slice preserving the rule that
generative inference and provider credentials stay outside Aergia production.

### Phase 0 — Make the verification baseline trustworthy

Do this before widening the patch contract. The current environment cannot run
the async SQLite integration tests because `aiosqlite.connect()` hangs under the
available Python runtime, and the repository's documented schema-codegen script
is absent. A schema-heavy change should not proceed while those gates are
ambiguous.

Tasks:

1. Establish and document a supported Python test runtime (prefer the declared
   Python 3.12 path) and a reproducible async SQLite setup.
2. Make `api/tests/test_tailoring.py` run from a fresh database, then add the
   full protocol flow to the normal backend test command.
3. Restore or replace the in-tree Pydantic-to-TypeScript codegen check before
   changing rich-text models. Generated frontend types must remain derived,
   never hand-edited.
4. Record the existing full-frontend lint baseline separately from new work;
   changed files must introduce no new lint errors.

Exit gate: the fixed-patch create → exchange → evidence → submit → apply →
score flow passes on a fresh database, and schema/codegen checks are usable.

### Phase 2 — Expand patch semantics safely

#### Contract and targeting

Keep protocol version 1 for additive operations and expose the server's
supported operation set in the evidence packet. Bump the protocol only for a
breaking wire-shape change. The installed skill must choose only operations
advertised by the server, so a published skill can work against an older
deployment.

Replace implicit array paths with explicit targets:

- `rewrite_rich_text`: section ID, entry ID, and an allowlisted field (`description`
  or `summary`) containing canonical `RichTextBlock[]`.
- `remove_bullet`: section ID, entry ID, rich-text field, and stable block/item
  IDs.
- `reorder_bullets`: section ID, entry ID, field, and the complete ordered list
  of stable item IDs.
- `remove_entry`: section ID and entry ID.
- `reorder_entries`: section ID and the complete ordered list of entry IDs.
- `add_library_entry`: authoritative Library entry ID plus source row ID, with
  the target section inferred and checked from the Library kind.

The current AST has rich-text blocks/items but no stable IDs for bullet items.
Add canonical IDs with a compatibility normalizer/backfill before enabling
bullet operations. Require exact permutations for reorder operations; reject
duplicates, missing IDs, unknown IDs, and array-index-only targets.

#### Protected policy

Create one server-owned policy table/module that maps section type and field to
`protected`, `editable prose`, `reorder/remove`, or `not patchable`. Reject
disallowed paths rather than silently dropping them. At minimum:

- protect names, employers, titles, institutions, dates, locations, degrees,
  certifications, publication metadata, URLs, verified metrics, counts,
  percentages, currencies, and structured technology claims;
- permit only descriptive prose rewrites in explicitly allowlisted fields;
- permit removing/reordering existing entries or bullets without changing their
  facts;
- permit Library insertion only by copying a server-fetched authoritative row;
- reject styles, customizations, IDs, arbitrary metadata, profile identity
  fields, and unknown section types.

The policy must be exercised against every current section type, including
`profile`, `experience`, `education`, `skills`, `projects`, `languages`,
`certifications`, `research`, and `extras`.

#### Concurrency and provenance

Add a monotonic CV revision and a canonical SHA-256 snapshot hash. The evidence
packet and patch carry the base revision/hash. Submission uses a compare-and-
swap update and rejects a stale CV with no CV, relevance, or audit mutation.
The hash should cover the authoritative CV document state relevant to the
operation, not a client-provided timestamp.

Do not use `CV.extra_metadata` as provenance; the existing code treats that JSON
as user-editable. Add a server-owned provenance representation (a small table
or protected JSON owned by the tailoring service) recording source kind,
Library entry/row IDs, target field paths, and the submitted evidence scope.
Every rewrite must declare evidence references. The server resolves each
reference to the current user's CV/Library snapshot and rejects references
outside the packet or references whose Library source changed after evidence
creation.

Submission order:

```text
validate protocol/session/base snapshot
  → copy CV sections
  → apply all operations to the copy
  → validate canonical AST and protected policy
  → run server fact checks
  → compare-and-swap CV revision
  → persist provenance, gaps, before/after relevance, and session result
```

All writes must be one transaction. A failed operation, fact check, stale
revision, or relevance calculation leaves the previous CV and score intact.

Exit gate: every operation has contract fixtures, server unit tests, stale and
concurrent-submit tests, protected-field rejection tests, copy-on-write tests,
and a full rollback test.

### Phase 3 — Add Career-Ops safety tools

Use Career-Ops as a source of safety behavior, not as a data model. Its JD gap
checker is explicitly zero-LLM and distinguishes `existing`,
`supportedByResume`, and `gap`; it also reports inconclusive extraction rather
than treating an empty result as a clean check. Its fact verifier normalizes
markup and numbers before checking metrics, employer/title, and technology
claims. These behaviors are the useful parts to adapt. [JD gap checker](https://raw.githubusercontent.com/santifer/career-ops/main/jd-skill-gap.mjs),
[fact verifier](https://raw.githubusercontent.com/santifer/career-ops/main/verify-cv-facts.mjs)

Tasks:

1. Add a local Node tool that converts `job.json` and the canonical CV AST into
   the JD checker input, preserving the raw JD and the inconclusive states.
2. Add an Aergia AST adapter that flattens rich text without treating styles or
   IDs as evidence. Keep Library entry ID and source row ID alongside every
   extracted field.
3. Add the fact verifier locally with Aergia source inputs, then implement the
   important server-side checks in Python or another server-native module. Do
   not make the server trust a local tool result or spawn an agent to validate.
4. Define a language-neutral fact-result contract with `pass`, `fail`, and
   `inconclusive` findings. A local pass is advisory; an inconclusive or failed
   server check blocks submission.
5. Add fixtures for changed percentages, currencies, counts, employer/title or
   technology claims, rich-text markup, Unicode/number normalization, supported
   paraphrases, and unrelated Library evidence.
6. Add an attribution file containing the Career-Ops MIT notice and retain
   required source notices for substantially adapted code. The upstream license
   requires the copyright and permission notice in copies or substantial
   portions. [MIT license](https://raw.githubusercontent.com/santifer/career-ops/main/LICENSE)

The agent must still read the complete raw JD. The JD checker is a guardrail,
not a replacement for model reasoning or Aergia's stored requirement analysis.

Exit gate: local and server fixtures agree on supported/unsupported facts; a
false numeric or employer claim is rejected before any database write; an
inconclusive JD/fact result is visible and cannot be mistaken for a pass.

### Phase 4 — Build the installed-skill workspace

The copied web prompt is the handoff. The installed `aergia-tailor` skill
exchanges the code, fetches evidence, creates the workspace, and guides the
coding agent through validation and submission. The workspace contains
`SKILL.md`, read-only `source/` JSON files, writable
`output/tailoring-patch.json`, and local `tools/` wrappers. `SKILL.md` must
require full-JD/CV/Library review, evidence selection, gap reporting, patch
validation, fact validation, repair, and submission only after all checks pass.

Do not spawn Codex, Claude Code, OpenCode, or any other agent. Codex support is
manual first: print the workspace path and `codex .`. Document the equivalent
manual invocation for Claude Code and OpenCode against the same workspace.

Use a 0700 temporary workspace, restrictive source/output permissions, bounded
file sizes and repair attempts, no secrets in filenames/logs, and cleanup on
submit, expiry, cancellation, failure, and interruption. The session capability
must not be written into `SKILL.md` or source files. The UI and skill must
clearly show expiry and provide a fresh-session retry path.

Exit gate: a human can run the workspace with Codex, write a patch manually,
run the tools, repair a deliberately invalid patch within the limit, and submit
only the valid result. No provider SDK or credential is present in `agent/` or
the server.

### Phase 5 — Finish UI lifecycle and hardening

Add a browser-authenticated session status/cancel path and make the UI model
the state machine (`created`, `exchanged`, `submitted`, `cancelled`,
`expired`). Show the one-time code and copied skill prompt once, an expiry countdown, and
clear retry instructions without displaying the capability.

Persist a bounded tailoring result containing:

- before and after relevance snapshots using the same stored requirements;
- score/coverage delta and matched/missing requirement summary;
- applied operation summary and provenance references;
- reported gaps and validation warnings;
- failure/stale/cancel reason where applicable.

Handle stale CV, changed JD/requirements, changed Library source, expiry,
replay, cancellation, rate limits, malformed JSON, protected-field attempts,
and server fact failures as distinct user-visible outcomes. Never show a
success state until the transaction and relevance update have committed.

Add backend, skill-tool, frontend, and live acceptance coverage for the complete flow.
The most valuable live test uses a fixed patch and a fresh database; the LLM
workspace is tested separately with a fixture patch, so CI never needs model
credentials.

Exit gate: the UI can start, monitor, cancel, retry, and complete a tailoring
session; the result shows before/after relevance and gaps; all failure paths
leave authoritative data unchanged.

## Delivery order and review boundaries

Deliver four reviewable implementation changes after the baseline gate:

1. **Patch contract and safety boundary** — operations, stable rich-text IDs,
   policy, revision/hash, provenance, server transaction, and backend fixtures.
2. **Safety tooling** — Career-Ops adaptations, Aergia AST adapters, server
   fact checks, attribution, and shared fixtures.
3. **Workspace/skill** — `SKILL.md`, tools, cleanup, bounded repair, and
   Codex-first documentation. Do not add an Aergia CLI.
4. **Lifecycle/UI hardening** — session state/cancel/retry, result persistence,
   stale handling, before/after relevance, end-to-end tests, and release docs.

Each change must pass its own focused tests and leave the fixed protocol flow
working. Do not combine the first real LLM-assisted run with a schema or
security migration; validate the deterministic path first.

## Revised estimate

| Work | Estimate |
|---|---:|
| Verification baseline and integration harness | 0.5–1 day |
| Patch semantics, policy, concurrency, provenance | 3–4 days |
| Career-Ops adaptation, server checks, fixtures | 3–4 days |
| Workspace, skill, manual agent workflow | 2–3 days |
| UI lifecycle, audit/result state, tests, hardening | 2–3 days |
| **Total robust implementation** | **10.5–15 focused engineer-days** |

The original 9–15 day estimate remains reasonable if the baseline repair is
small and provenance is implemented as a compact server-owned representation.
The lower bound is not realistic if rich-text IDs, server-side fact checks, or
stale-write testing are deferred.
