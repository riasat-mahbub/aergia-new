"""Parser test fixtures.

- ``sample.pdf`` — hand-crafted 848-byte single-page PDF (Jane Doe +
  EXPERIENCE + SKILLS). The smoke-gate minimum for the live import
  route; it is NOT a parser regression test.
- ``resume-benchmark.pdf`` — the user's own CV (Riasat Mahbub, August
  2026, Chromium-exported). The real-world corpus that exposed the
  parser's profile-only failure. `tests/test_parser_smoke.py` locks
  the end-to-end contract against it; do not replace with a mock.
"""
