from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from datetime import datetime
from urllib.parse import quote

from teamdash.models import PRDetail

_throttle_lock = threading.Lock()
_request_times: list[float] = []
_MAX_REQUESTS_PER_MINUTE = 28


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
        print(
            f"[WARN] GitHub rate limit hit, retrying in {delay}s (attempt {attempt + 1}/{retries})...",
            file=sys.stderr,
        )
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

    print(f"[WARN] GitHub API still failing after {retries} retries", file=sys.stderr)
    return result


def _orgs_query(orgs: list[str]) -> str:
    return "+".join(f"org:{quote(org, safe='')}" for org in orgs)


def _gh_graphql(query: str, variables: dict | None = None) -> dict | None:
    cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
    if variables:
        for k, v in variables.items():
            cmd.extend(["-f", f"{k}={v}"])
    result = _run_gh(cmd)
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


def fetch_merge_times(
    username: str, orgs: list[str], start: str, end: str
) -> list[float]:
    safe_user = quote(username, safe="")
    query = f"type:pr+author:{safe_user}+{_orgs_query(orgs)}+merged:{start}..{end}"
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
    safe_user = quote(username, safe="")
    query = f"type:pr+author:{safe_user}+{_orgs_query(orgs)}+merged:{start}..{end}"
    return _gh_search_count(query)


def fetch_reviews(username: str, orgs: list[str], start: str, end: str) -> int:
    safe_user = quote(username, safe="")
    query = f"type:pr+reviewed-by:{safe_user}+{_orgs_query(orgs)}+-author:{safe_user}+merged:{start}..{end}"
    return _gh_search_count(query)


_SEARCH_PR_DETAILS_QUERY = """
query($q: String!, $cursor: String) {
  search(query: $q, type: ISSUE, first: 100, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes {
      ... on PullRequest {
        title
        url
        additions
        deletions
        changedFiles
        createdAt
        closedAt
        labels(first: 10) { nodes { name } }
        comments { totalCount }
        reviews(first: 100) {
          totalCount
          nodes { state }
        }
      }
    }
  }
}
"""


def _fetch_details_for_query(query: str, author: str) -> list[PRDetail]:
    gql_query = query.replace("+", " ")
    details: list[PRDetail] = []
    cursor = None

    while True:
        variables = {"q": gql_query}
        if cursor:
            variables["cursor"] = cursor
        data = _gh_graphql(_SEARCH_PR_DETAILS_QUERY, variables)
        if not data:
            break

        search = data.get("data", {}).get("search", {})
        for node in search.get("nodes", []):
            if not node or "url" not in node:
                continue

            created = node.get("createdAt", "")
            closed = node.get("closedAt")
            merge_time = None
            if created and closed:
                dt_created = datetime.fromisoformat(created.replace("Z", "+00:00"))
                dt_closed = datetime.fromisoformat(closed.replace("Z", "+00:00"))
                merge_time = round((dt_closed - dt_created).total_seconds() / 86400, 1)

            reviews = node.get("reviews", {})
            review_nodes = reviews.get("nodes", [])
            review_count = reviews.get("totalCount", 0)
            changes_requested = sum(
                1 for r in review_nodes if r.get("state") == "CHANGES_REQUESTED"
            )

            labels = [
                lbl.get("name", "") for lbl in node.get("labels", {}).get("nodes", [])
            ]

            details.append(
                PRDetail(
                    url=node["url"],
                    source="github",
                    author=author,
                    additions=node.get("additions", 0),
                    title=node.get("title", ""),
                    deletions=node.get("deletions", 0),
                    changed_files=node.get("changedFiles", 0),
                    labels=labels,
                    review_count=review_count,
                    changes_requested_count=changes_requested,
                    comments_count=node.get("comments", {}).get("totalCount", 0),
                    merge_time_days=merge_time,
                    created_at=created,
                    closed_at=closed,
                )
            )

        page_info = search.get("pageInfo", {})
        if page_info.get("hasNextPage"):
            cursor = page_info["endCursor"]
        else:
            break

    return details


def fetch_pr_details(
    username: str,
    orgs: list[str],
    start: str,
    end: str,
) -> list[PRDetail]:
    safe_user = quote(username, safe="")
    query = f"type:pr+author:{safe_user}+{_orgs_query(orgs)}+merged:{start}..{end}"
    return _fetch_details_for_query(query, author=username)


def fetch_reviewed_pr_details(
    username: str,
    orgs: list[str],
    start: str,
    end: str,
) -> list[PRDetail]:
    safe_user = quote(username, safe="")
    query = f"type:pr+reviewed-by:{safe_user}+-author:{safe_user}+{_orgs_query(orgs)}+merged:{start}..{end}"
    return _fetch_details_for_query(query, author=username)


def check_auth() -> bool:
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
