from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime


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


def fetch_mr_merge_times(gitlab_url: str, username: str, start: str, end: str) -> list[float]:
    host = gitlab_url.rstrip("/")
    hostname = _extract_hostname(host)
    base = (
        f"{host}/api/v4/merge_requests?author_username={username}"
        f"&created_after={start}T00:00:00Z&created_before={end}T23:59:59Z"
        f"&state=merged&scope=all&per_page=100"
    )

    merge_times: list[float] = []
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
            return merge_times

        if result.returncode != 0:
            print(f"[WARN] GitLab API error for {username}: {result.stderr.strip()}", file=sys.stderr)
            return merge_times

        try:
            data = json.loads(result.stdout)
            if not isinstance(data, list):
                return merge_times
            for mr in data:
                created = mr.get("created_at")
                merged = mr.get("merged_at")
                if created and merged:
                    dt_created = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    dt_merged = datetime.fromisoformat(merged.replace("Z", "+00:00"))
                    days = (dt_merged - dt_created).total_seconds() / 86400
                    merge_times.append(round(days, 1))
            if len(data) < 100:
                break
            page += 1
        except json.JSONDecodeError:
            print(f"[WARN] Invalid JSON from GitLab API for {username}", file=sys.stderr)
            return merge_times

    return merge_times


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
