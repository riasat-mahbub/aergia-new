# Requirement-based CV relevance and one-time tailoring

Tracker: `FEAT-01M155ZDP74JTYPFYK8W289QB4`

## Objective

Replace the current `keyword-v1` frequency-based relevance score with a
cheap, deterministic requirement-coverage baseline. Use the existing Library
as the source of reusable content during generation, then materialize the
selected content into a standalone editable CV.

This plan does not introduce live CV-to-Library references. Generated CVs are
one-and-done snapshots: Builder edits can continue indefinitely, but no edit
automatically regenerates or reselects CV content.

## Implementation status — 2026-08-28

The first implementation pass is complete for the core V1 path. The API now
ships `requirement-v1` alongside the legacy reader-compatible keyword helpers:
atomic extraction, taxonomy aliases, explicit years/degree checks, SQLite
FTS5/BM25 lexical fallback, bounded fuzzy spelling fallback, strongest-evidence
explanations, weighted coverage, and greedy Library selection. Generation and
recomputation use the new contract, while the existing generated CV remains a
materialized snapshot. The Builder drawer renders requirement-level evidence.

FTS5 is currently built in memory per scoring operation because Library content
is stored as JSON and the relevance service is intentionally pure; this avoids
a second persisted index that could drift from the canonical Library. The
existing recompute endpoint is the explicit migration path for legacy
`keyword-v1` application results; no automatic historical backfill is run.

## Product invariants

- Generation reads the current job, profile, and Library once.
- Generation creates a normal editable CV and records source provenance.
- A generated CV is never automatically rewritten by Library or job changes.
- Application/job edits can recalculate relevance against the current CV.
- Builder saves recalculate relevance without changing CV content selection.
- Existing/manual CVs remain scoreable without Library provenance.
- A future new tailoring run must create a new CV/version explicitly.
- V1 uses no LLMs, embeddings, or transformer models.

## Delivery protocol

For every implementation step:

1. Confirm the step's tracker context with `tracker search`, `tracker affects`,
   and `tracker validate`.
2. Implement only that step and preserve unrelated worktree changes.
3. Run focused tests and static checks.
4. Commit the implementation separately using the step's commit message.
5. Update the parent tracker entry:

   ```bash
   tracker update FEAT-01M155ZDP74JTYPFYK8W289QB4 --status IN_PROGRESS \
     --note "<step result and verification>"
   tracker rebuild && tracker validate
   ```

6. Commit the tracker update separately with a `tracker:` commit message.

Do not squash implementation and tracker commits. The feature merges to
`master` with a regular merge commit, consistent with repository policy.

Because the current worktree contains unrelated application, renderer, and UI
changes, implementation should begin from an isolated branch or a clean
worktree containing only the intended baseline. Do not use reset/checkout to
discard the existing changes.

Execution note: this pass was performed in the existing dirty worktree and no
commit was created, because several in-scope files already contained unrelated
user changes. Before merging, stage the requirement-specific hunks in the
commit sequence below (or transplant the work into an isolated branch), then
create the separate tracker commits. This preserves the repository's regular
merge/no-squash policy without bundling unrelated work.

## Step 0 — Record the contract and baseline

Commit: `docs: plan requirement-based relevance and tailoring`

Work:

- Record this plan and the parent tracker feature.
- Capture current `keyword-v1` behavior and representative failure fixtures.
- Decide the supported deterministic JD grammar and scoring weights.
- Define the compatibility policy for existing application rows.

Verification:

- `tracker rebuild && tracker validate`
- Existing focused relevance and application tests remain unchanged and green.

## Step 1 — Add requirement contracts and deterministic extraction

Commit: `feat: add requirement-v1 job requirement extraction`

Files in scope:

- `api/app/schemas/application.py`
- `api/app/services/relevance.py`
- new taxonomy/alias data under `api/app/`
- `api/tests/test_relevance.py`

Work:

- Add typed requirement and evidence shapes.
- Extract atomic requirements from role text, headings, bullets, and prose.
- Detect hard skills/concepts, responsibilities, required/preferred status,
  years-of-experience expressions, and degree-level constraints.
- Handle negation such as “not required.”
- Avoid arbitrary sliding n-grams as primary requirements.
- Assign stable IDs and deterministic weights.

Verification:

- Parser fixtures cover headings, bullets, negation, duplicate concepts,
  technical punctuation, required/preferred sections, and malformed input.
- `pytest api/tests/test_relevance.py -q` from the API environment.

## Step 2 — Index and match Library content

Commit: `feat: add deterministic Library requirement matching`

Files in scope:

- `api/pyproject.toml`
- `api/app/models/library.py`
- `api/app/services/library.py`
- `api/app/services/relevance.py`
- `api/app/services/relevance_taxonomy.py`
- `api/tests/test_library.py`
- `api/tests/test_relevance.py`
- `api/tests/test_requirement_relevance.py`

Work:

- Normalize Library rows and individual bullets into searchable documents.
- Build an in-memory SQLite FTS5/BM25 document index from the canonical
  Library snapshot for each scoring operation; keep the service pure and avoid
  a second persisted index for JSON payloads.
- Match in this order: exact canonical concept, alias, structured constraint,
  FTS/BM25 free text, then bounded RapidFuzz spelling/format variation.
- Ensure row/bullet provenance is retained for evidence.
- Avoid making the relevance score depend on Library presence or frequency.

Verification:

- FTS5 ranking and document construction tests.
- BM25 ordering and fuzzy thresholds are deterministic.
- `ruff check .` and focused Library/relevance tests pass.

## Step 3 — Implement coverage scoring and greedy content selection

Commit: `feat: score requirement coverage and select tailored content`

Files in scope:

- `api/app/services/relevance.py`
- `api/app/services/application.py`
- `api/tests/test_relevance.py`
- `api/tests/test_applications_generation.py`

Work:

- Find the strongest evidence for each requirement.
- Calculate weighted requirement coverage rather than keyword frequency.
- Expose required coverage separately from preferred coverage.
- Prevent repeated bullets covering the same requirement from inflating score.
- Rank candidate Library rows/bullets by marginal uncovered requirement weight.
- Use deterministic greedy selection with section, length, and page-fit limits.
- Retain existing profile handling and editable materialization.

Verification:

- Matching one important requirement beats matching several duplicates.
- Missing required requirements cannot be hidden by generic matches.
- Evidence includes requirement, source row, field path, method, and snippet.
- Selection tie-breaking is stable across runs.

## Step 4 — Integrate one-time generation and score lifecycle

Commit: `feat: integrate one-time tailored generation lifecycle`

Files in scope:

- `api/app/services/application.py`
- `api/app/services/cv.py`
- `api/app/routes/applications.py`
- `api/app/routes/cvs.py`
- `api/app/models/application.py`
- `api/app/schemas/application.py`
- `api/tests/test_applications.py`
- `api/tests/test_applications_generation.py`

Work:

- Persist `requirement-v1` results and generation provenance.
- Calculate requirements for new/edited applications.
- Calculate initial relevance during one-time generation.
- Keep the existing generated-CV conflict behavior.
- Recalculate against the current CV after Builder saves.
- Recalculate after job edits without rewriting the CV.
- Do not propagate Library edits into existing generated CVs.
- Keep old `keyword-v1` records readable and use the explicit relevance
  endpoint as the opt-in recompute path; do not silently rewrite history.

Verification:

- Generation happens once and produces a standalone editable snapshot.
- Builder edits alter relevance only after save.
- Job edits change score but not CV sections or generation provenance.
- Library edits do not alter existing CV content.
- Applications without a generated CV have an explicit “not evaluated” state,
  not an ambiguous zero.

## Step 5 — Replace the relevance UI

Commit: `feat: show requirement-level application evidence`

Files in scope:

- `web/src/lib/api/applications.ts`
- `web/src/lib/store/applicationStore.ts`
- `web/src/components/applications/RelevanceDrawer.tsx`
- `web/src/components/applications/applicationPresentation.ts`
- `web/src/pages/ApplicationDetailPage.tsx`
- `web/src/pages/ApplicationsPage.tsx`
- `web/src/pages/BuilderPage.tsx`
- related frontend tests

Work:

- Replace matched/missing keyword chips with requirement-level rows.
- Show required/preferred state, coverage, strongest evidence, and match method.
- Keep list filtering and score display compatible with the new result.
- Make recomputation state and errors visible.
- Preserve the one-time generation UX; do not add automatic regeneration.

Verification:

- Frontend tests cover empty, pending, calculated, stale/error, and fully
  evidenced results.
- `npm run test -- --run`, `npm run lint`, and `npm run build` pass.

## Step 6 — Benchmark and hardening

Commit: `test: verify requirement-based relevance flow`

Work:

- Add representative job/CV/Library benchmark fixtures with expected
  requirements, evidence, scores, and selected content.
- Use the existing relevance endpoint for explicit legacy recomputation; a
  batch backfill remains an opt-in follow-up rather than running during deploy.
- Add live smoke coverage for generation, evidence, Builder edit, and job edit.
- Run the complete backend/frontend/smoke gate.

Verification:

```bash
cd api && pytest
cd api && ruff check .
cd web && npm run test -- --run
cd web && npm run lint
cd web && npm run build
cd web && npm run codegen:check
./dev.sh --smoke
tracker rebuild && tracker validate
```

Commit the final tracker closeout separately:

```bash
tracker update FEAT-01M155ZDP74JTYPFYK8W289QB4 --status DONE \
  --note "Requirement-v1 relevance and one-time tailoring verified by ..."
tracker rebuild && tracker validate
git add tracker/ && git commit -m "tracker: close requirement-based relevance feature"
```

## Commit sequence

The intended history is:

1. `docs: plan requirement-based relevance and tailoring`
2. `feat: add requirement-v1 job requirement extraction`
3. `tracker: record requirement extraction progress`
4. `feat: add deterministic Library requirement matching`
5. `tracker: record Library matching progress`
6. `feat: score requirement coverage and select tailored content`
7. `tracker: record coverage selection progress`
8. `feat: integrate one-time tailored generation lifecycle`
9. `tracker: record generation lifecycle progress`
10. `feat: show requirement-level application evidence`
11. `tracker: record requirement evidence UI progress`
12. `test: verify requirement-based relevance flow`
13. `tracker: close requirement-based relevance feature`

If a step requires a follow-up fix, keep the fix and its verification in a
new focused commit rather than amending unrelated history. Merge the finished
feature branch into `master` with a regular merge commit; do not squash.

## Out of scope

- Live CV-to-Library references.
- Automatic regeneration after Builder, job, profile, or Library changes.
- LLMs, embeddings, or transformer models.
- A “generate new tailored version” workflow.
- Replacing the HTML-first renderer.
