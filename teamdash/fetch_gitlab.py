from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timedelta

from teamdash.models import PRDetail


def _in_date_range(timestamp: str, start: str, end: str) -> bool:
    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    start_dt = datetime.fromisoformat(f"{start}T00:00:00+00:00")
    end_dt = datetime.fromisoformat(f"{end}T00:00:00+00:00") + timedelta(days=1)
    return start_dt <= dt < end_dt


def _glab_api_get(
    gitlab_url: str, endpoint: str,
) -> dict | list | None:
    hostname = _extract_hostname(gitlab_url)
    cmd = ["glab", "api", endpoint, "--hostname", hostname]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def fetch_mrs(gitlab_url: str, username: str, start: str, end: str) -> int:
    host = gitlab_url.rstrip("/")
    hostname = _extract_hostname(host)
    base = (
        f"{host}/api/v4/merge_requests?author_username={username}"
        f"&state=merged&updated_after={start}T00:00:00Z&updated_before={end}T23:59:59Z"
        f"&scope=all&per_page=100"
    )

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
            for mr in data:
                merged = mr.get("merged_at")
                if merged and _in_date_range(merged, start, end):
                    total += 1
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
        f"&state=merged&updated_after={start}T00:00:00Z&updated_before={end}T23:59:59Z"
        f"&scope=all&per_page=100"
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
                if created and merged and _in_date_range(merged, start, end):
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


def _fetch_mr_list(
    gitlab_url: str, username: str, start: str, end: str,
) -> list[dict]:
    host = gitlab_url.rstrip("/")
    hostname = _extract_hostname(host)
    base = (
        f"{host}/api/v4/merge_requests?author_username={username}"
        f"&state=merged&updated_after={start}T00:00:00Z&updated_before={end}T23:59:59Z"
        f"&scope=all&per_page=100"
    )
    items: list[dict] = []
    page = 1
    while True:
        endpoint = f"{base}&page={page}"
        cmd = ["glab", "api", endpoint, "--hostname", hostname]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return items
        if result.returncode != 0:
            return items
        try:
            data = json.loads(result.stdout)
            if not isinstance(data, list):
                return items
            for mr in data:
                merged = mr.get("merged_at")
                if merged and _in_date_range(merged, start, end):
                    items.append(mr)
            if len(data) < 100:
                break
            page += 1
        except json.JSONDecodeError:
            return items
    return items


def fetch_mr_details(
    gitlab_url: str, username: str, start: str, end: str,
) -> list[PRDetail]:
    mrs = _fetch_mr_list(gitlab_url, username, start, end)
    details: list[PRDetail] = []

    for mr in mrs:
        project_id = mr.get("project_id")
        iid = mr.get("iid")
        if not project_id or not iid:
            continue

        host = gitlab_url.rstrip("/")
        mr_detail = _glab_api_get(
            gitlab_url,
            f"{host}/api/v4/projects/{project_id}/merge_requests/{iid}",
        )
        time.sleep(0.5)

        additions = 0
        deletions = 0
        changed_files = 0
        if isinstance(mr_detail, dict):
            changes = mr_detail.get("changes_count")
            if changes is not None:
                try:
                    changed_files = int(changes)
                except (ValueError, TypeError):
                    pass
            diff_stats = mr_detail.get("diff_refs")
            if "additions" in mr_detail:
                additions = mr_detail.get("additions", 0) or 0
            if "deletions" in mr_detail:
                deletions = mr_detail.get("deletions", 0) or 0

        notes_data = _glab_api_get(
            gitlab_url,
            f"{host}/api/v4/projects/{project_id}/merge_requests/{iid}/notes?per_page=100",
        )
        time.sleep(0.5)

        review_count = 0
        comments_count = 0
        if isinstance(notes_data, list):
            author_user = mr.get("author", {}).get("username", "")
            non_author_notes = [
                n for n in notes_data
                if n.get("author", {}).get("username") != author_user
                and not n.get("system", False)
            ]
            review_count = len(non_author_notes)
            comments_count = review_count

        labels = mr.get("labels", [])
        created = mr.get("created_at", "")
        merged = mr.get("merged_at")
        closed = merged or mr.get("closed_at")
        merge_time = None
        if created and closed:
            dt_created = datetime.fromisoformat(created.replace("Z", "+00:00"))
            dt_closed = datetime.fromisoformat(closed.replace("Z", "+00:00"))
            merge_time = round(
                (dt_closed - dt_created).total_seconds() / 86400, 1
            )

        details.append(PRDetail(
            url=mr.get("web_url", ""),
            source="gitlab",
            author=username,
            additions=additions,
            deletions=deletions,
            changed_files=changed_files,
            labels=labels,
            review_count=review_count,
            changes_requested_count=0,
            comments_count=comments_count,
            merge_time_days=merge_time,
            created_at=created,
            closed_at=closed,
        ))

    return details


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
