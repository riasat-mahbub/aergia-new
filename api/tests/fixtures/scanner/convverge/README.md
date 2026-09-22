# Convverge Junior Software Developer regression pair

`job.json` is the complete Convverge posting captured from the tailoring
session. `candidate.json` is the actual tailored CV exported by that session;
it is intentionally kept unchanged so the scanner cannot pass by inventing
collaboration, Agile, or Azure evidence.

The end-to-end regression is in
`api/tests/test_scanner_convverge_fixture.py`. The readable before/after and
Jobscan comparison is generated alongside this fixture as
`regression-report.md`.
