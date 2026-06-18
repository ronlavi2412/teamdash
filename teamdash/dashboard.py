from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

from teamdash.config import TeamConfig
from teamdash.models import EngineerQuarterMetrics, QuarterSummary


COLORS = [
    "#f59e0b", "#3b82f6", "#8b5cf6", "#ec4899",
    "#06b6d4", "#10b981", "#ef4444", "#14b8a6",
    "#6366f1", "#d946ef", "#0ea5e9", "#84cc16",
]


def _pct(new: float, old: float) -> str:
    if old == 0:
        return "+999%" if new > 0 else "0%"
    delta = round((new - old) / old * 100)
    return f"+{delta}%" if delta >= 0 else f"{delta}%"


def _delta_class(new: float, old: float, lower_is_better: bool = False) -> str:
    if old == 0:
        cls = "up" if new > 0 else "flat"
    else:
        delta = (new - old) / old
        if delta > 0.01:
            cls = "up"
        elif delta < -0.01:
            cls = "down"
        else:
            cls = "flat"
    if lower_is_better and cls in ("up", "down"):
        cls = "down" if cls == "up" else "up"
    return cls


def _size_dist(eng: EngineerQuarterMetrics) -> dict[str, int]:
    counts = {"XS": 0, "S": 0, "M": 0, "L": 0, "XL": 0}
    for sp in eng.scored_prs:
        if sp.size in counts:
            counts[sp.size] += 1
    return counts


def _zero(name: str, quarter: str) -> EngineerQuarterMetrics:
    return EngineerQuarterMetrics(name=name, quarter=quarter)


def _build_table_row_data(
    summaries: list[QuarterSummary],
    names: list[str],
    has_scoring: bool,
) -> list[dict]:
    cur = summaries[-1]
    prev = summaries[-2] if len(summaries) >= 2 else cur

    rows = []
    for name in names:
        quarters = []
        for s in summaries:
            by_name = {e.name: e for e in s.engineers}
            eng = by_name.get(name)
            quarters.append({
                "total": eng.total if eng else 0,
                "github_prs": eng.github_prs if eng else 0,
                "gitlab_mrs": eng.gitlab_mrs if eng else 0,
                "reviews": eng.reviews if eng else 0,
                "merge_time": eng.merge_time_days if eng else None,
                "story_points": eng.story_points if eng else 0,
                "review_story_points": eng.review_story_points if eng else 0,
                "verified_bugs": eng.verified_bugs if eng else 0,
                "activity_type_counts": eng.activity_type_counts if eng else {},
            })

        cur_eng = {e.name: e for e in cur.engineers}.get(name)
        prev_eng = {e.name: e for e in prev.engineers}.get(name)
        cur_total = cur_eng.total if cur_eng else 0
        prev_total = prev_eng.total if prev_eng else 0
        growth = _pct(cur_total, prev_total) if prev != cur else "-"

        rows.append({
            "name": name,
            "quarters": quarters,
            "growth": growth,
        })
    return rows


def _build_config_data(config: TeamConfig, has_scoring: bool) -> dict:
    data: dict = {
        "github_orgs": config.github_orgs,
        "gitlab_url": config.gitlab_url,
        "jira_cloud_id": config.jira.cloud_id if config.jira else None,
        "jira_project_keys": config.jira.project_keys if config.jira else [],
        "engineers": [
            {"name": e.name, "github": e.github, "gitlab": e.gitlab}
            for e in config.engineers
        ],
        "scoring": None,
    }
    if has_scoring:
        sc = config.scoring
        data["scoring"] = {
            "size_points": sc.size_points,
            "diff_thresholds": list(sc.diff_thresholds),
            "file_thresholds": list(sc.file_thresholds),
            "merge_time_thresholds": list(sc.merge_time_thresholds),
        }
    return data


def build_dashboard_data(
    config: TeamConfig,
    summaries: list[QuarterSummary],
) -> dict:
    names = [e.name for e in summaries[0].engineers]
    colors = [COLORS[i % len(COLORS)] for i in range(len(names))]

    first_q = summaries[0].quarter
    last_q = summaries[-1].quarter
    title = f"{config.team_name} &mdash; {first_q.label} to {last_q.label}"
    subtitle = f"{len(summaries)} quarters ({first_q.start} to {last_q.end})"
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")

    has_scoring = any(s.total_story_points > 0 for s in summaries)
    has_jira = any(e.verified_bugs > 0 for s in summaries for e in s.engineers)
    has_activity_types = any(
        e.activity_type_counts for s in summaries for e in s.engineers
    )
    activity_type_names = sorted({
        at for s in summaries for e in s.engineers
        for at in e.activity_type_counts
    })

    today = date.today()
    is_current_quarter = date.fromisoformat(last_q.end) >= today
    current_quarter_index = len(summaries) - 1 if is_current_quarter else -1

    quarters = []
    for s in summaries:
        by_name = {e.name: e for e in s.engineers}
        quarters.append({
            "label": s.quarter.short_label,
            "gh_prs": [by_name.get(n, _zero(n, s.quarter.label)).github_prs for n in names],
            "gl_mrs": [by_name.get(n, _zero(n, s.quarter.label)).gitlab_mrs for n in names],
            "reviews": [by_name.get(n, _zero(n, s.quarter.label)).reviews for n in names],
            "merge_time": [by_name.get(n, _zero(n, s.quarter.label)).merge_time_days for n in names],
            "sp": [by_name.get(n, _zero(n, s.quarter.label)).story_points for n in names],
            "xl_count": [by_name.get(n, _zero(n, s.quarter.label)).xl_count for n in names],
            "review_sp": [by_name.get(n, _zero(n, s.quarter.label)).review_story_points for n in names],
            "size_dist": [_size_dist(by_name.get(n, _zero(n, s.quarter.label))) for n in names],
            "verified_bugs": [by_name.get(n, _zero(n, s.quarter.label)).verified_bugs for n in names],
            "activity_types": [by_name.get(n, _zero(n, s.quarter.label)).activity_type_counts for n in names],
        })

    return {
        "title": title,
        "subtitle": subtitle,
        "generated": generated,
        "names": names,
        "colors": colors,
        "quarters": quarters,
        "quarterLabels": [s.quarter.short_label for s in summaries],
        "currentQuarterIndex": current_quarter_index,
        "isCurrentQuarter": is_current_quarter,
        "hasScoring": has_scoring,
        "hasJira": has_jira,
        "hasActivityTypes": has_activity_types,
        "activityTypeNames": activity_type_names,
        "config": _build_config_data(config, has_scoring),
        "tableRows": _build_table_row_data(summaries, names, has_scoring),
    }


def generate_dashboard(
    config: TeamConfig,
    summaries: list[QuarterSummary],
    output_path: str,
) -> None:
    data = build_dashboard_data(config, summaries)
    generate_dashboard_from_data(data, output_path)


def generate_dashboard_from_data(data: dict, output_path: str) -> None:
    dist_dir = Path(__file__).parent.parent / "dashboard" / "dist"
    js_path = dist_dir / "dashboard.js"
    css_path = dist_dir / "dashboard.css"

    if not js_path.exists():
        print(
            "[ERROR] React dashboard not built. Run: cd dashboard && npm run build",
            file=sys.stderr,
        )
        sys.exit(1)

    js_bundle = js_path.read_text()
    css_bundle = css_path.read_text() if css_path.exists() else ""

    html = _REACT_HTML_TEMPLATE.format(
        title_text=data["title"],
        dashboard_data_json=json.dumps(data),
        css_bundle=css_bundle,
        js_bundle=js_bundle,
    )

    with open(output_path, "w") as f:
        f.write(html)


_REACT_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title_text}</title>
    <style>{css_bundle}</style>
</head>
<body>
    <div id="root"></div>
    <script>
        window.__DASHBOARD_DATA__ = {dashboard_data_json};
    </script>
    <script>{js_bundle}</script>
</body>
</html>
"""
