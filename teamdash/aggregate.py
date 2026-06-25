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
from teamdash.fetch_gitlab import (
    fetch_mr_details,
    fetch_mr_merge_times,
    fetch_mrs,
    fetch_reviewed_mr_details as fetch_reviewed_gl_details,
)
from teamdash.fetch_gitlab import fetch_reviews as fetch_gitlab_reviews
from teamdash.fetch_jira import JiraData
from teamdash.models import EngineerQuarterMetrics, Quarter, QuarterSummary
from teamdash.scoring import ScoringConfig, score_prs

CACHE_DIR = Path.home() / ".cache" / "teamdash"


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return round((s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2), 1)


def _config_hash(config: TeamConfig) -> str:
    scoring_key = None
    if config.scoring:
        scoring_key = {
            "size_points": config.scoring.size_points,
            "diff_thresholds": list(config.scoring.diff_thresholds),
            "file_thresholds": list(config.scoring.file_thresholds),
            "merge_time_thresholds": list(config.scoring.merge_time_thresholds),
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


def _is_quarter_cache_fresh(
    quarter_data: dict, quarter_end: str, enable_scoring: bool = False,
) -> bool:
    fetched = quarter_data.get("_meta", {}).get("fetched_date")
    if not fetched:
        return False
    if enable_scoring:
        for key, val in quarter_data.items():
            if key == "_meta":
                continue
            if isinstance(val, dict) and "story_points" not in val:
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
            futures["gl_reviews"] = pool.submit(fetch_gitlab_reviews, config.gitlab_url, eng.gitlab, q.start, q.end)

    gh_prs = futures["prs"].result() if "prs" in futures else 0
    gh_reviews = futures["reviews"].result() if "reviews" in futures else 0
    gl_reviews = futures["gl_reviews"].result() if "gl_reviews" in futures else 0
    gh_mt = futures["gh_mt"].result() if "gh_mt" in futures else []
    gl_mrs = futures["mrs"].result() if "mrs" in futures else 0
    gl_mt = futures["gl_mt"].result() if "gl_mt" in futures else []

    all_merge_times = gh_mt + gl_mt

    return EngineerQuarterMetrics(
        name=eng.name,
        quarter=q.label,
        github_prs=gh_prs,
        gitlab_mrs=gl_mrs,
        reviews=gh_reviews + gl_reviews,
        github_reviews=gh_reviews,
        merge_time_days=_median(all_merge_times),
        github_merge_times=gh_mt,
        gitlab_merge_times=gl_mt,
    )


def _fetch_engineer_data_scored(
    eng, config: TeamConfig, gitlab_ok: bool, q: Quarter,
) -> EngineerQuarterMetrics:
    from teamdash.models import PRDetail

    futures: dict[str, object] = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        if eng.github and config.github_orgs:
            futures["gh_details"] = pool.submit(fetch_pr_details, eng.github, config.github_orgs, q.start, q.end)
            futures["gh_reviews"] = pool.submit(fetch_reviews, eng.github, config.github_orgs, q.start, q.end)
            futures["gh_reviewed"] = pool.submit(fetch_reviewed_pr_details, eng.github, config.github_orgs, q.start, q.end)
        if eng.gitlab and config.gitlab_url and gitlab_ok:
            futures["gl_details"] = pool.submit(fetch_mr_details, config.gitlab_url, eng.gitlab, q.start, q.end)
            futures["gl_reviews"] = pool.submit(fetch_gitlab_reviews, config.gitlab_url, eng.gitlab, q.start, q.end)
            futures["gl_reviewed"] = pool.submit(fetch_reviewed_gl_details, config.gitlab_url, eng.gitlab, q.start, q.end)

    all_details: list[PRDetail] = []
    if "gh_details" in futures:
        all_details.extend(futures["gh_details"].result())
    if "gl_details" in futures:
        all_details.extend(futures["gl_details"].result())

    gh_reviews = futures["gh_reviews"].result() if "gh_reviews" in futures else 0
    gl_reviews = futures["gl_reviews"].result() if "gl_reviews" in futures else 0

    reviewed_details: list[PRDetail] = []
    if "gh_reviewed" in futures:
        reviewed_details.extend(futures["gh_reviewed"].result())
    if "gl_reviewed" in futures:
        reviewed_details.extend(futures["gl_reviewed"].result())

    gh_prs = sum(1 for d in all_details if d.source == "github")
    gl_mrs = sum(1 for d in all_details if d.source == "gitlab")

    gh_mt = [d.merge_time_days for d in all_details if d.source == "github" and d.merge_time_days is not None]
    gl_mt = [d.merge_time_days for d in all_details if d.source == "gitlab" and d.merge_time_days is not None]
    all_merge_times = gh_mt + gl_mt

    scored = score_prs(all_details, config.scoring)
    sp = sum(s.points for s in scored)
    xl = sum(1 for s in scored if s.size == "XL")

    scored_reviews = score_prs(reviewed_details, config.scoring)
    review_sp = sum(s.points for s in scored_reviews)

    return EngineerQuarterMetrics(
        name=eng.name,
        quarter=q.label,
        github_prs=gh_prs,
        gitlab_mrs=gl_mrs,
        reviews=gh_reviews + gl_reviews,
        github_reviews=gh_reviews,
        merge_time_days=_median(all_merge_times),
        story_points=sp,
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
        github_reviews=cached_eng.get("_github_reviews", 0),
        merge_time_days=cached_eng.get("merge_time_days"),
        story_points=cached_eng.get("story_points", 0),
        xl_count=cached_eng.get("xl_count", 0),
        review_story_points=cached_eng.get("review_story_points", 0),
        github_merge_times=cached_eng.get("_github_merge_times", []),
        gitlab_merge_times=cached_eng.get("_gitlab_merge_times", []),
        verified_bugs=cached_eng.get("verified_bugs", 0),
    )


def _refresh_engineer_gitlab(
    eng, config: TeamConfig, gitlab_ok: bool, q: Quarter,
    cached_eng: dict, enable_scoring: bool,
) -> EngineerQuarterMetrics:
    print(f"  Refreshing GitLab {q.label} for {eng.name}...", file=sys.stderr)

    gh_prs = cached_eng["github_prs"]
    gh_reviews = cached_eng.get("_github_reviews", 0)
    gh_mt = cached_eng.get("_github_merge_times", [])

    if not enable_scoring:
        if eng.gitlab and config.gitlab_url and gitlab_ok:
            gl_mrs = fetch_mrs(config.gitlab_url, eng.gitlab, q.start, q.end)
            gl_mt: list[float] = fetch_mr_merge_times(config.gitlab_url, eng.gitlab, q.start, q.end)
            gl_reviews = fetch_gitlab_reviews(config.gitlab_url, eng.gitlab, q.start, q.end)
        else:
            gl_mrs = cached_eng.get("gitlab_mrs", 0)
            gl_mt = cached_eng.get("_gitlab_merge_times", [])
            gl_reviews = max(0, cached_eng.get("reviews", 0) - cached_eng.get("_github_reviews", 0))

        all_mt = gh_mt + gl_mt

        return EngineerQuarterMetrics(
            name=eng.name,
            quarter=q.label,
            github_prs=gh_prs,
            gitlab_mrs=gl_mrs,
            reviews=gh_reviews + gl_reviews,
            github_reviews=gh_reviews,
            merge_time_days=_median(all_mt) if all_mt else cached_eng.get("merge_time_days"),
            github_merge_times=gh_mt,
            gitlab_merge_times=gl_mt,
        )

    from teamdash.models import PRDetail

    gh_scored_summary = [
        s for s in cached_eng.get("scored_prs_summary", [])
        if "github.com" in s.get("url", "")
    ]
    gh_sp = sum(s["points"] for s in gh_scored_summary)
    gh_xl = sum(1 for s in gh_scored_summary if s.get("size") == "XL")
    gh_review_sp = cached_eng.get("review_story_points", 0)

    gl_details: list[PRDetail] = []
    gl_reviews = 0
    if eng.gitlab and config.gitlab_url and gitlab_ok:
        gl_details = fetch_mr_details(config.gitlab_url, eng.gitlab, q.start, q.end)
        gl_reviews = fetch_gitlab_reviews(config.gitlab_url, eng.gitlab, q.start, q.end)

    if gl_details:
        gl_scored = score_prs(gl_details, config.scoring)
        gl_sp = sum(s.points for s in gl_scored)
        gl_xl = sum(1 for s in gl_scored if s.size == "XL")
        gl_mt_scored = [d.merge_time_days for d in gl_details if d.merge_time_days is not None]
        gl_mrs_count = len(gl_details)
    elif not gitlab_ok:
        gl_scored_summary = [
            s for s in cached_eng.get("scored_prs_summary", [])
            if "github.com" not in s.get("url", "")
        ]
        gl_scored = []
        gl_sp = sum(s["points"] for s in gl_scored_summary)
        gl_xl = sum(1 for s in gl_scored_summary if s.get("size") == "XL")
        gl_mt_scored = cached_eng.get("_gitlab_merge_times", [])
        gl_mrs_count = cached_eng.get("gitlab_mrs", 0)
        gl_reviews = max(0, cached_eng.get("reviews", 0) - cached_eng.get("_github_reviews", 0))
    else:
        gl_scored = []
        gl_sp = 0
        gl_xl = 0
        gl_mt_scored = []
        gl_mrs_count = 0

    all_mt = gh_mt + gl_mt_scored

    return EngineerQuarterMetrics(
        name=eng.name,
        quarter=q.label,
        github_prs=gh_prs,
        gitlab_mrs=gl_mrs_count,
        reviews=gh_reviews + gl_reviews,
        github_reviews=gh_reviews,
        merge_time_days=_median(all_mt) if all_mt else cached_eng.get("merge_time_days"),
        story_points=gh_sp + gl_sp,
        scored_prs=gl_scored,
        xl_count=gh_xl + gl_xl,
        review_story_points=gh_review_sp,
        github_merge_times=gh_mt,
        gitlab_merge_times=gl_mt_scored,
    )


def _merge_cached_gitlab(
    metrics: EngineerQuarterMetrics, old: dict, enable_scoring: bool,
) -> list[dict]:
    """Patch freshly-fetched metrics with GitLab values from old cache entry.

    Returns GitLab scored_prs_summary entries for use as extra_scored_summary.
    """
    metrics.gitlab_mrs = old.get("gitlab_mrs", 0)
    metrics.gitlab_merge_times = old.get("_gitlab_merge_times", [])
    old_gl_reviews = max(0, old.get("reviews", 0) - old.get("_github_reviews", 0))
    metrics.reviews = metrics.github_reviews + old_gl_reviews
    all_mt = metrics.github_merge_times + metrics.gitlab_merge_times
    metrics.merge_time_days = _median(all_mt) if all_mt else None

    gl_scored_summary: list[dict] = []
    if enable_scoring:
        gl_scored_summary = [
            s for s in old.get("scored_prs_summary", [])
            if "github.com" not in s.get("url", "")
        ]
        metrics.story_points += sum(s["points"] for s in gl_scored_summary)
        metrics.xl_count += sum(1 for s in gl_scored_summary if s.get("size") == "XL")
    return gl_scored_summary


def _build_cache_entry(
    metrics: EngineerQuarterMetrics, enable_scoring: bool,
    extra_scored_summary: list[dict] | None = None,
) -> dict:
    entry: dict = {
        "github_prs": metrics.github_prs,
        "gitlab_mrs": metrics.gitlab_mrs,
        "reviews": metrics.reviews,
        "_github_reviews": metrics.github_reviews,
        "merge_time_days": metrics.merge_time_days,
        "_github_merge_times": metrics.github_merge_times,
        "_gitlab_merge_times": metrics.gitlab_merge_times,
        "verified_bugs": metrics.verified_bugs,
    }
    if enable_scoring:
        entry["story_points"] = metrics.story_points
        entry["xl_count"] = metrics.xl_count
        entry["review_story_points"] = metrics.review_story_points
        summary = [
            {
                "url": s.detail.url,
                "title": s.detail.title,
                "size": s.size,
                "points": s.points,
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
    jira_data: JiraData | None = None,
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
            jira_data=jira_data,
        )

    quarter_cached: dict[str, dict[str, EngineerQuarterMetrics]] = {}
    fetch_tasks: list[tuple] = []

    for q in quarters:
        cached_quarter = cache.get(q.label, {})
        quarter_fresh = _is_quarter_cache_fresh(cached_quarter, q.end, enable_scoring)
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
    with ThreadPoolExecutor(max_workers=4) as pool:
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
                metrics = quarter_cached[q.label][eng.name]
            else:
                metrics = fetched[(q.label, eng.name)]
                extra_scored: list[dict] | None = None
                if not gitlab_ok:
                    old_eng = cache.get(q.label, {}).get(eng.name)
                    if old_eng:
                        extra_scored = _merge_cached_gitlab(metrics, old_eng, enable_scoring) or None
                cache_entry = _build_cache_entry(
                    metrics, enable_scoring, extra_scored_summary=extra_scored,
                )
                q_cache = updated_cache.setdefault(q.label, {})
                q_cache[eng.name] = cache_entry
                q_cache["_meta"] = {"fetched_date": date.today().isoformat()}
            if jira_data:
                metrics.verified_bugs = jira_data.bugs.get(q.label, {}).get(eng.name, 0)
                metrics.activity_type_counts = jira_data.activity_types.get(q.label, {}).get(eng.name, {})
            engineer_metrics.append(metrics)
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
    jira_data: JiraData | None = None,
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

            if jira_data:
                metrics.verified_bugs = jira_data.bugs.get(q.label, {}).get(eng.name, 0)
                metrics.activity_type_counts = jira_data.activity_types.get(q.label, {}).get(eng.name, {})
            engineer_metrics.append(metrics)
            q_cache = updated_cache.setdefault(q.label, {})
            q_cache[eng.name] = cache_entry
            q_cache["_meta"] = {"fetched_date": date.today().isoformat()}

        summaries.append(QuarterSummary(quarter=q, engineers=engineer_metrics))

    _save_cache(config, updated_cache)
    return summaries
