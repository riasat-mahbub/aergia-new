"""Regression tests for the `dev.sh` launcher and the Phase 8 smoke gate.

Two contracts are tested here:

1. The uvicorn launcher must pass its options as a bash array
   (``${UVICORN_OPTS[@]}``), not a quoted multi-token string. The
   pre-Phase-7 defect turned every ``./dev.sh`` start into a silent
   backend death; the suite below locks the fix.
2. The hardening gate (``--smoke``) must dispatch to
   ``scripts/smoke.sh`` before the normal install/migrate/launch
   pipeline runs, so it can exercise the architecture without
   mutating user data or installing Playwright browsers.
"""

from pathlib import Path
import os
import re

# dev.sh lives at the repo root: <repo>/dev.sh. This test file is <repo>/api/tests/.
REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_SH = REPO_ROOT / "dev.sh"
SMOKE_SH = REPO_ROOT / "scripts" / "smoke.sh"


def _launch_line() -> str:
    assert DEV_SH.exists(), f"dev.sh not found at {DEV_SH}"
    text = DEV_SH.read_text()
    for line in text.splitlines():
        if "uvicorn app.main:app" in line:
            return line.strip()
    raise AssertionError("no `uvicorn app.main:app` launch line found in dev.sh")


def test_uvicorn_launch_uses_bash_array_not_quoted_string():
    """The uvicorn options must be expanded from a bash array, not passed as one
    quoted blob (which uvicorn rejects with 'No such option')."""
    line = _launch_line()
    assert re.search(r"\$\{UVICORN_OPTS\[@\]\}", line), (
        "uvicorn launch line must expand the option array with "
        "${UVICORN_OPTS[@]}; got: " + line
    )
    # The quoted-string form ("$UVICORN_OPTS") is exactly the defect.
    assert '$"{UVICORN_OPTS[@]}"' not in line  # sanity: no doubly-quoted array
    assert "$UVICORN_OPTS\"" not in line, (
        'quoted multi-token string form "$UVICORN_OPTS" is the defect under test'
    )


def test_uvicorn_launch_presents_no_stray_quotes_around_options():
    """Ensure the app argument and array expansion are each separate tokens, and
    the flag (`&`) is present so uvicorn runs in the background."""
    line = _launch_line()
    assert line.startswith("uvicorn app.main:app ")
    assert " &" in line  # backgrounded so the frontend can start alongside


def test_uvicorn_launch_declares_options_as_array():
    """`UVICORN_OPTS` must be declared/appendable as a bash array, not a plain
    string concatenation, so ${UVICORN_OPTS[@]} word-splits correctly."""
    text = DEV_SH.read_text()
    # The --reload append must be `+=('...')` (array append), not `$VAR --reload`.
    assert "UVICORN_OPTS+=(--reload)" in text, (
        "UVICORN_OPTS --reload must be appended as an array element "
        "(UVICORN_OPTS+=(--reload)), not string concatenation"
    )


SMOKE_SECTION_MARKERS = (
    "--smoke",
    "SMOKE=true",
    "SMOKE=false",
    "ERROR: --smoke cannot be combined with --prod or --build",
    "scripts/smoke.sh",
)


def test_dev_sh_documents_smoke_flag_and_dispatches():
    """`--smoke` must be a documented flag that dispatches to scripts/smoke.sh
    before the normal install/launch pipeline runs. The hardening gate is the
    only developer-visible behavior added by Phase 8."""
    text = DEV_SH.read_text()
    for marker in SMOKE_SECTION_MARKERS:
        assert marker in text, (
            f"dev.sh must include the smoke contract marker {marker!r}; "
            "see local://phase-7-closeout-phase-8-hardening-plan.md"
        )
    # The smoke path must short-circuit before the normal install/migrate
    # sequence so `./dev.sh --smoke` doesn't try to install Playwright
    # browsers or mutate the user's local database.
    assert text.find("--smoke") < text.find("=== Setting up API ==="), (
        "--smoke dispatch must precede the normal install pipeline"
    )
    assert text.find('exec "$ROOT_DIR/scripts/smoke.sh"') >= 0, (
        "dev.sh must exec the smoke runner instead of forking into the "
        "normal dev loop"
    )


def test_smoke_sh_is_executable_and_sealed():
    """scripts/smoke.sh must exist, be executable, and not touch user data."""
    assert SMOKE_SH.exists(), f"{SMOKE_SH} missing; see plan Step 6"
    assert os.access(SMOKE_SH, os.X_OK), f"{SMOKE_SH} is not executable"
    text = SMOKE_SH.read_text()
    assert "set -Eeuo pipefail" in text, "smoke.sh must run with -Eeuo pipefail"
    for forbidden in (
        "data/aergia.db",
        "data/aergia.test.db",
    ):
        assert forbidden not in text, (
            f"smoke.sh must never reference {forbidden}"
        )
    assert "playwright install" not in text, (
        "smoke.sh must not auto-install Playwright browsers"
    )
    assert "mktemp" in text, "smoke.sh must use mktemp for its working directory"
