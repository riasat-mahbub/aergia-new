# Aergia tailoring skill assets

This directory contains a self-contained skill for coding agents such as
Codex, Claude Code, or OpenCode. The installable directory is
`skills/aergia-tailor/`; copying or extracting that one directory into an
agent's user-level skills directory includes every required script and schema.

The user starts from Aergia Web. Aergia creates a short-lived session and
shows a copyable prompt. The user pastes that prompt into their coding agent;
the installed `aergia-tailor` skill exchanges the one-time code, downloads
only the session evidence, creates a local patch, validates it, and submits it
to the server.

The skill must never ask the user to install or use a normal Aergia access
token. A tailoring prompt includes the same-origin official bundle URL. If the
skill is missing or incompatible, the coding agent must ask for approval before
downloading or updating it.

## Layout

- `skills/aergia-tailor/SKILL.md` — provider-neutral workflow instructions and
  required skill metadata.
- `skills/aergia-tailor/references/` — versioned evidence and patch JSON
  Schemas plus fixtures.
- `skills/aergia-tailor/scripts/` — the in-memory session helper and
  dependency-free local JD, patch, and fact guardrails.
- `tests/` — Node's built-in tests for the local safety tools.
- `THIRD_PARTY_NOTICES.md` — attribution for adapted safety tooling.

The browser entrypoint for a session remains `/agent/tailor/$sessionId`; the
directory name `tailoring-skill/` describes the local assets and does not
change that public URL.

The evidence packet is authoritative input. The Library is a bounded snapshot,
not a relevance-filtered shortlist, so the local agent has broad discretion to
select evidence and compose a better document. The packet's `cv` is the linked
CV for optional evidence; `target_cv` is a fresh scaffold. A successful
submission creates a new CV and leaves the linked source CV untouched.

The protocol supports targeted prose edits as well as complete section
creation, replacement, removal, and ordering. This freedom remains bounded by
renderer compatibility, immutable profile identity, evidence-backed candidate
facts, and auditable reasons/citations for structural decisions.
