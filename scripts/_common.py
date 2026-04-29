"""Shared helpers for scripts. Adds the parent skill folder to sys.path."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Make `client` and `kpi` importable regardless of how the script is invoked.
SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))


def out_json(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


def is_json_mode(argv: list[str]) -> bool:
    return "--json" in argv
