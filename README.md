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

# Copy and edit the team config
cp team.yaml.example team.yaml
# Edit team.yaml with your team's details

# Generate the dashboard
teamdash team.yaml
```

Open `dashboard.html` in a browser.

## Usage

```bash
teamdash team.yaml                     # 4 quarters, output dashboard.html
teamdash team.yaml -o report.html      # custom output path
teamdash team.yaml -q 6               # last 6 quarters
teamdash team.yaml --no-cache          # skip cache, fetch fresh data
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

Each engineer needs at least one of `github` or `gitlab`.

## Dashboard

The generated HTML file includes:

- **Summary cards** -- Total PRs+MRs, GitHub PRs, GitLab MRs, Code Reviews (with % change vs previous quarter)
- **Overview tab** -- PRs+MRs trend and Code Reviews trend line charts per engineer
- **Details tab** -- GitHub vs GitLab breakdown bar chart, review share doughnut chart
- **Full Table tab** -- Sortable table with all metrics per engineer per quarter

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
    cli.py              # CLI entry point (argparse)
    config.py           # YAML config loading and validation
    quarters.py         # Quarter date range calculation
    models.py           # Data classes
    fetch_github.py     # GitHub data fetching via gh CLI
    fetch_gitlab.py     # GitLab data fetching via glab CLI
    aggregate.py        # Orchestration and caching
    dashboard.py        # HTML dashboard generation
  team.yaml.example     # Example configuration
  pyproject.toml        # Package configuration
  requirements.txt
```
