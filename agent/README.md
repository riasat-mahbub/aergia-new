# Aergia tailoring skill assets

This directory is not an Aergia CLI and is not an agent runtime. It contains
the skill instructions and local validation tools used by an already-installed
coding agent such as Codex, Claude Code, or OpenCode.

The user starts from Aergia Web. Aergia creates a short-lived session and
shows a copyable prompt. The user pastes that prompt into their coding agent;
the installed `aergia-tailor` skill exchanges the one-time code, downloads
only the session evidence, creates a local patch, validates it, and submits it
to the server.

The skill must never ask the user to install or use a normal Aergia access
token. If the skill is missing or incompatible, it must ask for approval before
installing or updating from the official Aergia source.

## Layout

- `skills/aergia-tailor/SKILL.md` — provider-neutral workflow instructions.
- `tools/jd-check.mjs` — local JD requirement guardrail.
- `tools/verify-cv-facts.mjs` — local prose fact guardrail.
- `tools/validate-patch.mjs` — dependency-free local protocol guardrail.
- `THIRD_PARTY_NOTICES.md` — attribution for adapted safety tooling.

The evidence packet is authoritative input. The local agent may write only the
patch output; it must not edit the source evidence files.
