"""Codegen drift test — auto-discovered BaseModel subclasses must all be in the generated TS."""

import inspect
import subprocess
import sys
from pathlib import Path

from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_MODULE = "app.schema.models"


def _discovered_python_models() -> set[str]:
    sys.path.insert(0, str(REPO_ROOT / "api"))
    mod = __import__(SCHEMA_MODULE, fromlist=["*"])
    return {
        cls.__name__
        for _, cls in inspect.getmembers(mod)
        if inspect.isclass(cls) and issubclass(cls, BaseModel) and cls is not BaseModel
    }


def _emitted_ts_interfaces() -> set[str]:
    ts = (REPO_ROOT / "web" / "src" / "generated" / "schema.ts").read_text()
    return {
        line.split()[2]
        for line in ts.splitlines()
        if line.startswith("export interface ")
    }


def test_every_basemodel_subclass_is_emitted():
    """A schema addition without a corresponding TS interface would silently fail."""
    assert _discovered_python_models() == _emitted_ts_interfaces(), (
        "schema.ts is missing interfaces for: "
        f"{_discovered_python_models() - _emitted_ts_interfaces()}"
    )


def test_codegen_check_passes():
    """`codegen_schema.py --check` exits 0 against the committed schema."""
    result = subprocess.run(
        [sys.executable, "scripts/codegen_schema.py", "--check"],
        cwd=REPO_ROOT / "api",
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"--check failed:\n{result.stdout}\n{result.stderr}"
