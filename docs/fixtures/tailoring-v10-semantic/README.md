# Synthetic tailoring examples

These are fictional candidate and job fixtures for the v10 semantic comparison.
They contain no account data or tailoring capabilities. Both prompt arms use
the same dossier, including its labeled source-CV supplement, so the comparison
examines author guidance rather than unequal access to evidence.

Baseline instructions come from commit `04df13e`. Revised instructions come
from the implemented v10 skill. Each blind ideal is completed before candidate
evidence becomes available. Authors and fresh PDF reviewers use Luna 6 with max
reasoning. Aergia's canonical renderer and the `generic-minimal` template are
used for both arms.

The coordinator's execution report records the chosen PDFs, reviewer findings,
and observed limitations. This small comparison is evidence for prompt tuning;
it is not a statistically validated measurement of model bias.

## Local harness

`render.py` accepts only the named fictional candidate inputs in these case
directories. Run it with `PYTHONPATH=api api/.venv/bin/python` from the repository
root. It uses the seeded `generic-minimal` manifest, the server normalizer and
the canonical Python HTML/Chromium renderer, then emits the PDF, canonical
candidate, hashes and inspection thumbnails. It does not access an account DB.

`node docs/fixtures/tailoring-v10-semantic/prepare-review.mjs analysis revised`
exports the actual portable helper's three-file allowlist under an opaque UUID
directory. A separate reviewer reads only that directory and the independent
review guide. Package paths and thumbnails are local generated files; chosen
PDFs, manifests, jobs and reports are retained with each arm. Rendering again
may change PDF metadata and its SHA, so obtain a matching fresh review instead
of reusing a report from earlier bytes.

Three server interruptions affected execution. Software artifacts and the
baseline analytical comparison were retained before the last restart. Other
author drafts were restored from their original conversation artifacts; their
recovery notes document the stage gates. The analytical revised candidate
retained its original canonical hash and was rendered and independently
reviewed again after the temporary PDF disappeared.
