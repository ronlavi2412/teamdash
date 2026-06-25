# Agents

## Project Overview

Teamdash is a Python CLI tool that generates interactive HTML dashboards from GitHub and GitLab engineering metrics. It reads a `team.yaml` config, fetches data via `gh` and `glab` CLIs, and outputs a self-contained HTML file with Chart.js charts.

## Architecture

Single-package Python project (`teamdash/`) with no framework. Four CLI modes:

```
# Combined (default): fetch + generate
team.yaml -> config.py -> cli.py -> aggregate.py -> dashboard.py -> HTML file

# Fetch only: produce data.json
team.yaml -> config.py -> cli.py -> aggregate.py -> dashboard.py (build_dashboard_data) -> data.json

# Fetch Jira only: produce jira-data.json
team.yaml -> config.py -> cli.py -> fetch_jira_api.py -> jira-data.json

# Generate only: read data.json, skip API calls
data.json -> cli.py -> dashboard.py (generate_dashboard_from_data) -> HTML file

Supporting modules:
  fetch_github.py  -- gh api subprocess calls
  fetch_gitlab.py  -- glab api subprocess calls
  fetch_jira.py       -- reads pre-fetched Jira JSON file
  fetch_jira_api.py   -- fetches Jira data directly via REST API (requests library)
  scoring.py       -- story point estimation from PR metadata (ScoringConfig)
  models.py        -- Quarter, PRDetail, ScoredPR, EngineerQuarterMetrics, QuarterSummary
  quarters.py      -- date range calculation for N quarters
```

- **No web framework** -- generates static HTML, no server
- **No ORM or database** -- data is fetched live from APIs and cached as JSON in `~/.cache/teamdash/`
- **External CLIs** -- uses `gh` and `glab` subprocesses for API auth; Jira uses the `requests` library with Basic auth (email + API token)
- **Jira integration** -- `fetch_jira_api.py` fetches verified bugs, activity type story points, and cycle times directly from the Jira REST API; `fetch_jira.py` loads the resulting JSON file into the dashboard pipeline
- **React frontend** -- dashboard UI is a React/TypeScript app in `dashboard/` built with Vite and Chart.js, compiled into a JS/CSS bundle that `dashboard.py` embeds in the output HTML
- **`publish.sh`** -- deploys dashboard HTML to GitHub Pages via `gh-pages` branch

## Key Patterns

- API calls use subprocess to `gh api` / `glab api` rather than HTTP libraries, leveraging the user's existing CLI auth sessions
- **Rate limit handling**: GitHub search API has a 30 req/min limit. On 403 or "rate limit" errors, `fetch_github.py` sleeps 60s then retries once. Individual PR detail fetches sleep 0.5s between requests
- **Parallelization**: `aggregate.py` uses `ThreadPoolExecutor` with 4 workers for fetching across engineer/quarter combinations. Within each engineer fetch, a nested `ThreadPoolExecutor` with up to 5 workers parallelizes GitHub/GitLab API calls
- `dashboard.py` serializes data as JSON into `window.__DASHBOARD_DATA__` and embeds the React bundle from `dashboard/dist/`
- Caching is daily and keyed by config hash (MD5 of team name, orgs, engineers, and scoring config); `--no-cache` skips reading the cache but still writes it
- **Scoring**: story point estimation uses 4 signals (diff size, files changed, review friction, merge time) to classify PRs as XS/S/M/L/XL. PR labels can override the heuristic. Scoring is enabled by default; `--no-scoring` skips it for faster runs
- **Data models**: all structured data uses `dataclasses` in `models.py` (no Pydantic). Key classes: `PRDetail`, `ScoredPR`, `EngineerQuarterMetrics`, `QuarterSummary`

## Running

```bash
pip install .

# Combined (fetch + generate in one step)
teamdash team.yaml                     # 4 quarters, output dashboard.html
teamdash team.yaml -o report.html      # custom output path
teamdash team.yaml -q 6               # last 6 quarters
teamdash team.yaml --no-cache          # skip cache, fetch fresh data
teamdash team.yaml --include-current   # include current (in-progress) quarter
teamdash team.yaml --no-scoring        # skip story point estimation
teamdash team.yaml --refresh-gitlab    # re-fetch only GitLab data, keep cached GitHub data
teamdash team.yaml --jira-data jira-data.json  # include Jira data (verified bugs, activity types, cycle time)

# Fetch only (write data.json, no dashboard generation)
teamdash fetch team.yaml -o data.json
teamdash fetch team.yaml --jira-data jira-data.json -o data.json

# Fetch Jira only (write jira-data.json, requires JIRA_EMAIL and JIRA_API_TOKEN)
teamdash fetch-jira team.yaml -o jira-data.json

# Generate only (read data.json, no API calls)
teamdash generate data.json -o dashboard.html
```

## Testing

```bash
pip install -e ".[dev]"
python -m pytest tests/ -x -q
```

11 test files covering core modules: scoring, dashboard, aggregate, config, fetch_github, fetch_gitlab, fetch_jira, fetch_jira_api, models, quarters, and e2e. Tests use `unittest.mock` to patch subprocess calls and avoid real API hits.

## Generating Summaries

When regenerating the dashboard, always generate narrative summaries for each engineer for the most recent quarter. Summaries are generated by Claude Code (not an external API) and injected into `data.json` under the `"summaries"` key before regenerating the HTML.

Steps:
1. Read `data.json` to get all engineer metrics across quarters
2. For each engineer, write a concise narrative summary (2-3 paragraphs) for the last quarter covering:
   - PR/MR output and complexity trend vs prior quarters
   - Code review activity and review complexity
   - Merge time trends
   - Verified bugs (if applicable)
   - Activity type breakdown (if available)
   - Skip engineers with no activity across all quarters
3. Inject the summaries dict into `data.json`: `{"summaries": {"Engineer Name": "summary text", ...}}`
4. Regenerate `dashboard.html` from the updated `data.json`

Example workflow:
```bash
# 1. Fetch all data
teamdash fetch-jira config/team.yaml -q 4 --include-current -o jira-data.json
teamdash fetch config/team.yaml -q 4 --include-current --jira-data jira-data.json -o data.json

# 2. Claude Code generates summaries and injects into data.json

# 3. Generate dashboard
teamdash generate data.json -o dashboard.html
```

## Style

- Python 3.10+ with `from __future__ import annotations`
- Dataclasses for data models (no Pydantic)
- Errors and progress go to stderr, only the dashboard file is the output
- Warnings are `[WARN]`, errors are `[ERROR]` prefixed on stderr
