"""Make the showcase package importable when pytest runs from the repository root."""

from __future__ import annotations

import sys
from pathlib import Path


SHOWCASE_DIR = Path(__file__).resolve().parents[1]
if str(SHOWCASE_DIR) not in sys.path:
    sys.path.insert(0, str(SHOWCASE_DIR))
