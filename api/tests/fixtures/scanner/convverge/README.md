# Convverge Junior Software Developer regression pair

`job.json` is the complete Convverge posting captured from the tailoring
session. `candidate.json` is the actual tailored CV exported by that session
and remains unchanged. `library-opportunities.json` freezes two relevant
Library narratives from the local candidate source. `candidate-after.json`
is a manually composed, source-grounded example of a stronger draft; it is
not an output produced by an agent session.

The scan and opportunity regression is in
`api/tests/test_scanner_convverge_fixture.py`. The older investigation and
Jobscan comparison remain in `regression-report.md` and describe the prior
scanner version. The new example keeps client-facing and blocker-reporting
gaps when the source does not establish them.
