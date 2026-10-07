# Tailoring v10 execution report

Implementation follows the [approved plan](2026-09-30-tailoring-v10-implementation.md),
[packets](2026-09-30-tailoring-v10-execution-packets.md) and
[frozen contract](../tailoring-v10-contract.md). Implementation and synthetic
authors/reviewers used Luna 6 with max reasoning; the coordinator reviewed,
integrated and verified their work in a shared checkout with file ownership.

Baseline: `04df13e`. Current integrated implementation: `dda4cc7`.
Final historical-discard follow-up and merge cutover are pending at this checkpoint.
No deployment, production database migration or personal skill installation
was performed. All test databases and candidate/job evidence are synthetic.

## Delivered behavior

- Retained the job-only ideal CV stage, then released a full frozen dossier
  including the labeled source-CV supplement. Guidance encourages useful
  professional inference and transferable framing, with one bounded correction
  of fixed facts and completed-work claims. Professional headlines remain
  author-controlled; direct identity and contact fields are normalized by the server.
- Replaced compulsory pass counts with purposeful iteration. Five successful
  previews remain the agent limit; failures and owner reevaluations do not spend
  that budget. Immutable preview records retain candidate identity, selected
  PDF bytes and SHA; retry and submit replay preserve that exact selection.
- Added the portable independent review package and closed advisory report.
  A fresh reviewer receives only the selected PDF, three job fields and three
  binding fields. The helper requires a completed report or honest unavailable /
  explicit-user-skip reason. Backend absence is displayed as Not run. Generic
  verdicts remain permissible and do not gate submission or acceptance.
- Added saved-draft reevaluation, exact revision/hash acceptance and live
  contact/template/render-basis checks. The immutable submission is kept apart
  from current owner review. Editing makes the earlier PDF review historical.
- Added atomic replacement quota accounting, pending-draft recovery after
  capability expiry, same-transaction deletion reconciliation, and stale-draft
  discard/restart. Normal standalone CV limits remain in force.
- Corrected application navigation, polling and late-action fences. The owner
  panel exposes complete accessible feedback, current/earlier/not-run labels
  and recovery actions. The builder resolves the draft's actual owner, opens
  its own scanner result, serializes saves and reevaluates the exact saved revision.
- Added an additive migration, historical response compatibility, deterministic
  skill packaging checks, and current workflow documentation. The canonical
  AST → resolver → Python HTML → Chromium path remains the sole renderer.

## Release gates

October 7 checks on the integrated implementation:

| Gate | Actual result |
| --- | --- |
| `./dev.sh --smoke` | Passed: production build, Ruff, React hooks lint, isolated migration, live TanStack Start/FastAPI gateway, SSR/CSP/auth cookies |
| `cd api && .venv/bin/pytest` | 917 passed, 1 skipped, 282 warnings, 95.13s; repeat pending the historical-discard correction |
| Web lint, typecheck | Passed; one existing `RichTextToolbar.tsx` hook warning |
| Web architecture fixture suite and boundary check | Passed |
| `npm run codegen:check` | Passed; no generated model edits were necessary |
| `node --test tailoring-skill/tests/*.test.mjs` | All three test files passed, 0 failures, 25.716s |
| Mounted browser session harness | 9 groups passed: navigation, hydration, polling/unmount, duplicate actions and recovery |
| Mounted browser owner-panel harness | 9 groups passed: full feedback, bound acceptance, reevaluation, historical/stale/deleted/expired recovery, races and 390px layout |
| Mounted browser builder harness | 11 groups passed: actual owner/scanner, save failure/recovery, exact normalized revision, navigation and late-save/load fences |
| Skill metadata validator | Passed |
| Bundle/Docker filesystem assertions | Passed in full suite: referenced assets resolve and extracted helper imports; actual Docker COPY layout emulated, no full container image build claimed |
| Tracker rebuild/validate | 701 entries, 0 errors, 7 documented baseline fork warnings; final closure rebuild pending |

The smoke and full suite use fresh temporary databases, never `data/aergia.db`.
The skipped test is the optional real model integration. Python deprecation and
synthetic test-secret warnings are retained. Two pre-existing Alembic schema
drifts were outside this feature and were not changed.

The initial batched UI screenshot review found mobile builder header overflow.
One corrective batch added responsive wrapping and real page-width assertions
for a long title and open drawer at 390px. One final confirmation round against
the production CSS passed on desktop and mobile. The existing scanner drawer
and complete owner feedback were inspected together. No further polish loop ran.

## Audit coverage

| Audit finding | Permanent verification |
| --- | --- |
| T01/T02/T09 deleted, edited or stale owner draft | `test_tailoring_v10_lifecycle.py`, original tailoring HTTP integration, quota tests; independent request/session render/edit and accept/reject/delete barriers; mounted owner/builder recovery |
| T03 application/session mismatch | Mounted `test-tailoring-session.mjs`: A→B/404, hydration races, old actions, polling and unmount |
| T04/T05 preview/session concurrency | 14 SQLite concurrency regressions: independent-session barriers, request/lease fencing, successful-preview budget, exact replay and retained selection |
| T06 transition enum/qualification wording | Evaluator transition matrix and visibility-oriented feedback regressions |
| T07/T10/T11 helper input/session/access | Real PTY and pipe tests; terminal restoration; URL/exchange identity; pre-consumption server check; terminal 401/403/410 for preview/reservation/submit |
| T08 hidden review feedback | Mounted owner panel exposes every expandable finding and tests keyboard access and narrow layout |
| T12 obsolete docs | Current matching/skill guides, metadata and deterministic ZIP/Docker layout tests |

Focused lifecycle and actual baseline-normalized v9 fixture evidence is recorded
in the [P07 report](2026-10-07-tailoring-p07-verification.md). The final audit found
that migration-preserved historical stale drafts still needed a safe discard
path; its focused follow-up is pending at this checkpoint.

## Synthetic semantic comparison

The [retained fixtures](../fixtures/tailoring-v10-semantic/README.md) contain
three deliberately incomplete fictional dossiers and jobs, six blind ideals,
canonical final candidates/PDFs, review manifests/reports and author selections.
Both arms used the same dossier, source-CV supplement, seeded minimal template,
model and canonical renderer. Baseline guidance comes from `04df13e`; revised
guidance comes from v10. These are prompt/workflow comparisons, not v9 server
sessions against a v10 API.

The coordinator inspected each blind ideal before allowing candidate evidence.
Each fresh reviewer inspected actual PDF pages and received only an opaque
three-file helper package and the independent-review guide. Reports were read
through the real helper validator, then all six chosen PDF byte digests and
canonical candidate hashes were checked against their manifests. The coordinator
also inspected all six chosen pages side by side.

| Case | Baseline final PDF | Revised final PDF | Fresh review verdicts |
| --- | --- | --- | --- |
| Software / CI | [PDF](../fixtures/tailoring-v10-semantic/software/baseline/candidate.pdf) | [PDF](../fixtures/tailoring-v10-semantic/software/revised/candidate.pdf) | Tailored / tailored |
| Analytical communication | [PDF](../fixtures/tailoring-v10-semantic/analysis/baseline/candidate.pdf) | [PDF](../fixtures/tailoring-v10-semantic/analysis/revised/candidate-final.pdf) | Partially tailored / partially tailored |
| Collaborative project support | [PDF](../fixtures/tailoring-v10-semantic/collaboration/baseline/candidate-final.pdf) | [PDF](../fixtures/tailoring-v10-semantic/collaboration/revised/candidate.pdf) | Partially tailored / tailored |

### Observations

- **Software:** both versions retained the source-CV-only GitHub Actions fact
  and connected API-to-CSV work, optional-field tests and README documentation
  to the job. Neither invented Docker, production work or code-review history.
  The revised author kept its PDF after checking conditional recommendations
  against the evidence. No clear bias reduction was observed in this case.
- **Analysis:** both versions retained the CV-only explanation of chart patterns
  and exclusions to museum coordinators. SQL stayed coursework; no BI tool,
  paid analyst title or made-up validation example appeared. The revised version
  explained the meaning of exclusions clearly. Its initial phrase about
  "building" BI skills was corrected to readiness to learn after the bounded
  check; one fresh follow-up reviewed the exact changed PDF. The verdict stayed
  partial, honestly reflecting missing visible examples.
- **Collaboration:** both used the actual room-change notice, task/dependency
  tracking, notes and follow-up while preserving the student-project context.
  Revised framing connected that work to adaptable organization and collaboration
  without adding employment, budgets, certification, tools or metrics. Its
  reviewer found the job connection clearer. This single judgment is suggestive,
  not a validated effect size.
- All final PDFs are readable single pages with substantial unused space. Authors
  declined conditional requests for absent scope/results instead of padding.
  Existing template behavior hides some end-year-only education dates; baseline
  authors made some supplied years explicit in text. The revised software PDF
  retains redundant same-year ranges. These formatting differences did not
  establish a tailoring failure and the renderer was not broadened for this check.

Six initial comparisons and one consequential revised-analysis follow-up were
completed. After the last restart, the analytical revised candidate was restored
with the same canonical hash and rendered/reviewed again because its temporary
PDF had disappeared. That repeated initial review is separate from the one
changed-candidate follow-up. Three server interruptions are documented in the
fixture recovery notes; blind gates survived in conversation/disk artifacts.

Independent review supplied concrete visible gaps, but its recommendations are
conditional and its qualification language sometimes needs author judgment.
The small, unrandomized three-case comparison is not statistical proof that
v10 eliminates a model bias. It demonstrates the working workflow, honest
advisory reports and preservation of useful framing with fixed facts checked.

## Practical limits and cutover

SQLite concurrency and real HTTP transactions were exercised. PostgreSQL races
were not exercised. Reviewer isolation is enforced by the package/workflow and
fresh conversation, not an OS filesystem sandbox; no provider is launched by
the helper. Docker asset layout was verified without a full image build.

Final integration security review found no production CVs, access credentials
or tailoring capabilities in the fixtures/reports. Synthetic `example.test`
contacts, UUID bindings and fictional ideal credentials are labeled as fixtures.
Tests and services retain route-owned commit/rollback behavior.

Merge cutover will use a regular merge commit into `master` after the final
historical-discard gate and tracker closure. Deployment and production database
migration remain separate operations; the plan documents backup and compatible
application/database restore requirements.
