# Local-agent CV tailoring

## Goal

Add a local-agent tailoring flow without running generative AI on Aergia or
storing provider credentials on the Aergia server.

The first implementation is a protocol, not an LLM feature. Aergia creates a
short-lived, narrowly scoped tailoring session; a local CLI exchanges the
session code, downloads a sanitized evidence packet, and submits a structured
patch. The server remains the final validator and applies changes atomically.

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
web creates tailoring session
  → CLI exchanges one-time code
  → CLI fetches sanitized evidence packet
  → CLI submits fixed test patch
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

- `replace_description`: replace a plain-string description on an existing CV
  entry identified by explicit section and entry IDs.
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
Server and CLI validators must test the same fixtures.

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

## Phase 4 — Agent workspace

Have the CLI create a temporary, permission-restricted workspace containing:

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

## Phase 5 — UI lifecycle and hardening

Add the user-facing lifecycle around the protocol:

- session expiry and cancellation;
- retry/restart after failure;
- stale-CV handling;
- success result and applied changes;
- reported gaps;
- before/after relevance and score explanation;
- safe copy/display of the CLI command and one-time code.

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
