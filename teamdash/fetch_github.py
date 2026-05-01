from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from datetime import datetime

from teamdash.models import PRDetail

_throttle_lock = threading.Lock()
_request_times: list[float] = []
_MAX_REQUESTS_PER_MINUTE = 25


def _throttle() -> None:
    with _throttle_lock:
        now = time.monotonic()
        cutoff = now - 60
        _request_times[:] = [t for t in _request_times if t > cutoff]
        if len(_request_times) >= _MAX_REQUESTS_PER_MINUTE:
            wait = _request_times[0] - cutoff
            if wait > 0:
                time.sleep(wait)
        _request_times.append(time.monotonic())


def _is_rate_limit(stderr: str) -> bool:
    lower = stderr.lower()
    return "rate limit" in lower or "403" in lower


def _run_gh(cmd: list[str], retries: int = 3) -> subprocess.CompletedProcess | None:
    _throttle()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired:
        return None

    if result.returncode == 0:
        return result

    stderr = result.stderr.strip()
    if not _is_rate_limit(stderr):
        return result

    delays = [30, 60, 120]
    for attempt in range(retries):
        delay = delays[min(attempt, len(delays) - 1)]
        print(f"[WARN] GitHub rate limit hit, retrying in {delay}s (attempt {attempt + 1}/{retries})...", file=sys.stderr)
        time.sleep(delay)
        _throttle()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired:
            continue
        if result.returncode == 0:
            return result
        if not _is_rate_limit(result.stderr.strip()):
            return result

    print(f"[WARN] GitHub API still failing after {retries} retries: {stderr}", file=sys.stderr)
    return result


def _orgs_query(orgs: list[str]) -> str:
    return "+".join(f"org:{org}" for org in orgs)


def _gh_api_get(endpoint: str) -> dict | list | None:
    result = _run_gh(["gh", "api", endpoint])
    if result is None or result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def _gh_search_count(query: str) -> int:
    cmd = ["gh", "api", f"/search/issues?q={query}&per_page=1"]
    result = _run_gh(cmd)

    if result is None:
        print("[ERROR] 'gh' CLI not found or timed out.", file=sys.stderr)
        sys.exit(1)

    if result.returncode != 0:
        print(f"[WARN] GitHub API error: {result.stderr.strip()}", file=sys.stderr)
        return 0

    try:
        data = json.loads(result.stdout)
        return data.get("total_count", 0)
    except json.JSONDecodeError:
        print("[WARN] Invalid JSON from GitHub API", file=sys.stderr)
        return 0


def _gh_search_items(query: str) -> list[dict]:
    items: list[dict] = []
    page = 1
    while True:
        cmd = ["gh", "api", f"/search/issues?q={query}&per_page=100&page={page}"]
        result = _run_gh(cmd)

        if result is None:
            print("[ERROR] 'gh' CLI not found or timed out.", file=sys.stderr)
            sys.exit(1)

        if result.returncode != 0:
            print(f"[WARN] GitHub API error: {result.stderr.strip()}", file=sys.stderr)
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


def fetch_merge_times(username: str, orgs: list[str], start: str, end: str) -> list[float]:
    query = f"type:pr+author:{username}+{_orgs_query(orgs)}+merged:{start}..{end}"
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


def fetch_prs(username: str, orgs: list[str], start: str, end: str) -> int:
    query = f"type:pr+author:{username}+{_orgs_query(orgs)}+merged:{start}..{end}"
    return _gh_search_count(query)


def fetch_reviews(username: str, orgs: list[str], start: str, end: str) -> int:
    query = f"type:pr+reviewed-by:{username}+{_orgs_query(orgs)}+-author:{username}+merged:{start}..{end}"
    return _gh_search_count(query)


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

        reviews_data = _gh_api_get(f"/repos/{owner}/{repo}/pulls/{number}/reviews")

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


def fetch_pr_details(
    username: str, orgs: list[str], start: str, end: str,
) -> list[PRDetail]:
    query = f"type:pr+author:{username}+{_orgs_query(orgs)}+merged:{start}..{end}"
    return _fetch_details_for_query(query, author=username)


def fetch_reviewed_pr_details(
    username: str, orgs: list[str], start: str, end: str,
) -> list[PRDetail]:
    query = f"type:pr+reviewed-by:{username}+-author:{username}+{_orgs_query(orgs)}+merged:{start}..{end}"
    return _fetch_details_for_query(query, author=username)


def check_auth() -> bool:
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
