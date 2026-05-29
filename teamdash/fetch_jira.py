from __future__ import annotations

import json
import sys
from pathlib import Path


def load_jira_data(path: str) -> dict[str, dict[str, int]]:
    """Load verified-bugs counts from a pre-fetched Jira data JSON file.

    Expected format: {"2025-Q3": {"Engineer Name": 5, ...}, ...}
    """
    p = Path(path)
    if not p.exists():
        print(f"[WARN] Jira data file not found: {path}", file=sys.stderr)
        return {}

    try:
        data = json.loads(p.read_text())
    except json.JSONDecodeError as e:
        print(f"[WARN] Invalid JSON in Jira data file {path}: {e}", file=sys.stderr)
        return {}

    if not isinstance(data, dict):
        print(f"[WARN] Jira data must be a JSON object, got {type(data).__name__}", file=sys.stderr)
        return {}

    return data
