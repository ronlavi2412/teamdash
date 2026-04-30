from __future__ import annotations

import json
import subprocess
import sys
import time


def _gh_search_count(query: str) -> int:
    cmd = ["gh", "api", f"/search/issues?q={query}&per_page=1"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        print("[ERROR] 'gh' CLI not found. Install it: https://cli.github.com/", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print(f"[WARN] GitHub API timed out for query: {query}", file=sys.stderr)
        return 0

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "rate limit" in stderr.lower() or "403" in stderr:
            print("[WARN] GitHub rate limit hit, waiting 60s...", file=sys.stderr)
            time.sleep(60)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                print(f"[WARN] GitHub API still failing: {stderr}", file=sys.stderr)
                return 0
        else:
            print(f"[WARN] GitHub API error: {stderr}", file=sys.stderr)
            return 0

    try:
        data = json.loads(result.stdout)
        return data.get("total_count", 0)
    except json.JSONDecodeError:
        print(f"[WARN] Invalid JSON from GitHub API", file=sys.stderr)
        return 0


def fetch_prs(username: str, orgs: list[str], start: str, end: str) -> int:
    total = 0
    for org in orgs:
        query = f"type:pr+author:{username}+org:{org}+created:{start}..{end}"
        total += _gh_search_count(query)
        time.sleep(2)
    return total


def fetch_reviews(username: str, orgs: list[str], start: str, end: str) -> int:
    total = 0
    for org in orgs:
        query = f"type:pr+reviewed-by:{username}+org:{org}+-author:{username}+created:{start}..{end}"
        total += _gh_search_count(query)
        time.sleep(2)
    return total


def check_auth() -> bool:
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
