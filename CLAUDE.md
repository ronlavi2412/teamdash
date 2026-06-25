# Teamdash

Python CLI that generates interactive HTML dashboards of team engineering metrics from GitHub, GitLab, and Jira.

## Quick Reference

- **Stack:** Python 3.10+ (dataclasses, argparse, pytest), React 19 + Chart.js (Vite build)
- **Entry point:** `teamdash/cli.py` -- four subcommands: default (fetch+generate), `fetch`, `fetch-jira`, `generate`
- **Data models:** `teamdash/models.py` -- `Quarter`, `PRDetail`, `ScoredPR`, `EngineerQuarterMetrics`, `QuarterSummary`
- **Dashboard frontend:** `dashboard/src/` -- React app with Chart.js, built to `dashboard/dist/`

## Key Rules

- Use `from __future__ import annotations` at the top of every Python module
- Data models use `dataclasses`, not Pydantic
- API credentials resolve from env vars (`JIRA_EMAIL`, `JIRA_API_TOKEN`), never from `.env` files
- Errors/progress go to stderr with `[WARN]`/`[ERROR]` prefixes
- When adding fields: update `models.py`, `dashboard/src/types.ts`, cache logic in `aggregate.py`, and fixtures in `tests/conftest.py`

## Commands

```bash
pip install -e ".[dev]"
python -m pytest tests/ -x -q       # Python tests
cd dashboard && npm run lint         # Dashboard lint
cd dashboard && npm run test:e2e     # Playwright E2E tests
```

## Full Context

See [AGENTS.md](AGENTS.md) for repo structure, key patterns, and review guidelines.
See [ARCHITECTURE.md](ARCHITECTURE.md) for system design and data flow.
See [CONTRIBUTING.md](CONTRIBUTING.md) for development workflow.
