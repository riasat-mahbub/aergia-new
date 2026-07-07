---
SCHEMA: 3
FORMAT: project-tracker
ID: FEAT-01KZPHASE6STEP2
TYPE: feature
STATUS: IN_PROGRESS
SUMMARY: 'Per-instance SectionPolicy overrides — two instances of the same section type render differently.'
PRIORITY: High
SEVERITY: null
EFFORT: S
OWNER: riasat
CONFIDENCE: High
TAGS:
- phase-6
- policy
- per-instance
RELATIONS:
  part_of:
    - EPIC-01KZCCC3MTXDGPY31H06NFYP1Q
  supersedes:
    - FEAT-01KZPHASE6STEP1-phase-6-content-only-authoring
AFFECTS:
  files:
    - api/app/schema/models.py
    - api/app/services/renderer/resolve.py
    - api/app/services/renderer/policy.py
    - api/app/services/renderer/builders/__init__.py
    - api/app/services/renderer/builders/skills.py
    - web/src/components/customization/CustomizePanel.tsx
    - web/src/lib/validators/sections.ts
    - web/src/lib/sections/types.ts
    - web/src/pages/BuilderPage.tsx
    - web/src/generated/schema.ts
    - api/tests/test_resolve.py
    - api/tests/test_builders.py
LINKS:
  plan: local://phase-6-content-only-authoring-plan.md
CREATED_BY: riasat
UPDATED_BY: riasat
CREATED_AT: 2026-08-08
UPDATED_AT: 2026-08-08
---

# Phase 6 step 2 — Per-entry policy overrides

## Background

Phase 4 closed the manifest's design vocabulary to typed tokens. `SectionPolicy` is currently per-section-type — the resolver applies `manifest.policy_overrides.by_type[type]` on top of `SECTION_POLICIES[type]` in `api/app/services/renderer/policy.py:resolve_policy`. Two instances of the same section type (e.g. two "Skills" sections) render identically because the policy is keyed by type, not by instance.

The data layer already supports per-instance policy: `SectionInstanceStyle.policy: SectionPolicy | None` is on the wire (`api/app/schema/models.py:220`), and `build_section_style` in `api/app/services/renderer/builders/__init__.py:79-83` honours an explicit instance-level `policy` over the type default. The missing surface is the editor — the customize panel has a Section policy disclosure for skills_layout and show_title, but the writes flow through the per-section style axis and the round-trip is not exercised by tests.

## Investigation

- `SectionInstanceStyle.policy` exists at `api/app/schema/models.py:220`.
- `build_section_style` (`builders/__init__.py:52-91`) reads `instance_style.policy` first, falls back to `resolve_policy(type, manifest)` if absent.
- `resolve.py:resolve()` calls `resolve_policy(section.type, manifest_model)` at line 320, which sets `Section.policy` from the type default. With an instance policy on the wire, the builder's resolved policy already supersedes the type default because `build_document` reads `style.policy` (the resolved policy returned by `build_section_style`) and copies it onto the section before the resolver's pass.
- Wait — checking `resolve.py:resolve()` more carefully: it overwrites `section.policy` at line 320 with `resolve_policy(section.type, manifest_model)`. That happens AFTER the builder copies the resolved policy from `build_section_style`. So the resolver currently clobbers per-instance policies. This must change: when an instance policy is present, the resolver must respect it instead of re-applying the type default.

## Decision

Adjust the resolver to read the resolved policy from the build stage and not overwrite it. The cleanest path: pass `instance_policies: dict[str, SectionPolicy]` from the build stage into the resolver, and have the resolver use that when present, falling back to `resolve_policy(type, manifest)` otherwise. The build stage already has per-instance policy resolution at `build_section_style`; the resolver just needs to receive the result.

The customize panel already has a "Section policy" `<details>` group with `show_title` and `skill_variant` controls; those already write through `onUpdateStyle` → `handleUpdateStyle`. The only missing piece is a backend test that proves two instances of the same type can carry different policies and render differently. Once that test exists, the editor surface is complete.

## Implementation

- `api/app/services/renderer/resolve.py:resolve()` accepts a new optional `instance_policies` parameter (or reads it from the document AST — better, since it's already there as `section.policy` after the build stage).
- The resolver's policy-application step checks `if section.policy is not None: keep it; else: resolve_policy(type, manifest)` instead of always overwriting.
- Add tests in `api/tests/test_resolve.py` and `api/tests/test_builders.py` that exercise two skills sections with different `skill_variant` settings and assert the resolved policy differs.
- Frontend: verify `CustomizePanel.tsx`'s Section policy disclosure writes through the wire correctly (no change if so). If a policy field is set but `show_title` is the default, ensure `handleUpdateStyle` strips the empty value rather than overwriting the type default.

## Verification

```bash
cd api && pytest -q tests/test_resolve.py tests/test_builders.py
cd web && npm test -- --run src/components/__tests__/CustomizePanel.test.tsx
```

## Follow-up

None — this is the last editor-side behavior in the trimmed Phase 6 umbrella.
