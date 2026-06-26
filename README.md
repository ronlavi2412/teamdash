# Teamdash

## Overview

Teamdash is a Python CLI that fetches engineering metrics from GitHub, GitLab, and Jira and generates a self-contained interactive HTML dashboard. The output is a single HTML file with embedded React, Chart.js, and all data — no server required. It tracks PRs, merge requests, code reviews, story points, verified bugs, cycle times, and more across quarterly time windows, with per-engineer breakdowns and AI-generated narrative summaries.

## Prerequisites

1. **Python 3.10+** and **Node.js 18+** (for building the dashboard frontend)

2. **GitHub CLI** — install from [cli.github.com](https://cli.github.com/), then authenticate:
   ```bash
   gh auth login
   ```

3. **GitLab CLI** (optional, only if your team uses GitLab) — install from [gitlab.com/gitlab-org/cli](https://gitlab.com/gitlab-org/cli), then authenticate:
   ```bash
   glab auth login --hostname gitlab.example.com
   ```

4. **Jira API credentials** (optional, for bug tracking and cycle time metrics):
   - `JIRA_EMAIL` — your Atlassian account email
   - `JIRA_API_TOKEN` — create one at [id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)

   Set them in your shell profile or before running:
   ```bash
   export JIRA_EMAIL="you@company.com"
   export JIRA_API_TOKEN="your-token-here"
   ```

5. **Install teamdash**:
   ```bash
   pip install .
   cd dashboard && npm install && npm run build && cd ..
   ```

## Setting Up Your Team Config

Copy the example and fill in your team's details (`config.json` is git-ignored so your config stays local):

```bash
cp config.example.json config.json
```

```json
{
  "team_name": "My Team",
  "github": {
    "orgs": ["my-github-org"]
  },
  "gitlab": {
    "url": "https://gitlab.example.com"
  },
  "jira": {
    "cloud_id": "mycompany.atlassian.net",
    "project_keys": ["PROJ", "OPS"]
  },
  "engineers": [
    {
      "name": "Jane Doe",
      "github": "janedoe",
      "gitlab": "jdoe",
      "jira_account_id": "712020:xxxx-xxxx-xxxx"
    },
    {
      "name": "John Smith",
      "github": "jsmith"
    }
  ]
}
```

### How to find the values

| Field | How to find it |
|-------|----------------|
| **GitHub username** | The username in their GitHub profile URL: `github.com/<username>` |
| **GitLab username** | The username in their GitLab profile URL: `gitlab.example.com/<username>` |
| **GitHub orgs** | The organizations your team contributes to — visible at `github.com/orgs/<org>` |
| **Jira cloud ID** | Your Atlassian site hostname, e.g. `mycompany.atlassian.net` |
| **Jira project keys** | The prefix in issue IDs (e.g. `PROJ` from `PROJ-123`), visible in Jira board URLs |
| **Jira account ID** | See below |

**Finding Jira account IDs**: Open this URL in your browser (replace `<site>` with your Atlassian hostname and `<name>` with the person's name):

```
https://<site>.atlassian.net/rest/api/3/user/search?query=<name>
```

Look for the `accountId` field in the JSON response. It looks like `"712020:xxxx-xxxx-xxxx"` or `"5e9ff58b1f32260c13f717ca"`.

## Generating Your Dashboard

### Quick start (no Jira)

Fetch GitHub and GitLab data for all configured engineers, estimate story points, and produce a self-contained `dashboard.html` file. The `--include-current` flag includes the in-progress quarter.

```bash
teamdash config.json --include-current
open dashboard.html
```

### Full workflow (with Jira and summaries)

```bash
# Step 1: Fetch Jira data (verified bugs, activity types, cycle times)
teamdash fetch-jira config.json -q 4 --include-current -o jira-data.json

# Step 2: Fetch GitHub/GitLab data and combine with Jira data
teamdash fetch config.json -q 4 --include-current --jira-data jira-data.json -o data.json

# Step 3: Generate the dashboard
teamdash generate data.json -o dashboard.html
```

Open `dashboard.html` in a browser.

### Using Claude Code

This repo includes [Claude Code](https://docs.anthropic.com/en/docs/claude-code) slash commands to automate setup and dashboard generation. From the project directory, run `claude` and use:

| Command | What it does |
|---------|-------------|
| `/setup` | Interactive setup wizard — checks prerequisites, verifies auth, installs dependencies, helps create `config.json` |
| `/generate` | Full pipeline — fetches Jira/GitHub/GitLab data, generates per-engineer narrative summaries, produces `dashboard.html` |

**First time setup:**
```
claude
> /setup
```

**Generate your dashboard:**
```
claude
> /generate
```

### Using Cursor

This repo includes [Cursor](https://cursor.com/) rules (in `.cursor/rules/`) for the same workflows. In Cursor's chat, mention the rule to activate it:

| Rule | What it does |
|------|-------------|
| `@setup` | Interactive setup wizard — checks prerequisites, verifies auth, installs dependencies, helps create `config.json` |
| `@generate` | Full pipeline — fetches Jira/GitHub/GitLab data, generates per-engineer narrative summaries, produces `dashboard.html` |

## CLI Reference

```bash
# Combined (fetch + generate in one step)
teamdash team.json                     # 4 quarters, output dashboard.html
teamdash team.json -o report.html      # custom output path
teamdash team.json -q 6               # last 6 quarters
teamdash team.json --no-cache          # skip cache, fetch fresh data
teamdash team.json --include-current   # include the current (in-progress) quarter
teamdash team.json --no-scoring        # skip story point estimation (faster)
teamdash team.json --refresh-gitlab    # re-fetch only GitLab data, keep cached GitHub data
teamdash team.json --jira-data jira-data.json  # include Jira data

# Fetch only (write data.json, no dashboard generation)
teamdash fetch team.json -o data.json
teamdash fetch team.json --jira-data jira-data.json -o data.json

# Fetch Jira only (requires JIRA_EMAIL and JIRA_API_TOKEN)
teamdash fetch-jira team.json -o jira-data.json

# Generate only (read data.json, no API calls)
teamdash generate data.json -o dashboard.html
```

## Dashboard

The generated HTML file includes:

- **Summary cards** — Total PRs+MRs, GitHub PRs, GitLab MRs, Code Reviews (with % change vs previous quarter)
- **Overall Team View** — Aggregate bar charts: total PRs+MRs, total reviews, avg merge time per quarter, story points, review complexity, cycle time trends
- **Detailed View** — Per-engineer line charts: PRs+MRs trend, code reviews, complexity, merge time, verified bugs, cycle time by project
- **Summaries** — AI-generated narrative summaries per engineer for the most recent quarter
- **Full Table** — Sortable table with all metrics per engineer per quarter
- **Configuration** — Shows the scoring config and thresholds used

## Scoring

Story point estimation is enabled by default. Each PR/MR is sized XS–XL using four signals: diff size, files changed, review friction, and merge time. The final size is the maximum across all signals. PR labels (e.g. `size/m`) override the heuristic.

Points per size: XS=2, S=5, M=8, L=13, XL=21 (configurable).

Customize by adding a `scoring` section to your config:

```json
{
  "scoring": {
    "size_points": {"XS": 2, "S": 5, "M": 8, "L": 13, "XL": 21},
    "diff_thresholds": [50, 200, 500, 1200],
    "file_thresholds": [3, 8, 15, 30],
    "merge_time_thresholds": [0.5, 2.0, 5.0, 10.0],
    "size_label_patterns": {
      "XS": ["size/xs", "t-shirt/xs"],
      "S": ["size/s", "t-shirt/s"],
      "M": ["size/m", "t-shirt/m"],
      "L": ["size/l", "t-shirt/l"],
      "XL": ["size/xl", "t-shirt/xl"]
    }
  }
}
```

Use `--no-scoring` to skip estimation for faster runs.

## Deployment

Publish dashboards to GitHub Pages:

```bash
./publish.sh dashboard.html                            # single dashboard
./publish.sh dashboard-team1.html dashboard-team2.html # multiple dashboards
```

This commits the HTML files to the `gh-pages` branch, generates an index page, and pushes.

## Caching

Fetched data is cached daily in `~/.cache/teamdash/`, keyed by your config. Subsequent runs on the same day reuse cached data. Past quarters are cached permanently (their data doesn't change). Use `--no-cache` to force a fresh fetch.

## Testing

```bash
pip install -e ".[dev]"
pytest
```

## Project Structure

```
teamdash/
  teamdash/             # Python package
    __init__.py         # Package version
    __main__.py         # python -m teamdash entry point
    cli.py              # CLI entry point
    config.py           # JSON config loading
    quarters.py         # Quarter date range calculation
    models.py           # Data classes
    scoring.py          # Story point estimation
    fetch_github.py     # GitHub data fetching via gh CLI
    fetch_gitlab.py     # GitLab data fetching via glab CLI
    fetch_jira.py       # Jira data loader (from pre-fetched JSON)
    fetch_jira_api.py   # Jira REST API client
    aggregate.py        # Orchestration, caching, parallelization
    dashboard.py        # HTML dashboard generation
  dashboard/            # React/TypeScript frontend (Chart.js)
  tests/                # Python unit tests
  config.example.json   # Example config (tracked)
  config.json           # Your team config (git-ignored)
  pyproject.toml        # Package configuration
  requirements.txt      # Python dependencies
  publish.sh            # GitHub Pages deployment
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding standards, testing, and the PR process.
