from __future__ import annotations

import argparse
import sys

from teamdash.aggregate import collect_all_data
from teamdash.config import load_config
from teamdash.dashboard import generate_dashboard
from teamdash.fetch_github import check_auth
from teamdash.quarters import get_quarters


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="teamdash",
        description="Generate an interactive HTML dashboard of team engineering metrics",
    )
    parser.add_argument("config", help="Path to team.yaml config file")
    parser.add_argument("-o", "--output", default="dashboard.html",
                        help="Output HTML file path (default: dashboard.html)")
    parser.add_argument("-q", "--quarters", type=int, default=4,
                        help="Number of quarters to include (default: 4)")
    parser.add_argument("--no-cache", action="store_true",
                        help="Skip cache and fetch fresh data from APIs")
    parser.add_argument("--include-current", action="store_true",
                        help="Include the current (in-progress) quarter")
    parser.add_argument("--no-scoring", action="store_true",
                        help="Skip story point estimation (faster, fewer API calls)")

    args = parser.parse_args()

    config = load_config(args.config)

    if config.github_orgs and not check_auth():
        print("[ERROR] GitHub CLI not authenticated. Run: gh auth login", file=sys.stderr)
        sys.exit(1)

    quarters = get_quarters(args.quarters, include_current=args.include_current)
    print(f"Fetching data for {config.team_name} ({len(config.engineers)} engineers, "
          f"{len(quarters)} quarters)...", file=sys.stderr)

    summaries = collect_all_data(
        config, quarters,
        use_cache=not args.no_cache,
        enable_scoring=not args.no_scoring,
    )

    generate_dashboard(config.team_name, summaries, args.output)
    print(f"Dashboard written to {args.output}", file=sys.stderr)
