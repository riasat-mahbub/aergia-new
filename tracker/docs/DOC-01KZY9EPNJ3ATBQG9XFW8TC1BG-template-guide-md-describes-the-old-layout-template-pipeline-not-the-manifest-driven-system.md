---
SCHEMA: 3
FORMAT: project-tracker
ID: DOC-01KZY9EPNJ3ATBQG9XFW8TC1BG
TYPE: doc
STATUS: DONE
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - DOC-01KYZ1XGE9FSXGDWY3T3SZHKDT
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-13T19:26:45.426144+00:00'
UPDATED_AT: '2026-08-13T19:26:45.426144+00:00'
---

# TEMPLATE_GUIDE.md describes the old layout_template pipeline, not the manifest-driven system

## Background

## Background

TEMPLATE_GUIDE.md describes the old layout_template pipeline, not the manifest-driven system

The current `TEMPLATE_GUIDE.md` was written for the old user template
system (HTML-only templates with `{{zone_id}}` placeholders). The
manifest-driven pipeline has replaced this, but the guide hasn't been
updated. It references deprecated concepts:
- `layout_template` instead of manifest
- Zone configuration at upload time (now handled by the visual wizard)
- Old customization panel behavior

### What It Should Cover

- Manifest JSON schema reference
- Visual wizard flow (Step 1-4)
- Generated HTML/CSS from manifest
- Asset loading

*Migrated from SCHEMA 2 entry 006-template-guide-rewrite.md (status OPEN) on 2026-08-01.*

## Investigation

## Decision

**Closed via consolidation.** Rather than rewriting `TEMPLATE_GUIDE.md`
in place, the relevant content (manifest JSON schema, top-level keys,
renderer cascade) was folded into a new top-level `README.md`. The
docs-audit plan (`docs/doc-audit-and-readme-plan.md`) justified the
move:
- `TEMPLATE_GUIDE.md` is one of three stale docs (`PLAN.md`,
  `PHASE_7_PROMPT.md`, `TEMPLATE_GUIDE.md`) that have been superseded
  by either per-feature tracker entries or the git log.
- A new contributor's first read is the README, not a top-level
  template guide. The manifest schema reference belongs at the top
  of the project's mental model, not in a separate file.
- The new README includes a manifest JSON example, the top-level
  keys, the closed-vocabulary tokens, and the renderer cascade —
  the same content the old guide had, updated for the current schema
  (closed vocabulary, `policy_overrides.by_type`, `entry_layout`,
  etc.).

## Implementation

Removed `TEMPLATE_GUIDE.md`, `PLAN.md`, and `PHASE_7_PROMPT.md` from
the repo root in the same commit. Created `README.md` (~250 lines)
with the consolidated template-authoring content. Updated
`AGENTS.md`'s "Important Files" table to drop the deleted entries
and point to the new README.

Commit: `docs: consolidate docs, add README`.

## Verification

- `git ls-files | grep -E 'PLAN\.md|TEMPLATE_GUIDE\.md|PHASE_7_PROMPT\.md'` → empty.
- `git ls-files | grep README\.md` → `README.md`.
- `README.md` renders the manifest schema section with the current
  closed-vocabulary tokens (`narrow | half | full | auto` for width,
  `none | tight | comfortable | loose | spacious` for padding,
  `compact | comfortable | minimal` for spacing).
- `AGENTS.md` "Important Files" table no longer references the
  removed docs; new row points to `README.md` as the project entry
  point.

## Follow-up

- The `docs/plans/<date>-*.md` plans remain — each one is a
  per-feature historical record (the work that landed in a specific
  commit chain). Keep them.
- The `tracker/docs/` folder now has only `DOC-01KZP94J0QZTXC48QP6M5CYPK9-regenerate-agents-md.md`
  (DONE) plus this entry (now DONE). No new doc entries needed
  unless the README itself needs to be regenerated through the
  regen process.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
