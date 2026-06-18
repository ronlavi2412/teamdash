# Agents

## Project Overview

Teamdash is a Python CLI tool that generates interactive HTML dashboards from GitHub and GitLab engineering metrics. It reads a `team.yaml` config, fetches data via `gh` and `glab` CLIs, and outputs a self-contained HTML file with Chart.js charts.

## Architecture

Single-package Python project (`teamdash/`) with no framework. Three CLI modes:

```
# Combined (default): fetch + generate
team.yaml -> config.py -> cli.py -> aggregate.py -> dashboard.py -> HTML file

# Fetch only: produce data.json
team.yaml -> config.py -> cli.py -> aggregate.py -> dashboard.py (build_dashboard_data) -> data.json

# Generate only: read data.json, skip API calls
data.json -> cli.py -> dashboard.py (generate_dashboard_from_data) -> HTML file

Supporting modules:
  fetch_github.py  -- gh api subprocess calls
  fetch_gitlab.py  -- glab api subprocess calls
  fetch_jira.py    -- reads pre-fetched JSON from Atlassian MCP
  scoring.py       -- story point estimation from PR metadata (ScoringConfig)
  models.py        -- Quarter, PRDetail, ScoredPR, EngineerQuarterMetrics, QuarterSummary
  quarters.py      -- date range calculation for N quarters
```

- **No web framework** -- generates static HTML, no server
- **No ORM or database** -- data is fetched live from APIs and cached as JSON in `~/.cache/teamdash/`
- **External CLIs** -- uses `gh` and `glab` subprocesses for API auth, not raw HTTP requests
- **Jira integration** -- verified bug story point sums and activity type story point sums are loaded from a pre-fetched JSON file (produced by the Atlassian MCP via the `fetch-jira-data` Claude Code agent); configured via `.mcp.json`
- **React frontend** -- dashboard UI is a React/TypeScript app in `dashboard/` built with Vite and Chart.js, compiled into a JS/CSS bundle that `dashboard.py` embeds in the output HTML
- **`publish.sh`** -- deploys dashboard HTML to GitHub Pages via `gh-pages` branch

## Key Patterns

- API calls use subprocess to `gh api` / `glab api` rather than HTTP libraries, leveraging the user's existing CLI auth sessions
- **Rate limit handling**: GitHub search API has a 30 req/min limit. On 403 or "rate limit" errors, `fetch_github.py` sleeps 60s then retries once. Individual PR detail fetches sleep 0.5s between requests
- **Parallelization**: `aggregate.py` uses `ThreadPoolExecutor` with 2 workers for fetching across engineer/quarter combinations. Within each engineer fetch, a nested `ThreadPoolExecutor` with up to 5 workers parallelizes GitHub/GitLab API calls
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
teamdash team.yaml --jira-data jira-data.json  # include Jira data (verified bugs + activity types)

# Fetch only (write data.json, no dashboard generation)
teamdash fetch team.yaml -o data.json
teamdash fetch team.yaml --jira-data jira-data.json -o data.json

# Generate only (read data.json, no API calls)
teamdash generate data.json -o dashboard.html
```

## Testing

```bash
pip install -e ".[dev]"
python -m pytest tests/ -x -q
```

10 test files covering all modules: scoring, dashboard, aggregate, config, fetch_github, fetch_gitlab, fetch_jira, models, quarters, and e2e. Tests use `unittest.mock` to patch subprocess calls and avoid real API hits.

## Style

- Python 3.10+ with `from __future__ import annotations`
- Dataclasses for data models (no Pydantic)
- Errors and progress go to stderr, only the dashboard file is the output
- Warnings are `[WARN]`, errors are `[ERROR]` prefixed on stderr
