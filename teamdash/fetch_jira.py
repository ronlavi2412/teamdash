from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class JiraData:
    bugs: dict[str, dict[str, int]] = field(default_factory=dict)
    activity_types: dict[str, dict[str, dict[str, int]]] = field(default_factory=dict)
    cycle_times: dict[str, dict[str, dict[str, dict[str, list[float]]]]] = field(default_factory=dict)


def load_jira_data(path: str) -> JiraData | None:
    """Load Jira data from a pre-fetched JSON file.

    Expected format:
        {
            "2025-Q3": {"Engineer Name": 5, ...},
            "activity_types": {
                "2025-Q3": {"Engineer Name": {"Type": 3, ...}, ...}
            }
        }
    """
    p = Path(path)
    if not p.exists():
        print(f"[WARN] Jira data file not found: {path}", file=sys.stderr)
        return None

    try:
        data = json.loads(p.read_text())
    except json.JSONDecodeError as e:
        print(f"[WARN] Invalid JSON in Jira data file {path}: {e}", file=sys.stderr)
        return None

    if not isinstance(data, dict):
        print(f"[WARN] Jira data must be a JSON object, got {type(data).__name__}", file=sys.stderr)
        return None

    if "jiraData" in data:
        data = data["jiraData"]

    bugs = {k: v for k, v in data.items() if k not in ("activity_types", "cycle_times")}
    activity_types = data.get("activity_types", {})
    cycle_times = data.get("cycle_times", {})

    return JiraData(bugs=bugs, activity_types=activity_types, cycle_times=cycle_times)
