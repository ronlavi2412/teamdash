from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

from teamdash.config import TeamConfig
from teamdash.fetch_github import fetch_prs, fetch_reviews
from teamdash.fetch_gitlab import check_auth as check_gitlab_auth
from teamdash.fetch_gitlab import fetch_mrs
from teamdash.models import EngineerQuarterMetrics, Quarter, QuarterSummary

CACHE_DIR = Path.home() / ".cache" / "teamdash"


def _config_hash(config: TeamConfig) -> str:
    key = json.dumps({
        "team": config.team_name,
        "orgs": sorted(config.github_orgs),
        "engineers": [(e.name, e.github, e.gitlab) for e in config.engineers],
    }, sort_keys=True)
    return hashlib.md5(key.encode()).hexdigest()[:12]


def _load_cache(config: TeamConfig) -> dict:
    cache_file = CACHE_DIR / f"{_config_hash(config)}.json"
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text())
            if data.get("date") == date.today().isoformat():
                return data.get("quarters", {})
        except (json.JSONDecodeError, KeyError):
            pass
    return {}


def _save_cache(config: TeamConfig, quarters_data: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{_config_hash(config)}.json"
    cache_file.write_text(json.dumps({
        "date": date.today().isoformat(),
        "quarters": quarters_data,
    }, indent=2))


def collect_all_data(
    config: TeamConfig,
    quarters: list[Quarter],
    use_cache: bool = True,
) -> list[QuarterSummary]:
    cache = _load_cache(config) if use_cache else {}
    gitlab_ok = False
    if config.gitlab_url:
        gitlab_ok = check_gitlab_auth(config.gitlab_url)
        if not gitlab_ok:
            print("[WARN] glab not authenticated for " + config.gitlab_url + ", GitLab MR counts will be 0", file=sys.stderr)

    summaries: list[QuarterSummary] = []
    updated_cache = dict(cache)

    for q in quarters:
        cached_quarter = cache.get(q.label, {})
        engineer_metrics: list[EngineerQuarterMetrics] = []

        for eng in config.engineers:
            cached_eng = cached_quarter.get(eng.name)
            if cached_eng:
                engineer_metrics.append(EngineerQuarterMetrics(
                    name=eng.name,
                    quarter=q.label,
                    github_prs=cached_eng["github_prs"],
                    gitlab_mrs=cached_eng["gitlab_mrs"],
                    reviews=cached_eng["reviews"],
                ))
                continue

            print(f"  Fetching {q.label} for {eng.name}...", file=sys.stderr)

            gh_prs = 0
            gh_reviews = 0
            gl_mrs = 0

            if eng.github and config.github_orgs:
                gh_prs = fetch_prs(eng.github, config.github_orgs, q.start, q.end)
                gh_reviews = fetch_reviews(eng.github, config.github_orgs, q.start, q.end)

            if eng.gitlab and config.gitlab_url and gitlab_ok:
                gl_mrs = fetch_mrs(config.gitlab_url, eng.gitlab, q.start, q.end)

            metrics = EngineerQuarterMetrics(
                name=eng.name,
                quarter=q.label,
                github_prs=gh_prs,
                gitlab_mrs=gl_mrs,
                reviews=gh_reviews,
            )
            engineer_metrics.append(metrics)

            updated_cache.setdefault(q.label, {})[eng.name] = {
                "github_prs": gh_prs,
                "gitlab_mrs": gl_mrs,
                "reviews": gh_reviews,
            }

        summaries.append(QuarterSummary(quarter=q, engineers=engineer_metrics))

    _save_cache(config, updated_cache)

    return summaries
