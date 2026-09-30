# Aergia tailoring skill

This directory contains a self-contained skill for installed coding agents
such as Codex, Claude Code, and OpenCode. Install or copy
`skills/aergia-tailor/` into the agent's user-level skills directory. The
browser entrypoint remains `/agent/tailor/$sessionId`.

The protocol v10 helper exchanges the URL-bound one-time code for a scoped,
in-memory capability. It first exposes only the whitelisted job object so the
agent can write a complete fictional `output/ideal-target.md`. After that
blind stage, it exposes the frozen dossier, including the profile, Library
history, and any readable source CV. The source CV is supplementary evidence
and is not exposed before the ideal target is complete.

The agent writes a complete candidate, previews it through Aergia's canonical
renderer and scanner, and edits when a meaningful improvement remains. Each
preview freezes the server's canonical candidate and exact PDF. Up to five
successful previews are available; submission explicitly selects one by
evaluation ID and candidate hash. The user's page and content preferences
guide the final choice.

For an optional advisory fit review, the helper exports the selected PDF,
`job.json` with only the company, role, and description, and a binding
manifest. A fresh host-delegated reviewer inspects that package using
`skills/aergia-tailor/references/independent-review.md`. The report is bound
to the selected PDF and does not gate submission. When delegation or PDF
inspection is unavailable, the agent records that limitation honestly.

The server owns validation, candidate normalization, rendering, scanner
findings, and submission binding. A successful submission creates an
unlinked draft for the authenticated user to review; it does not replace the
application's current CV. Never request a normal Aergia access or refresh
token, persist the scoped capability, or edit source CV and Library records.
