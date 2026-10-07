# Tailoring v10 execution state

This is the historical October 5 checkpoint. Current verification and final
selection evidence are in the [October 7 execution report](2026-10-07-tailoring-v10-execution-report.md).
Do not interpret the remaining-work list below as current status.

Updated 2026-10-05 following two server interruptions. This is an execution
record; the implementation plan and frozen contract remain authoritative.

Branch: `feature/tailoring-v10`. Latest reviewed commit: `e62e869`.
Cutover into `master` has not happened. No production database was migrated.

## Reviewed packets

P00 contracts, P01 evaluator, P02 helper input protection, P03 storage and
migration, P04 frozen evidence and headline, P06 quota, and P09 navigation
were reviewed and committed. P12 packaging is committed: deterministic ZIP,
extracted helper, referenced assets, and Docker filesystem layout checks pass.
P10 review panel and start recovery are committed, with both mounted Chromium
harnesses passing.
P05 session/preview concurrency is committed, with 14 focused regressions
passing. Target rows are locked and revalidated after rendering in the short
completion transaction; PostgreSQL races have not been exercised.
P08 is committed: backend fit-review validator with 11 focused tests, and the
portable helper/reference with all three Node test files passing (0 failures,
25.743 seconds). The helper requires a matching report or honest unavailable /
explicit-user-skip reason; the backend still accepts absent reports as Not run.

The resumed focused backend run passed 77 tests across evaluator, contracts,
context, quota, and migration, 60 renderer tests, and 12 real Chromium PDF
readability tests. This is not the complete release gate.

## Work in progress

- P07: owner lifecycle is assigned after the reviewed validator handoff;
  this changes only scheduling, with disjoint P08 helper ownership.
- P07 follow-up: remove the old submit increment of `attempts`; successful
  preview completion now increments it atomically.
- P11 is committed with actual pending-owner context, draft-specific scanner,
  serialized save/reevaluate, revision checks, and navigation fences. Eleven
  mounted browser groups pass. Root screenshot inspection caught a mobile
  header overflow missed by the harness; a corrective layout and overflow
  assertion are assigned before final verification.
- P13: root updated `test_tailoring.py` for v10 exchange, reservations,
  frozen Library evidence, and revision-bound acceptance. It awaits P07.

Agents use Luna 6 max, isolated file ownership in the shared checkout.
Children do not write tracker or git history. Agent sessions disappear on a
server restart; inspect disk and live agents before resuming a packet.

## Remaining dependency order

1. Finish/review/commit the P11 mobile correction and P07 lifecycle.
2. P07 integrates P06 quota and the verified P08 validator; core service
   ownership remains serial. All P08 checks still precede the release gate.
3. Verify the integrated P12 recovery documentation against final behavior.
4. P13 full backend, smoke, web, Node, codegen, tracker, visual and semantic
   checks; resolve failures; truthful tracker closure; regular merge cutover.

Synthetic job-only author workspaces were recreated at
`/tmp/aergia-tailoring-v10-semantic`. Both software arms completed authoring,
canonical rendering, and fresh PDF reviews. Both were judged tailored; this
does not demonstrate a reduction in model bias. The revised software author
kept its candidate after checking the conditional recommendations against the
dossier. Analysis candidates have rendered; collaboration authoring is pending.
Revised software resumed in a fresh Luna conversation from completed artifacts
after a server restart; the blind gate was preserved on disk. Temporary
setup/render scripts are `/tmp/prepare_tailoring_semantic.py` and
`/tmp/render_tailoring_semantic.py`. Each arm must complete the blind ideal
before evidence is copied in. Six fresh author contexts and six fresh PDF
reviews are required; revised runs allow one consequential follow-up each.
If temporary files disappear, recreate synthetic fixtures, never real data.

Root resumed checks: eight historical/contract tests and two deterministic ZIP,
extracted-helper, and Docker filesystem layout checks passed. The original API
integration now includes real submitted-draft expiry/review/restart coverage;
four integration tests pass against the working owner lifecycle. The production
frontend build and owner-panel browser harness pass. Final smoke/full backend
gates still await the lifecycle packet and mobile correction.
The architecture fixture suite, generated-schema check, and skill metadata
validator also passed. Root review requested submit fixes for final target
revalidation, seeded owner-PDF pruning, full replay identity, and guarding
active stale drafts against accumulating replacement allowances.

Known baseline warnings: seven tracker forks, lint warnings, Python asyncio
deprecations. Two existing Alembic schema drifts are unrelated. Chromium
checks may require permitted sandbox escalation. Personal installed skills
remain untouched. Final gates and small semantic comparison are still pending.
