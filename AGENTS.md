# Agents

## Repository Structure

```text
teamdash/
  teamdash/              # Python package
    cli.py               # CLI entry point (argparse, 3 subcommands + default combined mode)
    config.py            # JSON config loading and validation (TeamConfig, EngineerConfig, JiraConfig)
    quarters.py          # Quarter date range calculation
    models.py            # Dataclasses: Quarter, PRDetail, ScoredPR, EngineerQuarterMetrics, QuarterSummary
    scoring.py           # Story point estimation engine (ScoringConfig, 4-signal heuristic)
    aggregate.py         # Orchestration: caching, parallelization, data collection
    fetch_github.py      # GitHub data fetching via `gh api` subprocess
    fetch_gitlab.py      # GitLab data fetching via `glab api` subprocess
    fetch_jira.py        # Loads pre-fetched Jira JSON (JiraData dataclass)
    fetch_jira_api.py    # Jira REST API client (requests library, Basic auth)
    dashboard.py         # HTML generation (embeds React bundle from dashboard/dist/)
  dashboard/             # React/TypeScript frontend
    src/
      App.tsx            # Root component: tab navigation, data prop drilling
      types.ts           # TypeScript interfaces for all dashboard data
      components/        # UI components (Header, TabBar, TeamView, DetailView, FullTable, etc.)
      hooks/             # Custom hooks (useEngineerFilter, useTableSort)
    e2e/                 # Playwright end-to-end tests
      specs/             # Test specs (charts, filter, scoring, table, tabs, jira, cycle-time, responsive)
      fixtures/          # Generated HTML test fixtures
    vite.config.ts       # Vite build config (single-file output: dashboard.js, dashboard.css)
  tests/                 # Python unit tests (pytest, unittest.mock)
  config.example.json    # Example config (tracked)
  config.json            # Your team config (git-ignored)
  publish.sh             # GitHub Pages deployment script
```

## Key Patterns

- **Subprocess-based API calls**: `fetch_github.py` and `fetch_gitlab.py` call `gh api` and `glab api` as subprocesses, relying on the user's CLI auth sessions rather than HTTP libraries.
- **Rate limit handling**: GitHub search API is throttled to 28 req/min. On 403 or rate limit errors, `fetch_github.py` retries up to 3 times with delays of 30s, 60s, and 120s. PR details are fetched via GraphQL pagination.
- **Parallelization**: `aggregate.py` uses `ThreadPoolExecutor` with 8 workers across engineer/quarter combinations. Within each engineer fetch, a nested `ThreadPoolExecutor` (up to 5 workers) parallelizes GitHub/GitLab/Jira API calls.
- **Caching**: Daily cache keyed by config hash (MD5 of team name, orgs, engineers, scoring config) in `~/.cache/teamdash/`. `--no-cache` skips reading but still writes. `--refresh-gitlab` re-fetches only GitLab data while keeping cached GitHub data.
- **Scoring engine**: 4 signals (diff size, files changed, review friction, merge time) classify PRs as XS/S/M/L/XL. PR labels can override the heuristic. Points are Fibonacci-like: XS=2, S=5, M=8, L=13, XL=21.
- **Dashboard embedding**: `dashboard.py` serializes data as JSON into `window.__DASHBOARD_DATA__` and embeds the compiled React bundle (`dashboard/dist/dashboard.js` + `dashboard/dist/dashboard.css`) to produce a self-contained HTML file.
- **Jira integration**: `fetch_jira_api.py` queries Jira REST API with pagination for verified bugs, activity type story points, and cycle times. Credentials are from `JIRA_EMAIL` and `JIRA_API_TOKEN` environment variables.

## Dependencies

### Python

| Package | Purpose |
|---------|---------|
| (stdlib `json`) | JSON config parsing |
| `requests` | Jira REST API calls |
| `pytest` | Test framework (dev) |

External CLIs: `gh` (GitHub CLI), `glab` (GitLab CLI).

### Dashboard (Node.js)

| Package | Purpose |
|---------|---------|
| `react`, `react-dom` | UI framework |
| `chart.js`, `react-chartjs-2` | Charts |
| `vite`, `@vitejs/plugin-react` | Build tool |
| `typescript`, `typescript-eslint` | Type checking and linting |
| `@playwright/test` | E2E testing |

## AI Agent Guidelines

### Generating Summaries

The `/generate` command (`.claude/commands/generate.md`) automates this entire process. The steps below are for reference when modifying the summary generation logic.

When regenerating the dashboard, generate comprehensive narrative summaries for each engineer for the most recent quarter only. Summaries are injected into `data.json` under the `"summaries"` key (nested by quarter) before regenerating the HTML. The `data.json` file includes a `pr_details` field with per-engineer per-quarter PR lists (title, repo, size, source) to enable content-aware summaries.

1. Extract the latest two quarters' metrics and latest quarter's PR details from `data.json` into a subset file (see generate.md Step 4 for the extraction script). Read the subset file, not the full `data.json`, to minimize LLM token usage.
2. For the most recent quarter only, and for each engineer, write a comprehensive narrative (up to 3 paragraphs):
   - **What they worked on:** Group PRs by repo, identify themes from titles (bugs, features, refactoring, i18n, etc.), highlight notable PRs.
   - **Output and complexity:** Total PRs/MRs, complexity points, size distribution, merge time, quarter-over-quarter trends.
   - **Reviews and Jira activity:** Code review volume, activity type breakdown.
   - Skip engineers with no activity in that quarter.
3. Inject the summaries dict into `data.json`: `{"summaries": {"Q2'26": {"Engineer Name": "summary text", ...}}}` (latest quarter only)
4. Regenerate: `teamdash generate data.json -o dashboard.html`

### Review Guidelines

When reviewing changes to this project:

- Verify `from __future__ import annotations` is at the top of new Python modules.
- Check that subprocess calls to `gh api` / `glab api` handle errors (non-zero exit codes, rate limits).
- Confirm new data fields are added to both `models.py` dataclasses and `dashboard/src/types.ts` interfaces.
- Verify cache entries handle the new field (both reading from cache and writing to cache in `aggregate.py`).
- Ensure `tests/conftest.py` fixtures are updated when model fields change.
- For dashboard changes, confirm the Vite build produces the expected single-file output (`dashboard.js`, `dashboard.css`).

## Running

See [README.md](README.md#cli-reference) for CLI commands and [CONTRIBUTING.md](CONTRIBUTING.md) for development setup.

## Style

- Python 3.10+ with `from __future__ import annotations`
- Dataclasses for data models (no Pydantic)
- Errors and progress go to stderr; only the dashboard file is the output
- Warnings are `[WARN]`, errors are `[ERROR]` prefixed on stderr
