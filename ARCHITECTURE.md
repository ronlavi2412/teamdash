# Architecture

## System Overview

Teamdash is a Python CLI that fetches engineering metrics from GitHub, GitLab, and Jira, then generates a self-contained HTML dashboard. The output is a single HTML file with embedded React, Chart.js, and all data -- no server required.

## Components

```text
                   team.yaml
                      |
                  config.py        (parse + validate YAML)
                      |
                   cli.py          (route to subcommand)
                   /    \
          aggregate.py   dashboard.py
          /    |    \         |
  fetch_   fetch_  fetch_   Embed React bundle +
  github   gitlab  jira_   serialized JSON into
  .py      .py     api.py  single HTML file
         \   |   /
        scoring.py         (classify PRs -> XS/S/M/L/XL)
              |
          models.py        (Quarter, PRDetail, ScoredPR, EngineerQuarterMetrics)
```

## Data Flow

1. **Config** -- `config.py` loads `team.yaml` into `TeamConfig`, `EngineerConfig`, `ScoringConfig`, and optional `JiraConfig` dataclasses.
2. **Fetch** -- `aggregate.py` orchestrates data collection. For each engineer/quarter combination, it dispatches parallel fetch calls via `ThreadPoolExecutor`. GitHub and GitLab fetchers shell out to `gh api` / `glab api` subprocesses. The Jira fetcher uses the `requests` library with Basic auth.
3. **Score** -- `scoring.py` classifies each PR/MR using four signals (diff size, files changed, review friction, merge time). The maximum signal determines the t-shirt size. PR labels override the heuristic.
4. **Cache** -- Results are cached daily in `~/.cache/teamdash/` keyed by a config hash. Completed quarters are cached permanently; the current quarter refreshes daily. `--refresh-gitlab` selectively re-fetches GitLab data while preserving cached GitHub data.
5. **Generate** -- `dashboard.py` serializes `QuarterSummary` data as JSON into `window.__DASHBOARD_DATA__`, then embeds the pre-built React bundle (`dashboard/dist/`) to produce a self-contained HTML file.

## CLI Modes

| Command | Input | Output | API Calls |
|---------|-------|--------|-----------|
| `teamdash team.yaml` | YAML config | `dashboard.html` | Yes |
| `teamdash fetch team.yaml` | YAML config | `data.json` | Yes |
| `teamdash fetch-jira team.yaml` | YAML config | `jira-data.json` | Jira only |
| `teamdash generate data.json` | JSON data | `dashboard.html` | None |

## Dashboard Frontend

The dashboard is a React 19 app built with Vite in `dashboard/`. It uses Chart.js via `react-chartjs-2` for all visualizations. The build produces two files (`dashboard.js`, `dashboard.css`) that `dashboard.py` embeds inline.

The app reads data from `window.__DASHBOARD_DATA__` and renders five tabs:

| Tab | Component | Purpose |
|-----|-----------|---------|
| Team | `TeamView` | Aggregate bar charts (total PRs, reviews, merge time, story points, cycle time) |
| Detailed | `DetailView` | Per-engineer line charts with engineer filter |
| Table | `FullTable` | Sortable metrics table per engineer per quarter |
| Config | `ConfigView` | Display the team.yaml configuration used |
| Summaries | `SummariesView` | AI-generated narrative summaries per engineer |

## Deployment

`publish.sh` deploys HTML files to GitHub Pages via the `gh-pages` branch. It generates an `index.html` listing all published dashboards.

## Dependencies

See [AGENTS.md — Dependencies](AGENTS.md#dependencies) for the full Python and Node.js dependency table.

For repo structure details, see [AGENTS.md — Repository Structure](AGENTS.md#repository-structure).
