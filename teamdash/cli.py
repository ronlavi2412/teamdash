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
    parser.add_argument("config", help="Path to team.json config file")
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


def _load_jira_raw(path: str) -> dict | None:
    from pathlib import Path
    try:
        data = json.loads(Path(path).read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return None
    if isinstance(data, dict) and "jiraData" in data:
        return data["jiraData"]
    if isinstance(data, dict):
        return data
    return None


def _cmd_fetch(args: argparse.Namespace) -> None:
    config, summaries = _do_fetch(args)
    jira_raw = _load_jira_raw(args.jira_data) if args.jira_data else None
    cycle_time_data = jira_raw.get("cycle_times") if jira_raw else None
    data = build_dashboard_data(config, summaries, jira_raw=jira_raw, cycle_time_data=cycle_time_data)
    output = args.output or "data.json"
    with open(output, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Data written to {output}", file=sys.stderr)


def _cmd_fetch_jira(args: argparse.Namespace) -> None:
    from teamdash.fetch_jira_api import check_auth as check_jira_auth
    from teamdash.fetch_jira_api import fetch_all_jira_data, get_credentials

    config = load_config(args.config)
    if not config.jira:
        print("[ERROR] No jira section in config", file=sys.stderr)
        sys.exit(1)

    email, token = get_credentials()
    if not check_jira_auth(config.jira.cloud_id, email, token):
        print("[ERROR] Jira authentication failed. Check JIRA_EMAIL and JIRA_API_TOKEN",
              file=sys.stderr)
        sys.exit(1)

    quarters = get_quarters(args.quarters, include_current=args.include_current)
    print(f"Fetching Jira data for {config.team_name} ({len(quarters)} quarters)...",
          file=sys.stderr)

    jira_data = fetch_all_jira_data(config, quarters, email, token)

    output = args.output or "jira-data.json"
    result: dict = {}
    for q_label, eng_bugs in jira_data.bugs.items():
        result[q_label] = eng_bugs
    if jira_data.activity_types:
        result["activity_types"] = jira_data.activity_types
    if jira_data.cycle_times:
        result["cycle_times"] = jira_data.cycle_times

    with open(output, "w") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(f"Jira data written to {output}", file=sys.stderr)


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

    elif args and args[0] == "fetch-jira":
        parser = argparse.ArgumentParser(
            prog="teamdash fetch-jira",
            description="Fetch Jira data (verified bugs, activity types, cycle times) and write JSON",
        )
        parser.add_argument("config", help="Path to team.json config file")
        parser.add_argument("-q", "--quarters", type=int, default=4,
                            help="Number of quarters to include (default: 4)")
        parser.add_argument("--include-current", action="store_true",
                            help="Include the current (in-progress) quarter")
        parser.add_argument("-o", "--output", default=None,
                            help="Output JSON file path (default: jira-data.json)")
        _cmd_fetch_jira(parser.parse_args(args[1:]))

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
        jira_raw = _load_jira_raw(parsed.jira_data) if parsed.jira_data else None
        cycle_time_data = jira_raw.get("cycle_times") if jira_raw else None
        generate_dashboard(config, summaries, parsed.output, cycle_time_data=cycle_time_data)
        print(f"Dashboard written to {parsed.output}", file=sys.stderr)
