from __future__ import annotations

import json
import subprocess
import sys


def fetch_mrs(gitlab_url: str, username: str, start: str, end: str) -> int:
    host = gitlab_url.rstrip("/")
    hostname = _extract_hostname(host)
    base = f"{host}/api/v4/merge_requests?author_username={username}&created_after={start}T00:00:00Z&created_before={end}T23:59:59Z&scope=all&per_page=100"

    total = 0
    page = 1
    while True:
        endpoint = f"{base}&page={page}"
        cmd = ["glab", "api", endpoint, "--hostname", hostname]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except FileNotFoundError:
            print("[ERROR] 'glab' CLI not found. Install it: https://gitlab.com/gitlab-org/cli", file=sys.stderr)
            sys.exit(1)
        except subprocess.TimeoutExpired:
            print(f"[WARN] GitLab API timed out for {username}", file=sys.stderr)
            return total

        if result.returncode != 0:
            print(f"[WARN] GitLab API error for {username}: {result.stderr.strip()}", file=sys.stderr)
            return total

        try:
            data = json.loads(result.stdout)
            if not isinstance(data, list):
                return total
            total += len(data)
            if len(data) < 100:
                break
            page += 1
        except json.JSONDecodeError:
            print(f"[WARN] Invalid JSON from GitLab API for {username}", file=sys.stderr)
            return total

    return total


def _extract_hostname(url: str) -> str:
    return url.split("://", 1)[-1].split("/", 1)[0]


def check_auth(gitlab_url: str) -> bool:
    hostname = _extract_hostname(gitlab_url)
    try:
        result = subprocess.run(
            ["glab", "auth", "status", "--hostname", hostname],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
