"""Ensure the repo root is on ``sys.path`` when running ``pytest scripts/tests``.

This lets tests ``from scripts.update_readme import ...`` whether invoked from
the repo root, from inside ``scripts/``, or from an IDE with a different
working directory.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
