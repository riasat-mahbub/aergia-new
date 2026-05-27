"""Regression test for the `dev.sh` uvicorn launch line.

Root cause of the `[vite] http proxy error: /api/v1/cvs ... ECONNREFUSED` 500 on
the CVs page: `dev.sh` launched uvicorn with a *quoted* multi-token option string:

    uvicorn app.main:app "$UVICORN_OPTS" &

With `UVICORN_OPTS="--host 0.0.0.0 --port 8000 --reload"` the quotes make the whole
string a single argument, so uvicorn exits immediately with
`Error: No such option '--host 0.0.0.0 --port 8000 --reload'` and the backend never
accepts connections.

This test encodes the `quoted-string` vs `bash-array` contract: the launcher must
pass each option as its own token (a bash array indexed as "${UVICORN_OPTS[@]}").
"""

from pathlib import Path
import re

# dev.sh lives at the repo root: <repo>/dev.sh. This test file is <repo>/api/tests/.
REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_SH = REPO_ROOT / "dev.sh"


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
