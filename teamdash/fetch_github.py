from __future__ import annotations

import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from teamdash.models import PRDetail


def _gh_api_get(endpoint: str) -> dict | list | None:
    cmd = ["gh", "api", endpoint]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "rate limit" in stderr.lower() or "403" in stderr:
            print("[WARN] GitHub rate limit hit, waiting 60s...", file=sys.stderr)
            time.sleep(60)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return None
        else:
            return None

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


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


def _gh_search_items(query: str) -> list[dict]:
    items: list[dict] = []
    page = 1
    while True:
        cmd = ["gh", "api", f"/search/issues?q={query}&per_page=100&page={page}"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except FileNotFoundError:
            print("[ERROR] 'gh' CLI not found. Install it: https://cli.github.com/", file=sys.stderr)
            sys.exit(1)
        except subprocess.TimeoutExpired:
            print(f"[WARN] GitHub API timed out for query: {query}", file=sys.stderr)
            return items

        if result.returncode != 0:
            stderr = result.stderr.strip()
            if "rate limit" in stderr.lower() or "403" in stderr:
                print("[WARN] GitHub rate limit hit, waiting 60s...", file=sys.stderr)
                time.sleep(60)
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    print(f"[WARN] GitHub API still failing: {stderr}", file=sys.stderr)
                    return items
            else:
                print(f"[WARN] GitHub API error: {stderr}", file=sys.stderr)
                return items

        try:
            data = json.loads(result.stdout)
            page_items = data.get("items", [])
            items.extend(page_items)
            if len(page_items) < 100:
                break
            page += 1
        except json.JSONDecodeError:
            print("[WARN] Invalid JSON from GitHub API", file=sys.stderr)
            return items

    return items


def _fetch_merge_times_for_org(username: str, org: str, start: str, end: str) -> list[float]:
    query = f"type:pr+author:{username}+org:{org}+created:{start}..{end}+is:merged"
    items = _gh_search_items(query)
    merge_times: list[float] = []
    for item in items:
        created = item.get("created_at")
        closed = item.get("closed_at")
        if created and closed:
            dt_created = datetime.fromisoformat(created.replace("Z", "+00:00"))
            dt_closed = datetime.fromisoformat(closed.replace("Z", "+00:00"))
            days = (dt_closed - dt_created).total_seconds() / 86400
            merge_times.append(round(days, 1))
    return merge_times


def fetch_merge_times(username: str, orgs: list[str], start: str, end: str) -> list[float]:
    with ThreadPoolExecutor(max_workers=len(orgs)) as pool:
        futures = [pool.submit(_fetch_merge_times_for_org, username, org, start, end) for org in orgs]
    merge_times: list[float] = []
    for f in futures:
        merge_times.extend(f.result())
    return merge_times


def fetch_prs(username: str, orgs: list[str], start: str, end: str) -> int:
    def _fetch_org(org: str) -> int:
        query = f"type:pr+author:{username}+org:{org}+created:{start}..{end}"
        return _gh_search_count(query)

    with ThreadPoolExecutor(max_workers=len(orgs)) as pool:
        return sum(pool.map(_fetch_org, orgs))


def fetch_reviews(username: str, orgs: list[str], start: str, end: str) -> int:
    def _fetch_org(org: str) -> int:
        query = f"type:pr+reviewed-by:{username}+org:{org}+-author:{username}+created:{start}..{end}"
        return _gh_search_count(query)

    with ThreadPoolExecutor(max_workers=len(orgs)) as pool:
        return sum(pool.map(_fetch_org, orgs))


def _parse_pr_url(html_url: str) -> tuple[str, str, str] | None:
    parts = html_url.rstrip("/").split("/")
    try:
        idx = parts.index("pull")
        return parts[idx - 2], parts[idx - 1], parts[idx + 1]
    except (ValueError, IndexError):
        return None


def _fetch_details_for_query(query: str, author: str) -> list[PRDetail]:
    items = _gh_search_items(query)
    details: list[PRDetail] = []

    for item in items:
        html_url = item.get("html_url", "")
        parsed = _parse_pr_url(html_url)
        if not parsed:
            continue
        owner, repo, number = parsed

        pr_data = _gh_api_get(f"/repos/{owner}/{repo}/pulls/{number}")
        if not pr_data or not isinstance(pr_data, dict):
            continue
        time.sleep(0.5)

        reviews_data = _gh_api_get(f"/repos/{owner}/{repo}/pulls/{number}/reviews")
        time.sleep(0.5)

        review_count = 0
        changes_requested = 0
        if isinstance(reviews_data, list):
            review_count = len(reviews_data)
            changes_requested = sum(
                1 for r in reviews_data if r.get("state") == "CHANGES_REQUESTED"
            )

        labels = [l.get("name", "") for l in item.get("labels", [])]
        comments_count = item.get("comments", 0)

        created = item.get("created_at", "")
        closed = item.get("closed_at")
        merge_time = None
        if created and closed:
            dt_created = datetime.fromisoformat(created.replace("Z", "+00:00"))
            dt_closed = datetime.fromisoformat(closed.replace("Z", "+00:00"))
            merge_time = round(
                (dt_closed - dt_created).total_seconds() / 86400, 1
            )

        details.append(PRDetail(
            url=html_url,
            source="github",
            author=author,
            additions=pr_data.get("additions", 0),
            deletions=pr_data.get("deletions", 0),
            changed_files=pr_data.get("changed_files", 0),
            labels=labels,
            review_count=review_count,
            changes_requested_count=changes_requested,
            comments_count=comments_count,
            merge_time_days=merge_time,
            created_at=created,
            closed_at=closed,
        ))

    return details


def _fetch_pr_details_for_org(
    username: str, org: str, start: str, end: str,
) -> list[PRDetail]:
    query = f"type:pr+author:{username}+org:{org}+created:{start}..{end}"
    return _fetch_details_for_query(query, author=username)


def fetch_pr_details(
    username: str, orgs: list[str], start: str, end: str,
) -> list[PRDetail]:
    details: list[PRDetail] = []
    for org in orgs:
        details.extend(_fetch_pr_details_for_org(username, org, start, end))
    return details


def _fetch_reviewed_pr_details_for_org(
    username: str, org: str, start: str, end: str,
) -> list[PRDetail]:
    query = f"type:pr+reviewed-by:{username}+-author:{username}+org:{org}+created:{start}..{end}"
    return _fetch_details_for_query(query, author=username)


def fetch_reviewed_pr_details(
    username: str, orgs: list[str], start: str, end: str,
) -> list[PRDetail]:
    details: list[PRDetail] = []
    for org in orgs:
        details.extend(_fetch_reviewed_pr_details_for_org(username, org, start, end))
    return details


def check_auth() -> bool:
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
