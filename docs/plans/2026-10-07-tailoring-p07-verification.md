# Tailoring v10 P07 verification

P07 lifecycle work was verified against the temporary database created by
`api/tests/conftest.py`. No production database was used.

## Verification

| Command | Result |
| --- | --- |
| `cd api && .venv/bin/pytest -q tests/test_tailoring_v10_lifecycle.py` | 12 passed in 14.95s |
| `cd api && .venv/bin/pytest -q tests/test_tailoring.py tests/test_cvs.py tests/test_tailoring_v10_quota.py tests/test_tailoring_v10_concurrency.py` | 45 passed in 19.81s |
| `cd api && .venv/bin/ruff check app/services/tailoring.py app/routes/tailoring.py app/routes/cvs.py tests/test_tailoring_v10_lifecycle.py` | Passed |

The lifecycle suite covers exact selected-PDF retention and submit replay,
fit-review binding, advisory findings, initial owner-current seeding,
capability expiry, CV edit revision checks, contact and template basis
changes, job and source staleness, stale draft blocking and discard, same-
transaction deletion reconciliation, and replacement quota cleanup. Its
independent-session barriers cover a CV edit during rendering, contact or
template changes during rendering, and competing accept/reject/delete actions.
The historical acceptance case loads a protocol-v9 result envelope and checks
bodyless acceptance without applying v10 normalization.

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
