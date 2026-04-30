# Agents

## Project Overview

Teamdash is a Python CLI tool that generates interactive HTML dashboards from GitHub and GitLab engineering metrics. It reads a `team.yaml` config, fetches data via `gh` and `glab` CLIs, and outputs a self-contained HTML file with Chart.js charts.

## Architecture

Single-package Python project (`teamdash/`) with no framework. The data flow is:

```
team.yaml -> config.py -> aggregate.py -> dashboard.py -> HTML file
                              |
                    fetch_github.py (gh api subprocess)
                    fetch_gitlab.py (glab api subprocess)
```

- **No web framework** -- generates static HTML, no server
- **No ORM or database** -- data is fetched live from APIs and cached as JSON in `~/.cache/teamdash/`
- **External CLIs** -- uses `gh` and `glab` subprocesses for API auth, not raw HTTP requests
- **Chart.js v4** loaded from CDN in the generated HTML

## Key Patterns

- API calls use subprocess to `gh api` / `glab api` rather than HTTP libraries, leveraging the user's existing CLI auth sessions
- GitHub search API has a 30 req/min rate limit; `fetch_github.py` sleeps 2s between requests
- Dashboard HTML is built with Python f-strings from a large template constant in `dashboard.py`
- All data is passed to the template as inline JavaScript arrays
- Caching is daily and keyed by config hash; `--no-cache` skips reading the cache but still writes it

## Running

```bash
pip install .
teamdash team.yaml
```

## Testing

No test suite yet. Verify changes by running against `team.yaml.example` and checking the generated HTML opens correctly in a browser with populated charts.

## Style

- Python 3.10+ with `from __future__ import annotations`
- Dataclasses for data models (no Pydantic)
- Errors and progress go to stderr, only the dashboard file is the output
- Warnings are `[WARN]`, errors are `[ERROR]` prefixed on stderr
