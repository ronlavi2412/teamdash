from __future__ import annotations

import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from teamdash.config import TeamConfig
from teamdash.fetch_github import (
    fetch_merge_times,
    fetch_pr_details,
    fetch_prs,
    fetch_reviewed_pr_details,
    fetch_reviews,
)
from teamdash.fetch_gitlab import check_auth as check_gitlab_auth
from teamdash.fetch_gitlab import fetch_mr_details, fetch_mr_merge_times, fetch_mrs
from teamdash.models import EngineerQuarterMetrics, Quarter, QuarterSummary
from teamdash.scoring import ScoringConfig, score_prs

CACHE_DIR = Path.home() / ".cache" / "teamdash"


def _config_hash(config: TeamConfig) -> str:
    scoring_key = None
    if config.scoring:
        scoring_key = {
            "size_points": config.scoring.size_points,
            "diff_thresholds": list(config.scoring.diff_thresholds),
            "file_thresholds": list(config.scoring.file_thresholds),
            "merge_time_thresholds": list(config.scoring.merge_time_thresholds),
            "qe_labels": sorted(config.scoring.qe_labels),
        }
    key = json.dumps({
        "team": config.team_name,
        "orgs": sorted(config.github_orgs),
        "engineers": [(e.name, e.github, e.gitlab) for e in config.engineers],
        "scoring": scoring_key,
    }, sort_keys=True)
    return hashlib.md5(key.encode()).hexdigest()[:12]


def _load_cache(config: TeamConfig) -> dict:
    cache_file = CACHE_DIR / f"{_config_hash(config)}.json"
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text()).get("quarters", {})
        except (json.JSONDecodeError, KeyError):
            pass
    return {}


def _is_quarter_cache_fresh(quarter_data: dict, quarter_end: str) -> bool:
    fetched = quarter_data.get("_meta", {}).get("fetched_date")
    if not fetched:
        return False
    if quarter_end < date.today().isoformat():
        return True
    return fetched == date.today().isoformat()


def _save_cache(config: TeamConfig, quarters_data: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{_config_hash(config)}.json"
    cache_file.write_text(json.dumps({
        "quarters": quarters_data,
    }, indent=2))


def _fetch_engineer_data(
    eng, config: TeamConfig, gitlab_ok: bool, q: Quarter,
    enable_scoring: bool = False,
) -> EngineerQuarterMetrics:
    print(f"  Fetching {q.label} for {eng.name}...", file=sys.stderr)

    if enable_scoring:
        return _fetch_engineer_data_scored(eng, config, gitlab_ok, q)

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
        github_merge_times=gh_mt,
        gitlab_merge_times=gl_mt,
    )


def _fetch_engineer_data_scored(
    eng, config: TeamConfig, gitlab_ok: bool, q: Quarter,
) -> EngineerQuarterMetrics:
    from teamdash.models import PRDetail

    all_details: list[PRDetail] = []

    gh_reviews = 0
    if eng.github and config.github_orgs:
        gh_details = fetch_pr_details(eng.github, config.github_orgs, q.start, q.end)
        all_details.extend(gh_details)
        gh_reviews = fetch_reviews(eng.github, config.github_orgs, q.start, q.end)

    gl_details: list[PRDetail] = []
    if eng.gitlab and config.gitlab_url and gitlab_ok:
        gl_details = fetch_mr_details(config.gitlab_url, eng.gitlab, q.start, q.end)
        all_details.extend(gl_details)

    reviewed_details: list[PRDetail] = []
    if eng.github and config.github_orgs:
        reviewed_details = fetch_reviewed_pr_details(
            eng.github, config.github_orgs, q.start, q.end,
        )

    gh_prs = sum(1 for d in all_details if d.source == "github")
    gl_mrs = sum(1 for d in all_details if d.source == "gitlab")

    gh_mt = [d.merge_time_days for d in all_details if d.source == "github" and d.merge_time_days is not None]
    gl_mt = [d.merge_time_days for d in all_details if d.source == "gitlab" and d.merge_time_days is not None]
    all_merge_times = gh_mt + gl_mt
    avg_mt = round(sum(all_merge_times) / len(all_merge_times), 1) if all_merge_times else None

    scored = score_prs(all_details, config.scoring)
    sp_dev = sum(s.points for s in scored if s.point_type == "dev")
    sp_qe = sum(s.points for s in scored if s.point_type == "qe")
    xl = sum(1 for s in scored if s.size == "XL")

    scored_reviews = score_prs(reviewed_details, config.scoring)
    review_sp = sum(s.points for s in scored_reviews)

    return EngineerQuarterMetrics(
        name=eng.name,
        quarter=q.label,
        github_prs=gh_prs,
        gitlab_mrs=gl_mrs,
        reviews=gh_reviews,
        merge_time_days=avg_mt,
        story_points_dev=sp_dev,
        story_points_qe=sp_qe,
        scored_prs=scored,
        xl_count=xl,
        review_story_points=review_sp,
        scored_reviews=scored_reviews,
        github_merge_times=gh_mt,
        gitlab_merge_times=gl_mt,
    )


def _metrics_from_cache(
    name: str, quarter: str, cached_eng: dict,
) -> EngineerQuarterMetrics:
    return EngineerQuarterMetrics(
        name=name,
        quarter=quarter,
        github_prs=cached_eng["github_prs"],
        gitlab_mrs=cached_eng["gitlab_mrs"],
        reviews=cached_eng["reviews"],
        merge_time_days=cached_eng.get("merge_time_days"),
        story_points_dev=cached_eng.get("story_points_dev", 0),
        story_points_qe=cached_eng.get("story_points_qe", 0),
        xl_count=cached_eng.get("xl_count", 0),
        review_story_points=cached_eng.get("review_story_points", 0),
        github_merge_times=cached_eng.get("_github_merge_times", []),
        gitlab_merge_times=cached_eng.get("_gitlab_merge_times", []),
    )


def _refresh_engineer_gitlab(
    eng, config: TeamConfig, gitlab_ok: bool, q: Quarter,
    cached_eng: dict, enable_scoring: bool,
) -> EngineerQuarterMetrics:
    print(f"  Refreshing GitLab {q.label} for {eng.name}...", file=sys.stderr)

    gh_prs = cached_eng["github_prs"]
    gh_reviews = cached_eng["reviews"]
    gh_mt = cached_eng.get("_github_merge_times", [])

    if not enable_scoring:
        gl_mrs = 0
        gl_mt: list[float] = []
        if eng.gitlab and config.gitlab_url and gitlab_ok:
            gl_mrs = fetch_mrs(config.gitlab_url, eng.gitlab, q.start, q.end)
            gl_mt = fetch_mr_merge_times(config.gitlab_url, eng.gitlab, q.start, q.end)

        all_mt = gh_mt + gl_mt
        avg_mt = round(sum(all_mt) / len(all_mt), 1) if all_mt else cached_eng.get("merge_time_days")

        return EngineerQuarterMetrics(
            name=eng.name,
            quarter=q.label,
            github_prs=gh_prs,
            gitlab_mrs=gl_mrs,
            reviews=gh_reviews,
            merge_time_days=avg_mt,
            github_merge_times=gh_mt,
            gitlab_merge_times=gl_mt,
        )

    from teamdash.models import PRDetail

    gh_scored_summary = [
        s for s in cached_eng.get("scored_prs_summary", [])
        if "github.com" in s.get("url", "")
    ]
    gh_sp_dev = sum(s["points"] for s in gh_scored_summary if s.get("point_type") == "dev")
    gh_sp_qe = sum(s["points"] for s in gh_scored_summary if s.get("point_type") == "qe")
    gh_xl = sum(1 for s in gh_scored_summary if s.get("size") == "XL")
    gh_review_sp = cached_eng.get("review_story_points", 0)

    gl_details: list[PRDetail] = []
    if eng.gitlab and config.gitlab_url and gitlab_ok:
        gl_details = fetch_mr_details(config.gitlab_url, eng.gitlab, q.start, q.end)

    gl_scored = score_prs(gl_details, config.scoring)
    gl_sp_dev = sum(s.points for s in gl_scored if s.point_type == "dev")
    gl_sp_qe = sum(s.points for s in gl_scored if s.point_type == "qe")
    gl_xl = sum(1 for s in gl_scored if s.size == "XL")
    gl_mt_scored = [d.merge_time_days for d in gl_details if d.merge_time_days is not None]

    all_mt = gh_mt + gl_mt_scored
    avg_mt = round(sum(all_mt) / len(all_mt), 1) if all_mt else cached_eng.get("merge_time_days")

    return EngineerQuarterMetrics(
        name=eng.name,
        quarter=q.label,
        github_prs=gh_prs,
        gitlab_mrs=len(gl_details),
        reviews=gh_reviews,
        merge_time_days=avg_mt,
        story_points_dev=gh_sp_dev + gl_sp_dev,
        story_points_qe=gh_sp_qe + gl_sp_qe,
        scored_prs=gl_scored,
        xl_count=gh_xl + gl_xl,
        review_story_points=gh_review_sp,
        github_merge_times=gh_mt,
        gitlab_merge_times=gl_mt_scored,
    )


def _build_cache_entry(
    metrics: EngineerQuarterMetrics, enable_scoring: bool,
    extra_scored_summary: list[dict] | None = None,
) -> dict:
    entry: dict = {
        "github_prs": metrics.github_prs,
        "gitlab_mrs": metrics.gitlab_mrs,
        "reviews": metrics.reviews,
        "merge_time_days": metrics.merge_time_days,
        "_github_merge_times": metrics.github_merge_times,
        "_gitlab_merge_times": metrics.gitlab_merge_times,
    }
    if enable_scoring:
        entry["story_points_dev"] = metrics.story_points_dev
        entry["story_points_qe"] = metrics.story_points_qe
        entry["xl_count"] = metrics.xl_count
        entry["review_story_points"] = metrics.review_story_points
        summary = [
            {
                "url": s.detail.url,
                "size": s.size,
                "points": s.points,
                "point_type": s.point_type,
                "flags": s.flags,
            }
            for s in metrics.scored_prs
        ]
        if extra_scored_summary:
            summary = extra_scored_summary + summary
        entry["scored_prs_summary"] = summary
    return entry


def collect_all_data(
    config: TeamConfig,
    quarters: list[Quarter],
    use_cache: bool = True,
    enable_scoring: bool = True,
    refresh_gitlab: bool = False,
) -> list[QuarterSummary]:
    cache = _load_cache(config) if (use_cache or refresh_gitlab) else {}
    gitlab_ok = False
    if config.gitlab_url:
        gitlab_ok = check_gitlab_auth(config.gitlab_url)
        if not gitlab_ok:
            print("[WARN] glab not authenticated for " + config.gitlab_url + ", GitLab MR counts will be 0", file=sys.stderr)

    if refresh_gitlab:
        return _collect_refresh_gitlab(
            config, quarters, cache, gitlab_ok, enable_scoring,
        )

    quarter_cached: dict[str, dict[str, EngineerQuarterMetrics]] = {}
    fetch_tasks: list[tuple] = []

    for q in quarters:
        cached_quarter = cache.get(q.label, {})
        quarter_fresh = _is_quarter_cache_fresh(cached_quarter, q.end)
        quarter_cached[q.label] = {}

        if quarter_fresh:
            for eng in config.engineers:
                cached_eng = cached_quarter.get(eng.name)
                if cached_eng:
                    quarter_cached[q.label][eng.name] = _metrics_from_cache(
                        eng.name, q.label, cached_eng,
                    )
                else:
                    fetch_tasks.append((eng, q))
        else:
            for eng in config.engineers:
                fetch_tasks.append((eng, q))

    fetched: dict[tuple[str, str], EngineerQuarterMetrics] = {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        future_to_key = {
            pool.submit(
                _fetch_engineer_data, eng, config, gitlab_ok, q,
                enable_scoring=enable_scoring,
            ): (q.label, eng.name)
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
                cache_entry = _build_cache_entry(metrics, enable_scoring)
                q_cache = updated_cache.setdefault(q.label, {})
                q_cache[eng.name] = cache_entry
                q_cache["_meta"] = {"fetched_date": date.today().isoformat()}
        if q.label in updated_cache and "_meta" not in updated_cache[q.label]:
            updated_cache[q.label]["_meta"] = {"fetched_date": date.today().isoformat()}
        summaries.append(QuarterSummary(quarter=q, engineers=engineer_metrics))

    _save_cache(config, updated_cache)
    return summaries


def _collect_refresh_gitlab(
    config: TeamConfig,
    quarters: list[Quarter],
    cache: dict,
    gitlab_ok: bool,
    enable_scoring: bool,
) -> list[QuarterSummary]:
    updated_cache = dict(cache)
    summaries: list[QuarterSummary] = []

    for q in quarters:
        cached_quarter = cache.get(q.label, {})
        engineer_metrics: list[EngineerQuarterMetrics] = []

        for eng in config.engineers:
            cached_eng = cached_quarter.get(eng.name)

            if cached_eng and eng.gitlab:
                metrics = _refresh_engineer_gitlab(
                    eng, config, gitlab_ok, q, cached_eng, enable_scoring,
                )
                gh_scored_summary = [
                    s for s in cached_eng.get("scored_prs_summary", [])
                    if "github.com" in s.get("url", "")
                ]
                cache_entry = _build_cache_entry(
                    metrics, enable_scoring,
                    extra_scored_summary=gh_scored_summary,
                )
            elif cached_eng:
                metrics = _metrics_from_cache(eng.name, q.label, cached_eng)
                cache_entry = cached_eng
            else:
                print(f"  [WARN] No cached data for {eng.name} {q.label}, skipping", file=sys.stderr)
                metrics = EngineerQuarterMetrics(name=eng.name, quarter=q.label)
                cache_entry = _build_cache_entry(metrics, enable_scoring)

            engineer_metrics.append(metrics)
            q_cache = updated_cache.setdefault(q.label, {})
            q_cache[eng.name] = cache_entry
            q_cache["_meta"] = {"fetched_date": date.today().isoformat()}

        summaries.append(QuarterSummary(quarter=q, engineers=engineer_metrics))

    _save_cache(config, updated_cache)
    return summaries
