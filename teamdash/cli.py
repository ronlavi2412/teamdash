from __future__ import annotations

import argparse
import json
import sys

from teamdash.aggregate import collect_all_data
from teamdash.config import load_config
from teamdash.dashboard import (
    build_dashboard_data,
    generate_dashboard,
    generate_dashboard_from_data,
)
from teamdash.fetch_github import check_auth
from teamdash.quarters import get_quarters


def _add_fetch_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("config", help="Path to team.yaml config file")
    parser.add_argument("-q", "--quarters", type=int, default=4,
                        help="Number of quarters to include (default: 4)")
    parser.add_argument("--no-cache", action="store_true",
                        help="Skip cache and fetch fresh data from APIs")
    parser.add_argument("--include-current", action="store_true",
                        help="Include the current (in-progress) quarter")
    parser.add_argument("--no-scoring", action="store_true",
                        help="Skip story point estimation (faster, fewer API calls)")
    parser.add_argument("--refresh-gitlab", action="store_true",
                        help="Re-fetch only GitLab data, keep cached GitHub data")
    parser.add_argument("--jira-data", default=None,
                        help="Path to pre-fetched Jira verified bugs JSON file")


def _do_fetch(args: argparse.Namespace) -> tuple:
    config = load_config(args.config)

    if not args.refresh_gitlab and config.github_orgs and not check_auth():
        print("[ERROR] GitHub CLI not authenticated. Run: gh auth login", file=sys.stderr)
        sys.exit(1)

    jira_data = None
    if args.jira_data:
        from teamdash.fetch_jira import load_jira_data
        jira_data = load_jira_data(args.jira_data)

    quarters = get_quarters(args.quarters, include_current=args.include_current)
    print(f"Fetching data for {config.team_name} ({len(config.engineers)} engineers, "
          f"{len(quarters)} quarters)...", file=sys.stderr)

    summaries = collect_all_data(
        config, quarters,
        use_cache=not args.no_cache,
        enable_scoring=not args.no_scoring,
        refresh_gitlab=args.refresh_gitlab,
        jira_data=jira_data,
    )
    return config, summaries


def _cmd_fetch(args: argparse.Namespace) -> None:
    config, summaries = _do_fetch(args)
    data = build_dashboard_data(config, summaries)
    output = args.output or "data.json"
    with open(output, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Data written to {output}", file=sys.stderr)


def _cmd_generate(args: argparse.Namespace) -> None:
    with open(args.data) as f:
        data = json.load(f)
    output = args.output or "dashboard.html"
    generate_dashboard_from_data(data, output)
    print(f"Dashboard written to {output}", file=sys.stderr)


def main() -> None:
    args = sys.argv[1:]

    if args and args[0] == "fetch":
        parser = argparse.ArgumentParser(
            prog="teamdash fetch",
            description="Fetch data and write JSON (no dashboard generation)",
        )
        _add_fetch_args(parser)
        parser.add_argument("-o", "--output", default=None,
                            help="Output JSON file path (default: data.json)")
        _cmd_fetch(parser.parse_args(args[1:]))

    elif args and args[0] == "generate":
        parser = argparse.ArgumentParser(
            prog="teamdash generate",
            description="Generate dashboard HTML from a data.json file",
        )
        parser.add_argument("data", help="Path to data.json file")
        parser.add_argument("-o", "--output", default=None,
                            help="Output HTML file path (default: dashboard.html)")
        _cmd_generate(parser.parse_args(args[1:]))

    else:
        parser = argparse.ArgumentParser(
            prog="teamdash",
            description="Generate an interactive HTML dashboard of team engineering metrics",
        )
        _add_fetch_args(parser)
        parser.add_argument("-o", "--output", default="dashboard.html",
                            help="Output HTML file path (default: dashboard.html)")
        parsed = parser.parse_args(args)
        config, summaries = _do_fetch(parsed)
        generate_dashboard(config, summaries, parsed.output)
        print(f"Dashboard written to {parsed.output}", file=sys.stderr)
