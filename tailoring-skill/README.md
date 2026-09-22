# Aergia tailoring skill assets

This directory contains a self-contained skill for coding agents such as
Codex, Claude Code, or OpenCode. The installable directory is
`skills/aergia-tailor/`; copying or extracting that one directory into an
agent's user-level skills directory includes every required script and schema.

The user starts from Aergia Web. Aergia creates a short-lived session and
shows a copyable prompt. The user pastes that prompt into their coding agent;
the installed `aergia-tailor` skill exchanges the one-time code, downloads
only the session context, creates a complete candidate, previews it, and
submits it to the server for user review.

The skill must never ask the user to install or use a normal Aergia access
token. A tailoring prompt includes the same-origin official bundle URL. If the
skill is missing or incompatible, the coding agent must ask for approval before
downloading or updating it.

## Layout

- `skills/aergia-tailor/SKILL.md` — provider-neutral workflow instructions and
  required skill metadata.
- `skills/aergia-tailor/references/` — versioned context and candidate JSON
  schemas plus fixtures.
- `skills/aergia-tailor/scripts/` — the in-memory session helper and a
  dependency-free local candidate shape check.
- `tests/` — Node's built-in tests for the local safety tools.
- `THIRD_PARTY_NOTICES.md` — attribution for adapted safety tooling.

The browser entrypoint for a session remains `/agent/tailor/$sessionId`; the
directory name `tailoring-skill/` describes the local assets and does not
change that public URL.

New sessions use tailoring protocol v5. Aergia returns the authoritative
scanner-derived `TailoringEvaluation`; the agent supplies composition and an
unscored hash-bound editorial review. There is no local numeric critique gate.
Reasonable technical inferences remain allowed in the user-reviewed draft,
while explicit user corrections and prohibitions remain authoritative.

The context is authoritative read-only input. The Library is a bounded
snapshot, not a relevance-filtered shortlist, so the local agent can select
rows and compose a document from scratch. `previous_cv` is optional context;
an accepted submission creates a new CV and leaves the linked source CV
untouched until the user reviews the draft.
