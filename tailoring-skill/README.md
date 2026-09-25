# Aergia tailoring skill assets

This directory contains a self-contained skill for coding agents such as
Codex, Claude Code, or OpenCode. The installable directory is
`skills/aergia-tailor/`; copying or extracting that one directory into an
agent's user-level skills directory includes every required script and schema.

The user starts from Aergia Web. Aergia creates a short-lived session and
shows a copyable prompt. The installed skill exchanges the one-time code,
checks the persistent candidate index, retrieves bounded composition context,
creates a complete candidate, previews it, and submits an unlinked draft for
user review. The browser entrypoint remains `/agent/tailor/$sessionId`.

New sessions use protocol v8. Every successful candidate preview receives a
unique evaluation ID, and the helper stores reviewed attempts for explicit
selection. The deterministic candidate index is updated
with Library mutations. Semantic propositions are cached per source and are
refreshed only when a source fingerprint or extraction contract changes. A
job-blind worker receives only a bounded stale-source batch. If refresh fails,
tailoring continues from deterministic facts and current Library narratives.

The linked-CV scanner remains the sole source of application Job Fit. A
tailoring preview has temporary scoring, and submitting a draft does not
change the application's linked CV. Only user acceptance links the draft and
starts the normal application scan lifecycle.

The writer starts from target priorities, uses the bounded retrieval context
and original narratives to infer and reframe candidate capabilities, creates
the complete CV holistically, and makes useful revisions from scanner/PDF
diagnostics. CandidateEvidence is a retrieval aid, not a whitelist. The helper
submits the selected evaluated candidate directly for user review.

The skill must never ask the user to install or use a normal Aergia access
token. It keeps the scoped capability in memory only.
