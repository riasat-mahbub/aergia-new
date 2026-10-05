# Tailoring v10 execution state

Updated 2026-10-05 following two server interruptions. This is an execution
record; the implementation plan and frozen contract remain authoritative.

Branch: `feature/tailoring-v10`. Latest reviewed commit: `7dee878`.
Cutover into `master` has not happened. No production database was migrated.

## Reviewed packets

P00 contracts, P01 evaluator, P02 helper input protection, P03 storage and
migration, P04 frozen evidence and headline, P06 quota, and P09 navigation
were reviewed and committed. P12 prose was committed; packaging is pending.
P10 review panel and start recovery are committed, with both mounted Chromium
harnesses passing.
P05 session/preview concurrency is committed, with 14 focused regressions
passing. Target rows are locked and revalidated after rendering in the short
completion transaction; PostgreSQL races have not been exercised.

The resumed focused backend run passed 77 tests across evaluator, contracts,
context, quota, and migration, 60 renderer tests, and 12 real Chromium PDF
readability tests. This is not the complete release gate.

## Work in progress

- P08: independent-review helper, reference, reservation integration, and
  backend fit-review binding validator are assigned to a Luna 6 max agent.
- P07 follow-up: remove the old submit increment of `attempts`; successful
  preview completion now increments it atomically.
- P11: partial builder context and persistence hooks. Finish header/page
  wiring, save/reevaluate synchronization, mounted browser regressions, and
  navigation/unmount/dirty-edit completion guards.
- P13: root updated `test_tailoring.py` for v10 exchange, reservations,
  frozen Library evidence, and revision-bound acceptance. It awaits P07.

Agents use Luna 6 max, isolated file ownership in the shared checkout.
Children do not write tracker or git history. Agent sessions disappear on a
server restart; inspect disk and live agents before resuming a packet.

## Remaining dependency order

1. Finish/review/commit P05 and P11 independently.
2. P08: v10 helper reservations and independent PDF review package/report;
   new backend fit-review validator. Own helper scripts and new validator.
3. P07: submit, owner reevaluation/accept/discard/status lifecycle and draft
   context. Integrate P06 quota and P08 validator; serialize core service edits.
4. Finish P12 packaging and precise recovery documentation.
5. P13 full backend, smoke, web, Node, codegen, tracker, visual and semantic
   checks; resolve failures; truthful tracker closure; regular merge cutover.

Synthetic job-only author workspaces were recreated at
`/tmp/aergia-tailoring-v10-semantic`; baseline software blind stage has started.
Candidate evidence has not yet been exposed to that author. Temporary
setup/render scripts are `/tmp/prepare_tailoring_semantic.py` and
`/tmp/render_tailoring_semantic.py`. Each arm must complete the blind ideal
before evidence is copied in. Six fresh author contexts and six fresh PDF
reviews are required; revised runs allow one consequential follow-up each.
If temporary files disappear, recreate synthetic fixtures, never real data.

Known baseline warnings: seven tracker forks, lint warnings, Python asyncio
deprecations. Two existing Alembic schema drifts are unrelated. Chromium
checks may require permitted sandbox escalation. Personal installed skills
remain untouched. Final gates and small semantic comparison are still pending.
