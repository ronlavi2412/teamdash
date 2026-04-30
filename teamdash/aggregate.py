from __future__ import annotations

import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from teamdash.config import TeamConfig
from teamdash.fetch_github import fetch_merge_times, fetch_prs, fetch_reviews
from teamdash.fetch_gitlab import check_auth as check_gitlab_auth
from teamdash.fetch_gitlab import fetch_mr_merge_times, fetch_mrs
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


def _fetch_engineer_data(
    eng, config: TeamConfig, gitlab_ok: bool, q: Quarter,
) -> EngineerQuarterMetrics:
    print(f"  Fetching {q.label} for {eng.name}...", file=sys.stderr)

    futures: dict[str, object] = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        if eng.github and config.github_orgs:
            futures["prs"] = pool.submit(fetch_prs, eng.github, config.github_orgs, q.start, q.end)
            futures["reviews"] = pool.submit(fetch_reviews, eng.github, config.github_orgs, q.start, q.end)
            futures["gh_mt"] = pool.submit(fetch_merge_times, eng.github, config.github_orgs, q.start, q.end)
        if eng.gitlab and config.gitlab_url and gitlab_ok:
            futures["mrs"] = pool.submit(fetch_mrs, config.gitlab_url, eng.gitlab, q.start, q.end)
            futures["gl_mt"] = pool.submit(fetch_mr_merge_times, config.gitlab_url, eng.gitlab, q.start, q.end)

    gh_prs = futures["prs"].result() if "prs" in futures else 0
    gh_reviews = futures["reviews"].result() if "reviews" in futures else 0
    gh_mt = futures["gh_mt"].result() if "gh_mt" in futures else []
    gl_mrs = futures["mrs"].result() if "mrs" in futures else 0
    gl_mt = futures["gl_mt"].result() if "gl_mt" in futures else []

    all_merge_times = gh_mt + gl_mt
    avg_mt = round(sum(all_merge_times) / len(all_merge_times), 1) if all_merge_times else None

    return EngineerQuarterMetrics(
        name=eng.name,
        quarter=q.label,
        github_prs=gh_prs,
        gitlab_mrs=gl_mrs,
        reviews=gh_reviews,
        merge_time_days=avg_mt,
    )


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

    quarter_cached: dict[str, dict[str, EngineerQuarterMetrics]] = {}
    fetch_tasks: list[tuple] = []

    for q in quarters:
        cached_quarter = cache.get(q.label, {})
        quarter_cached[q.label] = {}
        for eng in config.engineers:
            cached_eng = cached_quarter.get(eng.name)
            if cached_eng:
                quarter_cached[q.label][eng.name] = EngineerQuarterMetrics(
                    name=eng.name,
                    quarter=q.label,
                    github_prs=cached_eng["github_prs"],
                    gitlab_mrs=cached_eng["gitlab_mrs"],
                    reviews=cached_eng["reviews"],
                    merge_time_days=cached_eng.get("merge_time_days"),
                )
            else:
                fetch_tasks.append((eng, q))

    fetched: dict[tuple[str, str], EngineerQuarterMetrics] = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        future_to_key = {
            pool.submit(_fetch_engineer_data, eng, config, gitlab_ok, q): (q.label, eng.name)
            for eng, q in fetch_tasks
        }
        for future in future_to_key:
            key = future_to_key[future]
            fetched[key] = future.result()

    updated_cache = dict(cache)
    summaries: list[QuarterSummary] = []
    for q in quarters:
        engineer_metrics: list[EngineerQuarterMetrics] = []
        for eng in config.engineers:
            if eng.name in quarter_cached[q.label]:
                engineer_metrics.append(quarter_cached[q.label][eng.name])
            else:
                metrics = fetched[(q.label, eng.name)]
                engineer_metrics.append(metrics)
                updated_cache.setdefault(q.label, {})[eng.name] = {
                    "github_prs": metrics.github_prs,
                    "gitlab_mrs": metrics.gitlab_mrs,
                    "reviews": metrics.reviews,
                    "merge_time_days": metrics.merge_time_days,
                }
        summaries.append(QuarterSummary(quarter=q, engineers=engineer_metrics))

    _save_cache(config, updated_cache)
    return summaries
