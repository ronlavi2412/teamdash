# Teamdash

CLI tool that generates an interactive HTML dashboard showing team engineering metrics from GitHub and GitLab.

Takes a YAML config file with team members' GitHub/GitLab usernames, fetches PR/MR and code review data via the `gh` and `glab` CLIs, and produces a self-contained HTML dashboard with Chart.js visualizations.

## Prerequisites

- Python 3.10+
- [GitHub CLI](https://cli.github.com/) (`gh`) authenticated via `gh auth login`
- [GitLab CLI](https://gitlab.com/gitlab-org/cli) (`glab`) authenticated via `glab auth login --hostname <your-gitlab>`

## Quick Start

```bash
# Install
pip install .

# Create a team.yaml config (see Configuration section below)

# Generate the dashboard
teamdash team.yaml
```

Open `dashboard.html` in a browser.

## Usage

```bash
# Combined (fetch + generate in one step)
teamdash team.yaml                     # 4 quarters, output dashboard.html
teamdash team.yaml -o report.html      # custom output path
teamdash team.yaml -q 6               # last 6 quarters
teamdash team.yaml --no-cache          # skip cache, fetch fresh data
teamdash team.yaml --include-current   # include the current (in-progress) quarter
teamdash team.yaml --no-scoring        # skip story point estimation (faster)
teamdash team.yaml --refresh-gitlab    # re-fetch only GitLab data, keep cached GitHub data
teamdash team.yaml --jira-data jira-data.json  # include Jira data (verified bugs + activity types)

# Fetch only (write data.json, no dashboard generation)
teamdash fetch team.yaml -o data.json
teamdash fetch team.yaml --jira-data jira-data.json -o data.json

# Fetch Jira only (requires JIRA_EMAIL and JIRA_API_TOKEN env vars)
teamdash fetch-jira team.yaml -o jira-data.json

# Generate only (read data.json, no API calls)
teamdash generate data.json -o dashboard.html
```

## Configuration

Create a `team.yaml` file:

```yaml
team_name: "My Team"

gitlab:
  url: "https://gitlab.example.com"

github:
  orgs:
    - my-org
    - another-org

engineers:
  - name: "Jane Doe"
    github: janedoe
    gitlab: jdoe

  - name: "John Smith"
    github: jsmith
    gitlab: johnsmith
```

| Field | Required | Description |
|-------|----------|-------------|
| `team_name` | Yes | Displayed in the dashboard header |
| `gitlab.url` | No | Self-hosted GitLab instance URL. Omit to skip GitLab fetching |
| `github.orgs` | No | GitHub organizations to search for PRs. Omit to skip GitHub fetching |
| `engineers[].name` | Yes | Display name |
| `engineers[].github` | No | GitHub username |
| `engineers[].gitlab` | No | GitLab username |
| `engineers[].jira_account_id` | No | Atlassian Jira account ID (for verified bugs tracking) |
| `jira.cloud_id` | No | Atlassian cloud instance (e.g., `redhat.atlassian.net`) |
| `jira.project_keys` | No | Jira project keys to query (e.g., `["CNV", "MTV"]`) |

Each engineer needs at least one of `github` or `gitlab`.

### Jira Configuration

To track verified bugs from Jira, add a `jira` section and per-engineer `jira_account_id` fields:

```yaml
jira:
  cloud_id: "redhat.atlassian.net"
  project_keys: ["CNV", "MTV", "OCPBUGS"]

engineers:
  - name: "Jane Doe"
    github: janedoe
    gitlab: jdoe
    jira_account_id: "712020:xxxx-xxxx-xxxx"
```

Fetch Jira data and pass the resulting JSON file to teamdash:

```bash
# Fetch Jira data (requires JIRA_EMAIL and JIRA_API_TOKEN env vars)
teamdash fetch-jira team.yaml -o jira-data.json

# Generate dashboard with Jira data
teamdash team.yaml --jira-data jira-data.json
```

The JSON file maps quarters to per-engineer verified bug story point sums, with an optional `activity_types` section for story point sums by activity type:

```json
{
  "2025-Q1": {"Engineer Name": 5, ...},
  "activity_types": {
    "2025-Q1": {
      "Engineer Name": {"Incidents & Support": 3, "Product / Portfolio Work": 2}
    }
  }
}
```

### Scoring Configuration

Story point estimation is enabled by default. Customize the scoring behavior by adding a `scoring` section to your config:

```yaml
scoring:
  size_points:
    XS: 2
    S: 5
    M: 8
    L: 13
    XL: 21
  diff_thresholds: [50, 200, 500, 1200]          # lines changed -> XS/S/M/L/XL
  file_thresholds: [3, 8, 15, 30]                 # files changed -> XS/S/M/L/XL
  merge_time_thresholds: [0.5, 2.0, 5.0, 10.0]   # days to merge -> XS/S/M/L/XL
  size_label_patterns:                            # PR labels that override heuristic sizing
    XS: ["size/xs", "t-shirt/xs"]
    S: ["size/s", "t-shirt/s"]
    M: ["size/m", "t-shirt/m"]
    L: ["size/l", "t-shirt/l"]
    XL: ["size/xl", "t-shirt/xl"]
```

All scoring fields are optional; omitted fields use the defaults shown above. Use `--no-scoring` to skip story point estimation entirely.

## Dashboard

The generated HTML file includes:

- **Summary cards** -- Total PRs+MRs, GitHub PRs, GitLab MRs, Code Reviews (with % change vs previous quarter)
- **Overall Team View tab** -- Aggregate bar charts: total PRs+MRs, total reviews, avg merge time per quarter. When scoring is enabled, also shows total story points and review complexity per quarter
- **Detailed View tab** -- Per-engineer line charts: PRs+MRs trend, code reviews trend, avg merge time. When scoring is enabled, also shows per-engineer complexity and review complexity trends
- **Full Table tab** -- Sortable table with all metrics per engineer per quarter (includes story point columns when scoring is enabled, and verified bugs columns when Jira data is provided)

## Story Points

By default, teamdash estimates story points for each PR/MR using a multi-signal heuristic:

1. **Diff size** -- total lines added + deleted
2. **Files changed** -- number of files modified
3. **Review friction** -- changes-requested count and high comment volume
4. **Merge time** -- days from creation to merge

Each signal maps to a t-shirt size (XS/S/M/L/XL) via configurable thresholds. The final size is the maximum across all signals. If a PR carries a recognized size label (e.g., `size/m`), the label overrides the heuristic.

Points are assigned per size: XS=2, S=5, M=8, L=13, XL=21 (Fibonacci-like, configurable).

Review complexity scores the PRs reviewed by each engineer using the same sizing logic. XL PRs are flagged with "should-split" as a suggestion to break them into smaller changesets.

Use `--no-scoring` to skip estimation for faster runs with fewer API calls.

## Deployment

Publish dashboards to GitHub Pages:

```bash
./publish.sh dashboard.html                                    # single dashboard
./publish.sh dashboard-team1.html dashboard-team2.html         # multiple dashboards
```

This commits the HTML files to the `gh-pages` branch, generates an `index.html` listing all dashboards, and pushes to the remote.

## Caching

Fetched data is cached daily in `~/.cache/teamdash/`. Subsequent runs on the same day reuse cached data. Use `--no-cache` to force a fresh fetch.

## Testing

```bash
pip install -e ".[dev]"
pytest
```

## Project Structure

```
teamdash/
  teamdash/
    __init__.py         # Package version
    __main__.py         # python -m teamdash entry point
    cli.py              # CLI entry point (argparse)
    config.py           # YAML config loading and validation
    quarters.py         # Quarter date range calculation
    models.py           # Data classes (PRDetail, ScoredPR, EngineerQuarterMetrics, etc.)
    scoring.py          # Story point estimation engine
    fetch_github.py     # GitHub data fetching via gh CLI
    fetch_gitlab.py     # GitLab data fetching via glab CLI
    fetch_jira.py       # Jira data loader (verified bugs + activity types from pre-fetched JSON)
    fetch_jira_api.py   # Jira REST API client (direct fetch with pagination)
    aggregate.py        # Orchestration, caching, and parallelization
    dashboard.py        # HTML dashboard generation (embeds React bundle)
  dashboard/
    src/                # React/TypeScript frontend (Chart.js charts)
    e2e/                # Playwright end-to-end tests
    vite.config.ts      # Vite build config
  tests/
    conftest.py
    test_aggregate.py
    test_config.py
    test_dashboard.py
    test_e2e.py
    test_fetch_github.py
    test_fetch_gitlab.py
    test_fetch_jira.py
    test_models.py
    test_quarters.py
    test_scoring.py
  config/               # Team YAML configs (git-ignored)
  publish.sh            # GitHub Pages deployment script
  pyproject.toml        # Package configuration
  requirements.txt
```
