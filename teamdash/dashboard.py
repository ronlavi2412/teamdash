from __future__ import annotations

from datetime import datetime

from teamdash.models import QuarterSummary


COLORS = [
    "#f59e0b", "#3b82f6", "#8b5cf6", "#ec4899",
    "#06b6d4", "#10b981", "#ef4444", "#14b8a6",
    "#6366f1", "#d946ef", "#0ea5e9", "#84cc16",
]


def _pct(new: int, old: int) -> str:
    if old == 0:
        return "+999%" if new > 0 else "0%"
    delta = round((new - old) / old * 100)
    return f"+{delta}%" if delta >= 0 else f"{delta}%"


def _delta_class(new: int, old: int) -> str:
    if old == 0:
        return "up" if new > 0 else "flat"
    delta = (new - old) / old
    if delta > 0.01:
        return "up"
    if delta < -0.01:
        return "down"
    return "flat"


def _build_data_block(summaries: list[QuarterSummary], names: list[str]) -> str:
    def fmt(arr: list[int]) -> str:
        return "[" + ", ".join(str(v) for v in arr) + "]"

    q_entries = []
    for s in summaries:
        by_name = {e.name: e for e in s.engineers}
        gh = [by_name.get(n, _zero(n, s.quarter.label)).github_prs for n in names]
        gl = [by_name.get(n, _zero(n, s.quarter.label)).gitlab_mrs for n in names]
        rv = [by_name.get(n, _zero(n, s.quarter.label)).reviews for n in names]
        q_entries.append(
            f'    {{ label: "{s.quarter.short_label}",'
            f' gh_prs: {fmt(gh)}, gl_mrs: {fmt(gl)}, reviews: {fmt(rv)} }}'
        )

    return "const Q = [\n" + ",\n".join(q_entries) + "\n];"


def _zero(name, quarter):
    from teamdash.models import EngineerQuarterMetrics
    return EngineerQuarterMetrics(name=name, quarter=quarter)


def _build_summary_cards(summaries: list[QuarterSummary]) -> str:
    cur = summaries[-1]
    prev = summaries[-2] if len(summaries) >= 2 else cur

    cards = [
        ("Total PRs + MRs", cur.total_prs_mrs, prev.total_prs_mrs),
        ("GitHub PRs", cur.total_github_prs, prev.total_github_prs),
        ("GitLab MRs", cur.total_gitlab_mrs, prev.total_gitlab_mrs),
        ("Code Reviews", cur.total_reviews, prev.total_reviews),
    ]

    prev_label = prev.quarter.label
    parts = []
    for label, cur_val, prev_val in cards:
        cls = _delta_class(cur_val, prev_val)
        pct = _pct(cur_val, prev_val)
        parts.append(f"""            <div class="summary-card">
                <div class="label">{label}</div>
                <div class="value">{cur_val}</div>
                <div class="delta {cls}">{pct} from {prev_label} ({prev_val})</div>
            </div>""")

    return '<div class="summary-grid">\n' + "\n".join(parts) + "\n        </div>"


def _build_table_rows(summaries: list[QuarterSummary], names: list[str]) -> str:
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

        rows.append("<tr>" + "".join(cells) + "</tr>")

    return "\n                            ".join(rows)


def _build_table_headers(summaries: list[QuarterSummary]) -> str:
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
    return "\n                                ".join(headers)


def generate_dashboard(
    team_name: str,
    summaries: list[QuarterSummary],
    output_path: str,
) -> None:
    names = [e.name for e in summaries[0].engineers]
    colors_js = "[" + ", ".join(f'"{COLORS[i % len(COLORS)]}"' for i in range(len(names))) + "]"
    names_js = "[" + ", ".join(f'"{n}"' for n in names) + "]"

    first_q = summaries[0].quarter
    last_q = summaries[-1].quarter
    title = f"{team_name} &mdash; {first_q.label} to {last_q.label}"
    subtitle = f"{len(summaries)} quarters ({first_q.start} to {last_q.end})"
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")

    data_block = _build_data_block(summaries, names)
    summary_cards = _build_summary_cards(summaries)
    table_headers = _build_table_headers(summaries)
    table_rows = _build_table_rows(summaries, names)

    html = HTML_TEMPLATE.format(
        title=title,
        subtitle=subtitle,
        generated=generated,
        data_block=data_block,
        summary_cards=summary_cards,
        names_js=names_js,
        colors_js=colors_js,
        table_headers=table_headers,
        table_rows=table_rows,
        num_engineers=len(names),
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
            <div class="tab active" onclick="switchTab('overview')">Overview</div>
            <div class="tab" onclick="switchTab('details')">Details</div>
            <div class="tab" onclick="switchTab('table')">Full Table</div>
        </div>

        <div id="tab-overview" class="tab-content active">
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
        </div>

        <div id="tab-details" class="tab-content">
            <div class="chart-row">
                <div class="chart-card">
                    <h3>GitHub PRs vs GitLab MRs (Latest Quarter)</h3>
                    <div class="chart-wrap"><canvas id="chart-breakdown"></canvas></div>
                </div>
                <div class="chart-card">
                    <h3>Review Share (Latest Quarter)</h3>
                    <div class="chart-wrap"><canvas id="chart-review-share"></canvas></div>
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

        // GitHub vs GitLab breakdown (latest quarter)
        new Chart(document.getElementById('chart-breakdown'), {{
            type: 'bar',
            data: {{
                labels: names,
                datasets: [
                    {{
                        label: 'GitHub PRs',
                        data: cur.gh_prs,
                        backgroundColor: '#3b82f6',
                    }},
                    {{
                        label: 'GitLab MRs',
                        data: cur.gl_mrs,
                        backgroundColor: '#f59e0b',
                    }},
                ],
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ position: 'bottom' }} }},
                scales: {{ y: {{ beginAtZero: true }} }},
            }},
        }});

        // Review share pie
        new Chart(document.getElementById('chart-review-share'), {{
            type: 'doughnut',
            data: {{
                labels: names,
                datasets: [{{
                    data: cur.reviews,
                    backgroundColor: colors,
                }}],
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ position: 'bottom', labels: {{ usePointStyle: true }} }} }},
            }},
        }});

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
