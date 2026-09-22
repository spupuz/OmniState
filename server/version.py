"""Single source of truth for the server version.

The version lives only in VERSION.txt (repo root, also baked into the image at
/app/VERSION.txt). App, MCP server and /health all read this helper, so a
bump can never drift from what the server reports.
"""
from __future__ import annotations

from pathlib import Path

_VERSION_FILE = Path(__file__).resolve().parent.parent / "VERSION.txt"
FALLBACK = "0.0.0"


def get_version() -> str:
    try:
        version = _VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return FALLBACK
    return version or FALLBACK