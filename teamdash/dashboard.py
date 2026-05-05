from __future__ import annotations

from datetime import datetime

from teamdash.config import TeamConfig
from teamdash.models import EngineerQuarterMetrics, QuarterSummary
from teamdash.scoring import ScoringConfig


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


def _build_data_block(summaries: list[QuarterSummary], names: list[str]) -> str:
    def fmt(arr: list) -> str:
        return "[" + ", ".join("null" if v is None else str(v) for v in arr) + "]"

    def fmt_dists(dists: list[dict[str, int]]) -> str:
        parts = []
        for d in dists:
            parts.append("{" + ", ".join(f'{k}: {v}' for k, v in d.items()) + "}")
        return "[" + ", ".join(parts) + "]"

    q_entries = []
    for s in summaries:
        by_name = {e.name: e for e in s.engineers}
        gh = [by_name.get(n, _zero(n, s.quarter.label)).github_prs for n in names]
        gl = [by_name.get(n, _zero(n, s.quarter.label)).gitlab_mrs for n in names]
        rv = [by_name.get(n, _zero(n, s.quarter.label)).reviews for n in names]
        mt = [by_name.get(n, _zero(n, s.quarter.label)).merge_time_days for n in names]
        sp = [by_name.get(n, _zero(n, s.quarter.label)).story_points for n in names]
        xl = [by_name.get(n, _zero(n, s.quarter.label)).xl_count for n in names]
        review_sp = [by_name.get(n, _zero(n, s.quarter.label)).review_story_points for n in names]
        dists = [_size_dist(by_name.get(n, _zero(n, s.quarter.label))) for n in names]
        q_entries.append(
            f'    {{ label: "{s.quarter.short_label}",'
            f' gh_prs: {fmt(gh)}, gl_mrs: {fmt(gl)}, reviews: {fmt(rv)},'
            f' merge_time: {fmt(mt)},'
            f' sp: {fmt(sp)}, xl_count: {fmt(xl)},'
            f' review_sp: {fmt(review_sp)},'
            f' size_dist: {fmt_dists(dists)} }}'
        )

    return "const Q = [\n" + ",\n".join(q_entries) + "\n];"


def _zero(name, quarter):
    from teamdash.models import EngineerQuarterMetrics
    return EngineerQuarterMetrics(name=name, quarter=quarter)


def _build_summary_cards(summaries: list[QuarterSummary]) -> str:
    return ""


def _build_table_rows(summaries: list[QuarterSummary], names: list[str], has_scoring: bool = False) -> str:
    rows = []
    cur = summaries[-1]
    prev = summaries[-2] if len(summaries) >= 2 else cur

    for name in names:
        cells = [f"<td><strong>{name}</strong></td>"]
        for s in summaries:
            by_name = {e.name: e for e in s.engineers}
            eng = by_name.get(name)
            total = eng.total if eng else 0
            cells.append(f'<td class="num">{total}</td>')

        cur_eng = {e.name: e for e in cur.engineers}.get(name)
        prev_eng = {e.name: e for e in prev.engineers}.get(name)
        cur_total = cur_eng.total if cur_eng else 0
        prev_total = prev_eng.total if prev_eng else 0
        growth = _pct(cur_total, prev_total) if prev != cur else "-"
        cells.append(f'<td class="num">{growth}</td>')

        for s in summaries:
            by_name = {e.name: e for e in s.engineers}
            eng = by_name.get(name)
            cells.append(f'<td class="num">{eng.github_prs if eng else 0}</td>')

        for s in summaries:
            by_name = {e.name: e for e in s.engineers}
            eng = by_name.get(name)
            cells.append(f'<td class="num">{eng.gitlab_mrs if eng else 0}</td>')

        for s in summaries:
            by_name = {e.name: e for e in s.engineers}
            eng = by_name.get(name)
            cells.append(f'<td class="num">{eng.reviews if eng else 0}</td>')

        for s in summaries:
            by_name = {e.name: e for e in s.engineers}
            eng = by_name.get(name)
            mt = eng.merge_time_days if eng else None
            cells.append(f'<td class="num">{mt if mt is not None else "-"}</td>')

        if has_scoring:
            for s in summaries:
                by_name = {e.name: e for e in s.engineers}
                eng = by_name.get(name)
                cells.append(f'<td class="num">{eng.story_points if eng else 0}</td>')

        rows.append("<tr>" + "".join(cells) + "</tr>")

    return "\n                            ".join(rows)


def _build_table_headers(summaries: list[QuarterSummary], has_scoring: bool = False) -> str:
    headers = ['<th>Engineer</th>']
    for s in summaries:
        headers.append(f'<th data-type="num">PRs+MRs {s.quarter.short_label} <span class="sort-arrow"></span></th>')
    headers.append('<th data-type="num">Growth <span class="sort-arrow"></span></th>')
    for s in summaries:
        headers.append(f'<th data-type="num">GH PRs {s.quarter.short_label} <span class="sort-arrow"></span></th>')
    for s in summaries:
        headers.append(f'<th data-type="num">GL MRs {s.quarter.short_label} <span class="sort-arrow"></span></th>')
    for s in summaries:
        headers.append(f'<th data-type="num">Reviews {s.quarter.short_label} <span class="sort-arrow"></span></th>')
    for s in summaries:
        headers.append(f'<th data-type="num">Merge days {s.quarter.short_label} <span class="sort-arrow"></span></th>')
    if has_scoring:
        for s in summaries:
            headers.append(f'<th data-type="num">Complexity {s.quarter.short_label} <span class="sort-arrow"></span></th>')
    return "\n                                ".join(headers)


def _build_sp_tab(summaries: list[QuarterSummary], names: list[str]) -> str:
    xl_prs = []
    if summaries:
        latest = summaries[-1]
        for eng in latest.engineers:
            for sp in eng.scored_prs:
                if sp.size == "XL":
                    xl_prs.append((eng.name, sp.detail.url))

    xl_html = ""
    if xl_prs:
        rows = "\n".join(
            f'                        <tr><td>{name}</td><td><a href="{url}" target="_blank">{url}</a></td></tr>'
            for name, url in xl_prs
        )
        xl_html = f"""
            <div class="chart-card full">
                <h3>XL PRs — Consider Splitting</h3>
                <table class="data-table">
                    <thead><tr><th>Engineer</th><th>PR URL</th></tr></thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
            </div>"""

    return f"""
        <div id="tab-storypoints" class="tab-content">
            <div class="chart-row">
                <div class="chart-card">
                    <h3>Complexity Velocity per Quarter</h3>
                    <div class="chart-wrap"><canvas id="chart-sp-velocity"></canvas></div>
                </div>
                <div class="chart-card">
                    <h3>Size Distribution (Latest Quarter)</h3>
                    <div class="chart-wrap"><canvas id="chart-size-dist"></canvas></div>
                </div>
            </div>{xl_html}
        </div>"""


def _build_team_tab(has_scoring: bool) -> str:
    sp_chart = ""
    review_sp_chart = ""
    if has_scoring:
        sp_chart = """
                <div class="chart-card">
                    <h3>Total Complexity per Quarter <span class="chart-info" data-tooltip="Sum of complexity scores across all team members. Each merged PR is sized XS–XL based on diff size, files changed, review friction, and merge time, then mapped to points (XS=2, S=5, M=8, L=13, XL=21).">i</span></h3>
                    <div class="chart-wrap"><canvas id="chart-team-sp"></canvas></div>
                </div>"""
        review_sp_chart = """
                <div class="chart-card">
                    <h3>Total Review Complexity per Quarter <span class="chart-info" data-tooltip="Sum of complexity scores for merged PRs reviewed by team members, scored the same way as authored PRs.">i</span></h3>
                    <div class="chart-wrap"><canvas id="chart-team-review-sp"></canvas></div>
                </div>"""

    return f"""
        <div id="tab-team" class="tab-content active">
            <div class="chart-row">
                <div class="chart-card">
                    <h3>Total PRs + MRs per Quarter <span class="chart-info" data-tooltip="Sum of GitHub PRs and GitLab MRs merged during the quarter across all team members.">i</span></h3>
                    <div class="chart-wrap"><canvas id="chart-team-prs"></canvas></div>
                </div>
                <div class="chart-card">
                    <h3>Total Reviews per Quarter <span class="chart-info" data-tooltip="Total merged PRs reviewed by team members during the quarter. Excludes self-reviews.">i</span></h3>
                    <div class="chart-wrap"><canvas id="chart-team-reviews"></canvas></div>
                </div>
            </div>
            <div class="chart-row">{sp_chart}{review_sp_chart}
                <div class="chart-card">
                    <h3>Median Merge Time per Quarter (days) <span class="chart-info" data-tooltip="Median days from PR/MR creation to merge across all team members for the quarter.">i</span></h3>
                    <div class="chart-wrap"><canvas id="chart-team-merge-time"></canvas></div>
                </div>
            </div>
        </div>"""


def _build_config_tab(config: TeamConfig, has_scoring: bool) -> str:
    sources_rows = ""
    if config.github_orgs:
        orgs = ", ".join(config.github_orgs)
        sources_rows += f'<tr><td><strong>GitHub Organizations</strong></td><td>{orgs}</td></tr>\n'
    if config.gitlab_url:
        sources_rows += f'<tr><td><strong>GitLab Instance</strong></td><td>{config.gitlab_url}</td></tr>\n'
    if not sources_rows:
        sources_rows = '<tr><td colspan="2">No data sources configured</td></tr>'

    engineer_rows = ""
    for eng in config.engineers:
        gh = eng.github or "-"
        gl = eng.gitlab or "-"
        engineer_rows += f"<tr><td>{eng.name}</td><td>{gh}</td><td>{gl}</td></tr>\n"

    scoring_html = ""
    if has_scoring:
        sc = config.scoring
        sp_rows = "".join(
            f"<tr><td>{size}</td><td>{sc.size_points.get(size, 0)}</td></tr>"
            for size in ("XS", "S", "M", "L", "XL")
        )
        diff_th = ", ".join(str(t) for t in sc.diff_thresholds)
        file_th = ", ".join(str(t) for t in sc.file_thresholds)
        merge_th = ", ".join(str(t) for t in sc.merge_time_thresholds)

        scoring_html = f"""
            <div class="chart-card full">
                <h3>Scoring Configuration</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px;">
                    <div>
                        <h4 style="margin-bottom: 8px; font-size: 0.9rem; color: var(--text-muted);">Complexity Points per Size</h4>
                        <table class="data-table">
                            <thead><tr><th>Size</th><th>Points</th></tr></thead>
                            <tbody>{sp_rows}</tbody>
                        </table>
                    </div>
                    <div>
                        <h4 style="margin-bottom: 8px; font-size: 0.9rem; color: var(--text-muted);">Classification Thresholds</h4>
                        <table class="data-table">
                            <thead><tr><th>Signal</th><th>Thresholds (XS/S/M/L boundary)</th></tr></thead>
                            <tbody>
                                <tr><td>Lines changed</td><td>{diff_th}</td></tr>
                                <tr><td>Files changed</td><td>{file_th}</td></tr>
                                <tr><td>Merge time (days)</td><td>{merge_th}</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>"""

    return f"""
        <div id="tab-config" class="tab-content">
            <div class="chart-row">
                <div class="chart-card">
                    <h3>Data Sources</h3>
                    <table class="data-table">
                        <thead><tr><th>Source</th><th>Value</th></tr></thead>
                        <tbody>{sources_rows}</tbody>
                    </table>
                </div>
                <div class="chart-card">
                    <h3>Team Members</h3>
                    <table class="data-table">
                        <thead><tr><th>Name</th><th>GitHub</th><th>GitLab</th></tr></thead>
                        <tbody>{engineer_rows}</tbody>
                    </table>
                </div>
            </div>{scoring_html}
        </div>"""


def generate_dashboard(
    config: TeamConfig,
    summaries: list[QuarterSummary],
    output_path: str,
) -> None:
    team_name = config.team_name
    names = [e.name for e in summaries[0].engineers]
    colors_js = "[" + ", ".join(f'"{COLORS[i % len(COLORS)]}"' for i in range(len(names))) + "]"
    names_js = "[" + ", ".join(f'"{n}"' for n in names) + "]"

    first_q = summaries[0].quarter
    last_q = summaries[-1].quarter
    title = f"{team_name} &mdash; {first_q.label} to {last_q.label}"
    subtitle = f"{len(summaries)} quarters ({first_q.start} to {last_q.end})"
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")

    has_scoring = any(s.total_story_points > 0 for s in summaries)

    # Detect if last quarter is current (in-progress)
    from datetime import date
    today = date.today()
    is_current_quarter = date.fromisoformat(last_q.end) >= today
    current_quarter_index = len(summaries) - 1 if is_current_quarter else -1

    in_progress_note = (
        '<p style="text-align: center; color: var(--text-muted); font-size: 0.85rem; margin-top: 8px;">'
        '<em>* Striped bars and dashed lines indicate in-progress quarter with incomplete data</em></p>'
        if is_current_quarter else ""
    )

    data_block = _build_data_block(summaries, names)
    summary_cards = _build_summary_cards(summaries)
    team_tab = _build_team_tab(has_scoring)
    config_tab = _build_config_tab(config, has_scoring)
    table_headers = _build_table_headers(summaries, has_scoring=has_scoring)
    table_rows = _build_table_rows(summaries, names, has_scoring=has_scoring)
    html = HTML_TEMPLATE.format(
        title=title,
        subtitle=subtitle,
        generated=generated,
        data_block=data_block,
        summary_cards=summary_cards,
        team_tab=team_tab,
        config_tab=config_tab,
        names_js=names_js,
        colors_js=colors_js,
        table_headers=table_headers,
        table_rows=table_rows,
        num_engineers=len(names),
        has_scoring="true" if has_scoring else "false",
        current_quarter_index=current_quarter_index,
        is_current_quarter="true" if is_current_quarter else "false",
        in_progress_note=in_progress_note,
    )

    with open(output_path, "w") as f:
        f.write(html)


HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    <style>
        :root {{
            --bg: #f8fafc;
            --surface: #ffffff;
            --border: #e2e8f0;
            --text: #1e293b;
            --text-muted: #64748b;
            --accent: #3b82f6;
            --positive: #10b981;
            --negative: #ef4444;
            --neutral: #94a3b8;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text); }}
        .header {{ background: linear-gradient(135deg, #1e293b 0%, #334155 100%); color: white; padding: 32px 40px; }}
        .header h1 {{ font-size: 1.75rem; font-weight: 700; }}
        .header p {{ color: #94a3b8; margin-top: 4px; font-size: 0.9rem; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 24px; }}

        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 32px; }}
        .summary-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 20px; }}
        .summary-card .label {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); font-weight: 600; }}
        .summary-card .value {{ font-size: 2rem; font-weight: 700; margin: 4px 0; }}
        .summary-card .delta {{ font-size: 0.85rem; font-weight: 600; }}
        .delta.up {{ color: var(--positive); }}
        .delta.down {{ color: var(--negative); }}
        .delta.flat {{ color: var(--neutral); }}

        .tabs {{ display: flex; gap: 4px; border-bottom: 2px solid var(--border); margin-bottom: 24px; overflow-x: auto; }}
        .tab {{ padding: 10px 20px; cursor: pointer; font-weight: 500; color: var(--text-muted); border-bottom: 2px solid transparent; margin-bottom: -2px; white-space: nowrap; font-size: 0.9rem; transition: all 0.15s; }}
        .tab:hover {{ color: var(--text); }}
        .tab.active {{ color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}

        .chart-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px; }}
        .chart-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 24px; }}
        .chart-card h3 {{ font-size: 1rem; font-weight: 600; margin-bottom: 16px; color: var(--text); }}
        .chart-card.full {{ grid-column: 1 / -1; }}
        .chart-wrap {{ position: relative; height: 350px; }}

        .data-table {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; }}
        .data-table thead {{ background: #f1f5f9; }}
        .data-table th {{ padding: 12px 16px; text-align: left; font-weight: 600; color: var(--text-muted); cursor: pointer; user-select: none; white-space: nowrap; border-bottom: 2px solid var(--border); }}
        .data-table th:hover {{ color: var(--text); }}
        .data-table th .sort-arrow {{ margin-left: 4px; font-size: 0.7rem; }}
        .data-table td {{ padding: 10px 16px; border-bottom: 1px solid var(--border); }}
        .data-table td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
        .data-table tbody tr:hover {{ background: #f8fafc; }}

        .chart-info {{ display: inline-block; position: relative; margin-left: 6px; width: 18px; height: 18px; line-height: 18px; text-align: center; border-radius: 50%; background: var(--border); color: var(--text-muted); font-size: 0.7rem; font-weight: 700; font-style: normal; cursor: help; vertical-align: middle; }}
        .chart-info::after {{ content: attr(data-tooltip); position: absolute; left: 50%; top: 100%; transform: translateX(-50%); margin-top: 8px; background: var(--text); color: #fff; font-size: 0.8rem; font-weight: 400; line-height: 1.4; padding: 8px 12px; border-radius: 6px; white-space: normal; width: 280px; pointer-events: none; opacity: 0; transition: opacity 0.15s; z-index: 100; }}
        .chart-info:hover::after {{ opacity: 1; }}

        .footer {{ text-align: center; padding: 24px; color: var(--text-muted); font-size: 0.8rem; }}

        /* Engineer Filter Styles */
        .filter-bar {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 24px; }}
        .filter-dropdown {{ position: relative; display: inline-block; }}
        .filter-button {{ display: flex; align-items: center; gap: 8px; padding: 10px 16px; background: var(--surface); border: 1px solid var(--border); border-radius: 6px; font-family: inherit; font-size: 0.9rem; font-weight: 500; color: var(--text); cursor: pointer; transition: all 0.15s; }}
        .filter-button:hover {{ border-color: var(--accent); background: var(--bg); }}
        .filter-icon {{ font-size: 1rem; }}
        .filter-count {{ display: inline-flex; align-items: center; justify-content: center; min-width: 20px; height: 20px; padding: 0 6px; background: var(--accent); color: white; font-size: 0.75rem; font-weight: 600; border-radius: 10px; }}
        .dropdown-arrow {{ font-size: 0.7rem; transition: transform 0.15s; }}
        .filter-dropdown.open .dropdown-arrow {{ transform: rotate(180deg); }}
        .filter-panel {{ display: none; position: absolute; top: calc(100% + 4px); left: 0; min-width: 300px; max-width: 400px; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); z-index: 1000; }}
        .filter-dropdown.open .filter-panel {{ display: block; }}
        .filter-actions {{ display: flex; gap: 8px; padding: 12px; border-bottom: 1px solid var(--border); }}
        .filter-action-btn {{ flex: 1; padding: 6px 12px; background: var(--bg); border: 1px solid var(--border); border-radius: 4px; font-family: inherit; font-size: 0.8rem; font-weight: 500; color: var(--text); cursor: pointer; transition: all 0.15s; }}
        .filter-action-btn:hover {{ background: var(--surface); border-color: var(--accent); }}
        .filter-search {{ padding: 12px; border-bottom: 1px solid var(--border); }}
        .filter-search input {{ width: 100%; padding: 8px 12px; border: 1px solid var(--border); border-radius: 4px; font-family: inherit; font-size: 0.85rem; color: var(--text); background: var(--bg); }}
        .filter-search input:focus {{ outline: none; border-color: var(--accent); }}
        .filter-list {{ max-height: 300px; overflow-y: auto; padding: 8px; }}
        .filter-checkbox {{ display: flex; align-items: center; padding: 8px 12px; cursor: pointer; border-radius: 4px; transition: background 0.15s; }}
        .filter-checkbox:hover {{ background: var(--bg); }}
        .filter-checkbox input[type="checkbox"] {{ margin-right: 10px; width: 16px; height: 16px; cursor: pointer; }}
        .filter-checkbox label {{ flex: 1; cursor: pointer; font-size: 0.85rem; user-select: none; }}
        .filter-checkbox.hidden {{ display: none; }}
        .engineer-color-dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-left: 6px; vertical-align: middle; }}

        @media (max-width: 768px) {{
            .chart-row {{ grid-template-columns: 1fr; }}
            .header {{ padding: 24px 20px; }}
            .container {{ padding: 16px; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        <p>{subtitle} &middot; Generated {generated}</p>
        {in_progress_note}
    </div>
    <div class="container">
        {summary_cards}

        <div class="tabs">
            <div class="tab active" onclick="switchTab('team')">Overall Team View</div>
            <div class="tab" onclick="switchTab('overview')">Detailed View</div>
            <div class="tab" onclick="switchTab('table')">Full Table</div>
            <div class="tab" onclick="switchTab('config')">Configuration</div>
        </div>

        {team_tab}

        <div id="tab-overview" class="tab-content">
            <!-- Engineer Filter Section -->
            <div class="filter-bar">
                <div class="filter-dropdown">
                    <button class="filter-button" id="engineer-filter-btn">
                        <span class="filter-icon">👤</span>
                        <span id="filter-label">All Engineers</span>
                        <span class="filter-count" id="filter-count"></span>
                        <span class="dropdown-arrow">▼</span>
                    </button>
                    <div class="filter-panel" id="engineer-filter-panel">
                        <div class="filter-actions">
                            <button class="filter-action-btn" id="select-all-btn">Select All</button>
                            <button class="filter-action-btn" id="clear-all-btn">Clear All</button>
                        </div>
                        <div class="filter-search">
                            <input type="text" id="engineer-search" placeholder="Search engineers..." />
                        </div>
                        <div class="filter-list" id="engineer-filter-list">
                            <!-- Checkboxes generated dynamically via JavaScript -->
                        </div>
                    </div>
                </div>
            </div>

            <div class="chart-row">
                <div class="chart-card">
                    <h3>PRs + MRs per Quarter <span class="chart-info" data-tooltip="GitHub PRs and GitLab MRs merged per engineer during the quarter.">i</span></h3>
                    <div class="chart-wrap"><canvas id="chart-prs-trend"></canvas></div>
                </div>
                <div class="chart-card">
                    <h3>Code Reviews per Quarter <span class="chart-info" data-tooltip="Merged PRs reviewed per engineer during the quarter. Excludes self-reviews.">i</span></h3>
                    <div class="chart-wrap"><canvas id="chart-reviews-trend"></canvas></div>
                </div>
            </div>
            <div class="chart-row">
                <div class="chart-card" id="overview-complexity" style="display:none;">
                    <h3>Complexity per Quarter <span class="chart-info" data-tooltip="Complexity score per engineer. Each merged PR is sized XS–XL by taking the max of: diff size, files changed, review friction, and merge time signals. Size labels on PRs override the calculation.">i</span></h3>
                    <div class="chart-wrap"><canvas id="chart-complexity-trend"></canvas></div>
                </div>
                <div class="chart-card" id="overview-review-complexity" style="display:none;">
                    <h3>Review Complexity per Quarter <span class="chart-info" data-tooltip="Complexity of merged PRs reviewed per engineer, scored identically to authored PRs.">i</span></h3>
                    <div class="chart-wrap"><canvas id="chart-review-complexity-trend"></canvas></div>
                </div>
            </div>
            <div class="chart-row">
                <div class="chart-card">
                    <h3>Median Merge Time per Quarter (days) <span class="chart-info" data-tooltip="Median days from PR/MR creation to merge per engineer for the quarter.">i</span></h3>
                    <div class="chart-wrap"><canvas id="chart-merge-time-trend"></canvas></div>
                </div>
            </div>
        </div>

        <div id="tab-table" class="tab-content">
            <div class="chart-card full">
                <div style="overflow-x: auto;">
                    <table class="data-table" id="main-table">
                        <thead>
                            <tr>
                                {table_headers}
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        {config_tab}
    </div>

    <div class="footer">Generated by teamdash &middot; {generated}</div>

    <script>
        const names = {names_js};
        const colors = {colors_js};
        {data_block}
        const cur = Q[Q.length - 1];
        const currentQuarterIndex = {current_quarter_index};
        const isCurrentQuarter = {is_current_quarter};

        function createStripePattern(baseColor) {{
            const canvas = document.createElement('canvas');
            canvas.width = 8;
            canvas.height = 8;
            const ctx = canvas.getContext('2d');

            // Background (lighter version of base color)
            ctx.fillStyle = baseColor + '40'; // 25% opacity
            ctx.fillRect(0, 0, 8, 8);

            // Diagonal stripes
            ctx.strokeStyle = baseColor;
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(0, 8);
            ctx.lineTo(8, 0);
            ctx.moveTo(-2, 2);
            ctx.lineTo(2, -2);
            ctx.moveTo(6, 10);
            ctx.lineTo(10, 6);
            ctx.stroke();

            return ctx.createPattern(canvas, 'repeat');
        }}

        function switchTab(id) {{
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
            document.getElementById('tab-' + id).classList.add('active');
            event.target.classList.add('active');
        }}

        // Store chart instances for filtering
        const detailViewCharts = {{}};

        // PRs+MRs trend
        detailViewCharts.prs = new Chart(document.getElementById('chart-prs-trend'), {{
            type: 'line',
            data: {{
                labels: Q.map((q, idx) => isCurrentQuarter && idx === currentQuarterIndex ? q.label + ' *' : q.label),
                datasets: names.map((name, i) => ({{
                    label: name,
                    data: Q.map(q => q.gh_prs[i] + q.gl_mrs[i]),
                    borderColor: colors[i],
                    backgroundColor: colors[i] + '20',
                    tension: 0.3,
                    fill: false,
                    pointRadius: 4,
                    segment: {{
                        borderDash: ctx => {{
                            if (isCurrentQuarter && ctx.p1DataIndex === currentQuarterIndex) {{
                                return [5, 5];
                            }}
                            return [];
                        }}
                    }}
                }})),
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ position: 'bottom', labels: {{ usePointStyle: true }} }} }},
                scales: {{ y: {{ beginAtZero: true, ticks: {{ stepSize: 5 }} }} }},
            }},
        }});

        // Reviews trend
        detailViewCharts.reviews = new Chart(document.getElementById('chart-reviews-trend'), {{
            type: 'line',
            data: {{
                labels: Q.map((q, idx) => isCurrentQuarter && idx === currentQuarterIndex ? q.label + ' *' : q.label),
                datasets: names.map((name, i) => ({{
                    label: name,
                    data: Q.map(q => q.reviews[i]),
                    borderColor: colors[i],
                    backgroundColor: colors[i] + '20',
                    tension: 0.3,
                    fill: false,
                    pointRadius: 4,
                    segment: {{
                        borderDash: ctx => {{
                            if (isCurrentQuarter && ctx.p1DataIndex === currentQuarterIndex) {{
                                return [5, 5];
                            }}
                            return [];
                        }}
                    }}
                }})),
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ position: 'bottom', labels: {{ usePointStyle: true }} }} }},
                scales: {{ y: {{ beginAtZero: true, ticks: {{ stepSize: 5 }} }} }},
            }},
        }});

        // Merge time trend
        detailViewCharts.mergeTime = new Chart(document.getElementById('chart-merge-time-trend'), {{
            type: 'line',
            data: {{
                labels: Q.map((q, idx) => isCurrentQuarter && idx === currentQuarterIndex ? q.label + ' *' : q.label),
                datasets: names.map((name, i) => ({{
                    label: name,
                    data: Q.map(q => q.merge_time[i]),
                    borderColor: colors[i],
                    backgroundColor: colors[i] + '20',
                    tension: 0.3,
                    fill: false,
                    pointRadius: 4,
                    spanGaps: true,
                    segment: {{
                        borderDash: ctx => {{
                            if (isCurrentQuarter && ctx.p1DataIndex === currentQuarterIndex) {{
                                return [5, 5];
                            }}
                            return [];
                        }}
                    }}
                }})),
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ position: 'bottom', labels: {{ usePointStyle: true }} }} }},
                scales: {{ y: {{ beginAtZero: true, max: 20, title: {{ display: true, text: 'Days' }} }} }},
            }},
        }});

        // Total complexity per quarter (overview tab)
        if ({has_scoring}) {{
            document.getElementById('overview-complexity').style.display = '';
            detailViewCharts.complexity = new Chart(document.getElementById('chart-complexity-trend'), {{
                type: 'line',
                data: {{
                    labels: Q.map((q, idx) => isCurrentQuarter && idx === currentQuarterIndex ? q.label + ' *' : q.label),
                    datasets: names.map((name, i) => ({{
                        label: name,
                        data: Q.map(q => q.sp[i]),
                        borderColor: colors[i],
                        backgroundColor: colors[i] + '20',
                        tension: 0.3,
                        fill: false,
                        pointRadius: 4,
                        segment: {{
                            borderDash: ctx => {{
                                if (isCurrentQuarter && ctx.p1DataIndex === currentQuarterIndex) {{
                                    return [5, 5];
                                }}
                                return [];
                            }}
                        }}
                    }})),
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{ legend: {{ position: 'bottom', labels: {{ usePointStyle: true }} }} }},
                    scales: {{ y: {{ beginAtZero: true, title: {{ display: true, text: 'Complexity Points' }} }} }},
                }},
            }});

            document.getElementById('overview-review-complexity').style.display = '';
            detailViewCharts.reviewComplexity = new Chart(document.getElementById('chart-review-complexity-trend'), {{
                type: 'line',
                data: {{
                    labels: Q.map((q, idx) => isCurrentQuarter && idx === currentQuarterIndex ? q.label + ' *' : q.label),
                    datasets: names.map((name, i) => ({{
                        label: name,
                        data: Q.map(q => q.review_sp[i]),
                        borderColor: colors[i],
                        backgroundColor: colors[i] + '20',
                        tension: 0.3,
                        fill: false,
                        pointRadius: 4,
                        segment: {{
                            borderDash: ctx => {{
                                if (isCurrentQuarter && ctx.p1DataIndex === currentQuarterIndex) {{
                                    return [5, 5];
                                }}
                                return [];
                            }}
                        }}
                    }})),
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{ legend: {{ position: 'bottom', labels: {{ usePointStyle: true }} }} }},
                    scales: {{ y: {{ beginAtZero: true, title: {{ display: true, text: 'Complexity Points' }} }} }},
                }},
            }});
        }}

        // Team view: Total PRs + MRs
        new Chart(document.getElementById('chart-team-prs'), {{
            type: 'bar',
            data: {{
                labels: Q.map((q, idx) => isCurrentQuarter && idx === currentQuarterIndex ? q.label + ' *' : q.label),
                datasets: [{{
                    label: 'Total PRs + MRs',
                    data: Q.map(q => q.gh_prs.reduce((a, b) => a + b, 0) + q.gl_mrs.reduce((a, b) => a + b, 0)),
                    backgroundColor: Q.map((q, idx) =>
                        idx === currentQuarterIndex && isCurrentQuarter
                            ? createStripePattern('#3b82f6')
                            : '#3b82f6'
                    ),
                    borderColor: '#2563eb',
                    borderWidth: 1,
                    borderRadius: 4,
                }}],
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{ y: {{ beginAtZero: true, ticks: {{ stepSize: 10 }} }} }},
            }},
        }});

        // Team view: Total Reviews
        new Chart(document.getElementById('chart-team-reviews'), {{
            type: 'bar',
            data: {{
                labels: Q.map((q, idx) => isCurrentQuarter && idx === currentQuarterIndex ? q.label + ' *' : q.label),
                datasets: [{{
                    label: 'Total Reviews',
                    data: Q.map(q => q.reviews.reduce((a, b) => a + b, 0)),
                    backgroundColor: Q.map((q, idx) =>
                        idx === currentQuarterIndex && isCurrentQuarter
                            ? createStripePattern('#8b5cf6')
                            : '#8b5cf6'
                    ),
                    borderColor: '#7c3aed',
                    borderWidth: 1,
                    borderRadius: 4,
                }}],
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{ y: {{ beginAtZero: true, ticks: {{ stepSize: 10 }} }} }},
            }},
        }});

        // Team view: Avg Merge Time
        new Chart(document.getElementById('chart-team-merge-time'), {{
            type: 'line',
            data: {{
                labels: Q.map((q, idx) => isCurrentQuarter && idx === currentQuarterIndex ? q.label + ' *' : q.label),
                datasets: [{{
                    label: 'Median Merge Time (days)',
                    data: Q.map(q => {{
                        const vals = q.merge_time.filter(v => v !== null).sort((a, b) => a - b);
                        if (!vals.length) return null;
                        const mid = Math.floor(vals.length / 2);
                        return +(vals.length % 2 ? vals[mid] : (vals[mid - 1] + vals[mid]) / 2).toFixed(1);
                    }}),
                    borderColor: '#ef4444',
                    backgroundColor: '#ef444420',
                    tension: 0.3,
                    fill: true,
                    pointRadius: 5,
                    pointBackgroundColor: '#ef4444',
                    spanGaps: true,
                    segment: {{
                        borderDash: ctx => {{
                            if (isCurrentQuarter && ctx.p1DataIndex === currentQuarterIndex) {{
                                return [5, 5];
                            }}
                            return [];
                        }}
                    }}
                }}],
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{ y: {{ beginAtZero: true, max: 20, title: {{ display: true, text: 'Days' }} }} }},
            }},
        }});

        // Team view: Total Complexity
        if ({has_scoring}) {{
            new Chart(document.getElementById('chart-team-sp'), {{
                type: 'bar',
                data: {{
                    labels: Q.map((q, idx) => isCurrentQuarter && idx === currentQuarterIndex ? q.label + ' *' : q.label),
                    datasets: [{{
                        label: 'Total Complexity',
                        data: Q.map(q => q.sp.reduce((a, b) => a + b, 0)),
                        backgroundColor: Q.map((q, idx) =>
                            idx === currentQuarterIndex && isCurrentQuarter
                                ? createStripePattern('#10b981')
                                : '#10b981'
                        ),
                        borderColor: '#059669',
                        borderWidth: 1,
                        borderRadius: 4,
                    }}],
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{ legend: {{ display: false }} }},
                    scales: {{ y: {{ beginAtZero: true, title: {{ display: true, text: 'Complexity Points' }} }} }},
                }},
            }});

            new Chart(document.getElementById('chart-team-review-sp'), {{
                type: 'bar',
                data: {{
                    labels: Q.map((q, idx) => isCurrentQuarter && idx === currentQuarterIndex ? q.label + ' *' : q.label),
                    datasets: [{{
                        label: 'Total Reviews Complexity',
                        data: Q.map(q => q.review_sp.reduce((a, b) => a + b, 0)),
                        backgroundColor: Q.map((q, idx) =>
                            idx === currentQuarterIndex && isCurrentQuarter
                                ? createStripePattern('#f59e0b')
                                : '#f59e0b'
                        ),
                        borderColor: '#d97706',
                        borderWidth: 1,
                        borderRadius: 4,
                    }}],
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{ legend: {{ display: false }} }},
                    scales: {{ y: {{ beginAtZero: true, title: {{ display: true, text: 'Complexity Points' }} }} }},
                }},
            }});
        }}

        // Engineer Filter Implementation
        let engineerSelection = new Set(names); // All engineers selected by default

        function initEngineerFilter() {{
            const filterList = document.getElementById('engineer-filter-list');
            const filterBtn = document.getElementById('engineer-filter-btn');
            const filterPanel = document.getElementById('engineer-filter-panel');
            const searchInput = document.getElementById('engineer-search');

            // Generate checkboxes for each engineer
            names.forEach((name, index) => {{
                const checkbox = document.createElement('div');
                checkbox.className = 'filter-checkbox';
                checkbox.dataset.index = index;
                checkbox.dataset.name = name.toLowerCase();

                checkbox.innerHTML = `
                    <input type="checkbox" id="engineer-${{index}}" checked>
                    <label for="engineer-${{index}}">
                        ${{name}}
                        <span class="engineer-color-dot" style="background-color: ${{colors[index]}}"></span>
                    </label>
                `;

                const input = checkbox.querySelector('input');
                input.addEventListener('change', () => handleEngineerToggle(name, input.checked));

                filterList.appendChild(checkbox);
            }});

            // Toggle dropdown
            filterBtn.addEventListener('click', (e) => {{
                e.stopPropagation();
                document.querySelector('.filter-dropdown').classList.toggle('open');
            }});

            // Close dropdown when clicking outside
            document.addEventListener('click', () => {{
                document.querySelector('.filter-dropdown').classList.remove('open');
            }});

            filterPanel.addEventListener('click', (e) => {{
                e.stopPropagation();
            }});

            // Search functionality
            searchInput.addEventListener('input', (e) => {{
                const query = e.target.value.toLowerCase();
                document.querySelectorAll('.filter-checkbox').forEach(checkbox => {{
                    const name = checkbox.dataset.name;
                    checkbox.classList.toggle('hidden', !name.includes(query));
                }});
            }});

            // Select All button
            document.getElementById('select-all-btn').addEventListener('click', () => {{
                engineerSelection.clear();
                names.forEach(name => engineerSelection.add(name));
                document.querySelectorAll('.filter-checkbox input').forEach(input => {{
                    input.checked = true;
                }});
                updateChartVisibility();
                updateFilterLabel();
            }});

            // Clear All button
            document.getElementById('clear-all-btn').addEventListener('click', () => {{
                engineerSelection.clear();
                document.querySelectorAll('.filter-checkbox input').forEach(input => {{
                    input.checked = false;
                }});
                updateChartVisibility();
                updateFilterLabel();
            }});

            updateFilterLabel();
        }}

        function handleEngineerToggle(name, isChecked) {{
            if (isChecked) {{
                engineerSelection.add(name);
            }} else {{
                engineerSelection.delete(name);
            }}
            updateChartVisibility();
            updateFilterLabel();
        }}

        function updateFilterLabel() {{
            const label = document.getElementById('filter-label');
            const count = document.getElementById('filter-count');
            const selectedCount = engineerSelection.size;

            if (selectedCount === names.length) {{
                label.textContent = 'All Engineers';
                count.textContent = '';
            }} else if (selectedCount === 0) {{
                label.textContent = 'No Engineers';
                count.textContent = '';
            }} else {{
                label.textContent = 'Engineers';
                count.textContent = selectedCount;
            }}
        }}

        function updateChartVisibility() {{
            // Update all detail view charts
            Object.values(detailViewCharts).forEach(chart => {{
                if (!chart) return; // Skip if chart doesn't exist

                chart.data.datasets.forEach((dataset, index) => {{
                    const engineerName = names[index];
                    dataset.hidden = !engineerSelection.has(engineerName);
                }});

                chart.update('none'); // 'none' animation mode for instant update
            }});
        }}

        // Initialize filter when page loads
        initEngineerFilter();

        // Table sorting
        document.querySelectorAll('#main-table th').forEach((th, colIdx) => {{
            th.addEventListener('click', () => {{
                const tbody = document.querySelector('#main-table tbody');
                const rows = Array.from(tbody.querySelectorAll('tr'));
                const isNum = th.dataset.type === 'num';
                const arrow = th.querySelector('.sort-arrow');
                const asc = arrow && arrow.textContent === '\\u25B2';

                document.querySelectorAll('#main-table th .sort-arrow').forEach(a => a.textContent = '');

                rows.sort((a, b) => {{
                    let va = a.cells[colIdx].textContent.trim();
                    let vb = b.cells[colIdx].textContent.trim();
                    if (isNum) {{
                        va = parseFloat(va.replace(/[^\\d.\\-]/g, '')) || 0;
                        vb = parseFloat(vb.replace(/[^\\d.\\-]/g, '')) || 0;
                    }}
                    if (asc) return va < vb ? -1 : va > vb ? 1 : 0;
                    return va > vb ? -1 : va < vb ? 1 : 0;
                }});

                if (arrow) arrow.textContent = asc ? '\\u25BC' : '\\u25B2';
                rows.forEach(r => tbody.appendChild(r));
            }});
        }});
    </script>
</body>
</html>
"""
