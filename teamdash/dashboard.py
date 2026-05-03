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
            headers.append(f'<th data-type="num">SP {s.quarter.short_label} <span class="sort-arrow"></span></th>')
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
                    <h3>Story Points Velocity per Quarter</h3>
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
                    <h3>Total Story Points per Quarter</h3>
                    <div class="chart-wrap"><canvas id="chart-team-sp"></canvas></div>
                </div>"""
        review_sp_chart = """
                <div class="chart-card">
                    <h3>Total Reviews Complexity per Quarter</h3>
                    <div class="chart-wrap"><canvas id="chart-team-review-sp"></canvas></div>
                </div>"""

    return f"""
        <div id="tab-team" class="tab-content active">
            <div class="chart-row">
                <div class="chart-card">
                    <h3>Total PRs + MRs per Quarter</h3>
                    <div class="chart-wrap"><canvas id="chart-team-prs"></canvas></div>
                </div>
                <div class="chart-card">
                    <h3>Total Reviews per Quarter</h3>
                    <div class="chart-wrap"><canvas id="chart-team-reviews"></canvas></div>
                </div>
            </div>
            <div class="chart-row">{sp_chart}{review_sp_chart}
                <div class="chart-card">
                    <h3>Avg Merge Time per Quarter (days)</h3>
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
                        <h4 style="margin-bottom: 8px; font-size: 0.9rem; color: var(--text-muted);">Story Points per Size</h4>
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

        .footer {{ text-align: center; padding: 24px; color: var(--text-muted); font-size: 0.8rem; }}

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
            <div class="chart-row">
                <div class="chart-card">
                    <h3>PRs + MRs per Quarter</h3>
                    <div class="chart-wrap"><canvas id="chart-prs-trend"></canvas></div>
                </div>
                <div class="chart-card">
                    <h3>Code Reviews per Quarter</h3>
                    <div class="chart-wrap"><canvas id="chart-reviews-trend"></canvas></div>
                </div>
            </div>
            <div class="chart-row">
                <div class="chart-card" id="overview-complexity" style="display:none;">
                    <h3>Total Complexity per Quarter (Story Points)</h3>
                    <div class="chart-wrap"><canvas id="chart-complexity-trend"></canvas></div>
                </div>
                <div class="chart-card" id="overview-review-complexity" style="display:none;">
                    <h3>Reviews Complexity per Quarter (Story Points)</h3>
                    <div class="chart-wrap"><canvas id="chart-review-complexity-trend"></canvas></div>
                </div>
            </div>
            <div class="chart-row">
                <div class="chart-card">
                    <h3>Avg Merge Time per Quarter (days)</h3>
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

        function switchTab(id) {{
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
            document.getElementById('tab-' + id).classList.add('active');
            event.target.classList.add('active');
        }}

        // PRs+MRs trend
        new Chart(document.getElementById('chart-prs-trend'), {{
            type: 'line',
            data: {{
                labels: Q.map(q => q.label),
                datasets: names.map((name, i) => ({{
                    label: name,
                    data: Q.map(q => q.gh_prs[i] + q.gl_mrs[i]),
                    borderColor: colors[i],
                    backgroundColor: colors[i] + '20',
                    tension: 0.3,
                    fill: false,
                    pointRadius: 4,
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
        new Chart(document.getElementById('chart-reviews-trend'), {{
            type: 'line',
            data: {{
                labels: Q.map(q => q.label),
                datasets: names.map((name, i) => ({{
                    label: name,
                    data: Q.map(q => q.reviews[i]),
                    borderColor: colors[i],
                    backgroundColor: colors[i] + '20',
                    tension: 0.3,
                    fill: false,
                    pointRadius: 4,
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
        new Chart(document.getElementById('chart-merge-time-trend'), {{
            type: 'line',
            data: {{
                labels: Q.map(q => q.label),
                datasets: names.map((name, i) => ({{
                    label: name,
                    data: Q.map(q => q.merge_time[i]),
                    borderColor: colors[i],
                    backgroundColor: colors[i] + '20',
                    tension: 0.3,
                    fill: false,
                    pointRadius: 4,
                    spanGaps: true,
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
            new Chart(document.getElementById('chart-complexity-trend'), {{
                type: 'line',
                data: {{
                    labels: Q.map(q => q.label),
                    datasets: names.map((name, i) => ({{
                        label: name,
                        data: Q.map(q => q.sp[i]),
                        borderColor: colors[i],
                        backgroundColor: colors[i] + '20',
                        tension: 0.3,
                        fill: false,
                        pointRadius: 4,
                    }})),
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{ legend: {{ position: 'bottom', labels: {{ usePointStyle: true }} }} }},
                    scales: {{ y: {{ beginAtZero: true, title: {{ display: true, text: 'Story Points' }} }} }},
                }},
            }});

            document.getElementById('overview-review-complexity').style.display = '';
            new Chart(document.getElementById('chart-review-complexity-trend'), {{
                type: 'line',
                data: {{
                    labels: Q.map(q => q.label),
                    datasets: names.map((name, i) => ({{
                        label: name,
                        data: Q.map(q => q.review_sp[i]),
                        borderColor: colors[i],
                        backgroundColor: colors[i] + '20',
                        tension: 0.3,
                        fill: false,
                        pointRadius: 4,
                    }})),
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{ legend: {{ position: 'bottom', labels: {{ usePointStyle: true }} }} }},
                    scales: {{ y: {{ beginAtZero: true, title: {{ display: true, text: 'Story Points' }} }} }},
                }},
            }});
        }}

        // Team view: Total PRs + MRs
        new Chart(document.getElementById('chart-team-prs'), {{
            type: 'bar',
            data: {{
                labels: Q.map(q => q.label),
                datasets: [{{
                    label: 'Total PRs + MRs',
                    data: Q.map(q => q.gh_prs.reduce((a, b) => a + b, 0) + q.gl_mrs.reduce((a, b) => a + b, 0)),
                    backgroundColor: '#3b82f6',
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
                labels: Q.map(q => q.label),
                datasets: [{{
                    label: 'Total Reviews',
                    data: Q.map(q => q.reviews.reduce((a, b) => a + b, 0)),
                    backgroundColor: '#8b5cf6',
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
                labels: Q.map(q => q.label),
                datasets: [{{
                    label: 'Avg Merge Time (days)',
                    data: Q.map(q => {{
                        const vals = q.merge_time.filter(v => v !== null);
                        return vals.length ? +(vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1) : null;
                    }}),
                    borderColor: '#ef4444',
                    backgroundColor: '#ef444420',
                    tension: 0.3,
                    fill: true,
                    pointRadius: 5,
                    pointBackgroundColor: '#ef4444',
                    spanGaps: true,
                }}],
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{ y: {{ beginAtZero: true, max: 20, title: {{ display: true, text: 'Days' }} }} }},
            }},
        }});

        // Team view: Total Story Points
        if ({has_scoring}) {{
            new Chart(document.getElementById('chart-team-sp'), {{
                type: 'bar',
                data: {{
                    labels: Q.map(q => q.label),
                    datasets: [{{
                        label: 'Total Story Points',
                        data: Q.map(q => q.sp.reduce((a, b) => a + b, 0)),
                        backgroundColor: '#10b981',
                        borderColor: '#059669',
                        borderWidth: 1,
                        borderRadius: 4,
                    }}],
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{ legend: {{ display: false }} }},
                    scales: {{ y: {{ beginAtZero: true, title: {{ display: true, text: 'Story Points' }} }} }},
                }},
            }});

            new Chart(document.getElementById('chart-team-review-sp'), {{
                type: 'bar',
                data: {{
                    labels: Q.map(q => q.label),
                    datasets: [{{
                        label: 'Total Reviews Complexity',
                        data: Q.map(q => q.review_sp.reduce((a, b) => a + b, 0)),
                        backgroundColor: '#f59e0b',
                        borderColor: '#d97706',
                        borderWidth: 1,
                        borderRadius: 4,
                    }}],
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{ legend: {{ display: false }} }},
                    scales: {{ y: {{ beginAtZero: true, title: {{ display: true, text: 'Story Points' }} }} }},
                }},
            }});
        }}

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
