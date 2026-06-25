# Contributing to Teamdash

## Getting Started

For installation, prerequisites, and basic usage, see [README.md](README.md#quick-start).

## Development Setup

Follow [README.md](README.md#quick-start) to install, then add dev dependencies with `pip install -e ".[dev]"`.

For dashboard frontend work, install Node dependencies in `dashboard/` and use `npm run dev` for the Vite dev server. After changing frontend code, rebuild with `npm run build` so that `dashboard.py` embeds the updated bundle.

## Coding Standards

### Python

- Target Python 3.10+. Use `from __future__ import annotations` at the top of every module.
- Use `dataclasses` for data models (no Pydantic).
- Errors and progress go to stderr via `print(..., file=sys.stderr)`. Prefix warnings with `[WARN]` and errors with `[ERROR]`.
- API credentials resolve from environment variables (`JIRA_EMAIL`, `JIRA_API_TOKEN`), never from `.env` files or config.

### TypeScript (Dashboard)

- React 19 with functional components and hooks.
- ESLint with `typescript-eslint` and `eslint-plugin-react-hooks` (enforced by `npm run lint`).
- TypeScript strict mode via `tsconfig.app.json`.

## Testing

### Python Tests

```bash
python -m pytest tests/ -x -q
```

11 test files cover all core modules. Tests use `unittest.mock` to patch subprocess and HTTP calls -- no real API calls are made. Shared fixtures are in `tests/conftest.py`.

To skip end-to-end tests that require real API credentials:

```bash
python -m pytest tests/ -x -q -m "not e2e"
```

### Dashboard E2E Tests

```bash
cd dashboard
npm run test:e2e
```

Playwright tests run against generated HTML fixtures in `dashboard/e2e/fixtures/`. The fixture generator (`e2e/fixtures/generate-test-html.py`) creates test HTML files before each run.

## PR Process

1. Create a branch from `main`.
2. Make changes. Ensure `pytest` and `npm run lint` (in `dashboard/`) pass.
3. Commit with a clear message describing the change.
4. Push and open a PR against `main`.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for system design, data flow, and component relationships.
