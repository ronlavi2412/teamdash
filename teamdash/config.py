from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import json

from teamdash.scoring import ScoringConfig


@dataclass
class EngineerConfig:
    name: str
    github: str | None = None
    gitlab: str | None = None
    jira_account_id: str | None = None


@dataclass
class JiraConfig:
    cloud_id: str
    project_keys: list[str]


@dataclass
class TeamConfig:
    team_name: str
    gitlab_url: str | None
    github_orgs: list[str]
    engineers: list[EngineerConfig] = field(default_factory=list)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    jira: JiraConfig | None = None


def load_config(path: str) -> TeamConfig:
    p = Path(path)
    if not p.exists():
        print(f"[ERROR] Config file not found: {path}", file=sys.stderr)
        sys.exit(1)

    try:
        raw = json.loads(p.read_text())
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in {path}: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(raw, dict):
        print(
            f"[ERROR] Config must be a JSON object, got {type(raw).__name__}",
            file=sys.stderr,
        )
        sys.exit(1)

    team_name = raw.get("team_name")
    if not team_name:
        print("[ERROR] Missing 'team_name' in config", file=sys.stderr)
        sys.exit(1)

    gitlab_url = (raw.get("gitlab") or {}).get("url")
    github_orgs = (raw.get("github") or {}).get("orgs", [])

    engineers_raw = raw.get("engineers", [])
    if not engineers_raw:
        print("[ERROR] No engineers defined in config", file=sys.stderr)
        sys.exit(1)

    engineers = []
    for i, eng in enumerate(engineers_raw):
        name = eng.get("name")
        if not name:
            print(f"[ERROR] Engineer #{i + 1} missing 'name'", file=sys.stderr)
            sys.exit(1)
        gh = eng.get("github")
        gl = eng.get("gitlab")
        if not gh and not gl:
            print(
                f"[ERROR] Engineer '{name}' needs at least one of 'github' or 'gitlab'",
                file=sys.stderr,
            )
            sys.exit(1)
        jira_id = eng.get("jira_account_id")
        engineers.append(
            EngineerConfig(name=name, github=gh, gitlab=gl, jira_account_id=jira_id)
        )

    jira_raw = raw.get("jira")
    jira = None
    if jira_raw and isinstance(jira_raw, dict):
        cloud_id = jira_raw.get("cloud_id")
        project_keys = jira_raw.get("project_keys", [])
        if cloud_id:
            jira = JiraConfig(cloud_id=cloud_id, project_keys=project_keys)

    scoring_raw = raw.get("scoring", {}) or {}
    scoring_kwargs: dict = {}
    if "size_points" in scoring_raw:
        scoring_kwargs["size_points"] = scoring_raw["size_points"]
    if "diff_thresholds" in scoring_raw:
        scoring_kwargs["diff_thresholds"] = tuple(scoring_raw["diff_thresholds"])
    if "file_thresholds" in scoring_raw:
        scoring_kwargs["file_thresholds"] = tuple(scoring_raw["file_thresholds"])
    if "merge_time_thresholds" in scoring_raw:
        scoring_kwargs["merge_time_thresholds"] = tuple(
            scoring_raw["merge_time_thresholds"]
        )
    if "size_label_patterns" in scoring_raw:
        scoring_kwargs["size_label_patterns"] = scoring_raw["size_label_patterns"]
    scoring = ScoringConfig(**scoring_kwargs)

    return TeamConfig(
        team_name=team_name,
        gitlab_url=gitlab_url,
        github_orgs=github_orgs,
        engineers=engineers,
        scoring=scoring,
        jira=jira,
    )
