# Tailoring v10 P07 verification

P07 lifecycle work was verified against the temporary database created by
`api/tests/conftest.py`. No production database was used.

## Verification

| Command | Result |
| --- | --- |
| `cd api && .venv/bin/pytest -q tests/test_tailoring_v10_lifecycle.py tests/test_tailoring_v10_migration.py` | 18 passed in 19.63s |
| `cd api && .venv/bin/pytest -q tests/test_tailoring.py tests/test_cvs.py tests/test_tailoring_v10_quota.py tests/test_tailoring_v10_concurrency.py` | 45 passed in 19.81s |
| `cd api && .venv/bin/pytest -q tests/test_tailoring_v10_lifecycle.py tests/test_tailoring_v10_concurrency.py tests/test_tailoring.py tests/test_tailoring_v10_quota.py` | 53 passed in 31.91s |
| `cd api && .venv/bin/ruff check app/services/tailoring.py app/routes/tailoring.py app/routes/cvs.py tests/test_tailoring_v10_lifecycle.py` | Passed |

Focused historical regressions also pass: `pytest -q tests/test_tailoring_v10_lifecycle.py -k 'historical_v9 or actual_v9'`
reports 4 passed. It covers frozen-v9 bodyless acceptance, stale and expired submitted
rows with a surviving counted CV, a stale submitted row whose CV pointer is
missing, repeated discard, quota release without creating a replacement
reservation, and successful restart. The missing-draft case uses an obsolete
scanner result schema and verifies discard succeeds with `scanner_result: null`.
Discard remains forbidden for accepted v9 sessions.

Expired rows with a surviving submitted draft remain a pending owner task;
both the session-creation and submit pending checks include that state. The
lifecycle regression verifies a second session is blocked until discard. An
ordinary expired author session with no draft can restart. Expired rows with a
missing draft pointer are reconciled through the `draft_missing` compare-and-
swap path, whose candidate selection and final state guard include `expired`.

The lifecycle suite covers exact selected-PDF retention and submit replay,
fit-review binding, advisory findings, initial owner-current seeding,
capability expiry, CV edit revision checks, contact and template basis
changes, job and source staleness, stale draft blocking and discard, same-
transaction deletion reconciliation, and replacement quota cleanup. Its
independent-session barriers cover a CV edit during rendering, contact or
template changes during rendering, and competing accept/reject/delete actions.
The historical acceptance case loads a protocol-v9 result envelope and checks
bodyless acceptance without applying v10 normalization. Historical discard
reuses the locked current-state reject path, recognizes submitted v4–v9 rows
that migration preserved as stale or expired, retires an active draft through
normal CV quota accounting, and treats an absent draft as an idempotent cleanup.

## Frozen protocol-v9 candidate provenance

`api/tests/fixtures/tailoring-v9-submission.json` is a synthetic result
envelope, not a captured database row. To generate its candidate, the exact
`TailoringCandidateCV`, `TailoringSection`, `_inject_profile_identity`, and
`_normalize_candidate` definitions were extracted from baseline commit
`04df13e` using `git show` and executed in the isolated module
`/tmp/tailoring_v9_baseline_normalizer.py`. The module used the baseline
candidate schema and normalizer methods with the persisted synthetic profile
and the `generic-minimal` manifest. The normalized output matched the frozen
candidate exactly. Its canonical SHA-256 is
`9cc0abb78602e325e176df174efc237a41206fcb1b61689eb900a599d6807a54`; the test
asserts that hash and retains the v9 candidate/evaluation bindings. Only the
database identities and scanner evidence are supplied for the isolated test
application.

The temporary module was generated outside the repository and was not
committed. Repository test data contains no production CVs, credentials, or
tailoring capabilities.
