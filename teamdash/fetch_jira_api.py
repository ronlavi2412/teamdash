from __future__ import annotations

import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import requests

from teamdash.config import TeamConfig
from teamdash.fetch_jira import JiraData
from teamdash.models import Quarter

ACTIVITY_TYPES = [
    "Associate Wellness & Development",
    "Future Sustainability",
    "Incidents & Support",
    "Quality / Stability / Reliability",
    "Security & Compliance",
    "Product / Portfolio Work",
]

DEFAULT_SP = 2
SP_FIELD = "customfield_10028"
ACTIVITY_TYPE_FIELD = "customfield_10464"
QA_CONTACT_FIELD = "cf[10470]"
MAX_RESULTS = 100

DEV_START_STATUSES = ["assigned", "in progress", "post"]
DEV_END_STATUSES = ["modified", "dev complete"]
QE_START_STATUSES = ["on_qa", "testing"]


def get_credentials() -> tuple[str, str]:
    email = os.environ.get("JIRA_EMAIL", "")
    token = os.environ.get("JIRA_API_TOKEN", "")
    if not email or not token:
        print(
            "[ERROR] JIRA_EMAIL and JIRA_API_TOKEN environment variables are required",
            file=sys.stderr,
        )
        sys.exit(1)
    return email, token


def check_auth(cloud_id: str, email: str, token: str) -> bool:
    url = f"https://{cloud_id}/rest/api/3/myself"
    try:
        resp = requests.get(url, auth=(email, token), timeout=10)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def _jira_search(
    cloud_id: str,
    jql: str,
    fields: list[str],
    email: str,
    token: str,
) -> list[dict]:
    url = f"https://{cloud_id}/rest/api/3/search/jql"
    all_issues: list[dict] = []
    next_page_token: str | None = None

    while True:
        body: dict = {
            "jql": jql,
            "fields": fields,
            "maxResults": MAX_RESULTS,
        }
        if next_page_token:
            body["nextPageToken"] = next_page_token

        resp = requests.post(url, json=body, auth=(email, token), timeout=30)
        if resp.status_code != 200:
            print(
                f"[WARN] Jira search failed (HTTP {resp.status_code})",
                file=sys.stderr,
            )
            break

        data = resp.json()
        issues = data.get("issues", [])
        all_issues.extend(issues)

        next_page_token = data.get("nextPageToken")
        if not next_page_token or not issues:
            break

    return all_issues


def _fetch_changelog(
    cloud_id: str,
    issue_key: str,
    email: str,
    token: str,
) -> dict:
    url = f"https://{cloud_id}/rest/api/3/issue/{issue_key}/changelog"
    histories: list[dict] = []
    start_at = 0

    while True:
        resp = requests.get(
            url,
            params={"startAt": start_at, "maxResults": MAX_RESULTS},
            auth=(email, token),
            timeout=30,
        )
        if resp.status_code != 200:
            break
        data = resp.json()
        values = data.get("values", [])
        histories.extend(values)
        if data.get("isLast", True) or not values:
            break
        start_at += len(values)

    return {"histories": histories}


def _jira_search_with_changelog(
    cloud_id: str,
    jql: str,
    fields: list[str],
    email: str,
    token: str,
) -> list[dict]:
    issues = _jira_search(cloud_id, jql, fields, email, token)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(_fetch_changelog, cloud_id, issue["key"], email, token): issue
            for issue in issues
        }
        for fut in as_completed(futures):
            issue = futures[fut]
            try:
                issue["changelog"] = fut.result()
            except Exception:
                issue["changelog"] = {"histories": []}

    return issues


def _sum_story_points(issues: list[dict]) -> int:
    total = 0
    for issue in issues:
        sp = issue.get("fields", {}).get(SP_FIELD)
        total += int(sp) if sp and sp > 0 else DEFAULT_SP
    return total


def _jql_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _project_clause(project_keys: list[str]) -> str:
    for key in project_keys:
        if not re.match(r"^[A-Za-z][A-Za-z0-9_]+$", key):
            raise ValueError(f"Invalid Jira project key: {key}")
    return "project in (" + ", ".join(project_keys) + ")"


def _business_days(start: datetime, end: datetime) -> float:
    if end <= start:
        return 0.0
    days = 0
    current = start
    while current.date() < end.date():
        current += timedelta(days=1)
        if current.weekday() < 5:
            days += 1
    return float(days)


def _find_first_transition_to(
    changelog: dict,
    target_statuses: list[str],
) -> str | None:
    histories = changelog.get("histories", [])
    if not histories:
        return None

    sorted_asc = sorted(histories, key=lambda h: h.get("created", ""))

    for history in sorted_asc:
        for item in history.get("items", []):
            if item.get("field") != "status":
                continue
            to_status = (item.get("toString") or "").lower()
            if any(s in to_status for s in target_statuses):
                return history["created"]

    return None


def _get_first_done_date(issue: dict) -> str | None:
    """Get the date when an issue first became 'done' (VERIFIED, Closed, or Release Pending).

    Uses changelog to find the first transition to any done status. Falls back to
    resolutiondate or updated date if changelog unavailable.

    Args:
        issue: Jira issue dict with fields and optional changelog

    Returns:
        ISO timestamp string when issue first became done, or None if not done
    """
    # Priority 1: Use changelog to find first transition to any DONE_STATUSES
    changelog = issue.get("changelog", {})
    if changelog and changelog.get("histories"):
        done_statuses_lower = [
            s.lower() for s in ("Verified", "Closed", "Release Pending")
        ]
        first_done = _find_first_transition_to(changelog, done_statuses_lower)
        if first_done:
            return first_done

    # Priority 2: Fall back to resolutiondate if changelog unavailable
    fields = issue.get("fields", {})
    resolution_date = fields.get("resolutiondate")
    if resolution_date:
        return resolution_date

    # Priority 3: For issues in done status but no resolutiondate, use updated date
    # (This handles issues that were manually moved without proper resolution)
    current_status = fields.get("status", {}).get("name", "")
    done_statuses = ("Verified", "Closed", "Release Pending")
    if any(s.lower() in current_status.lower() for s in done_statuses):
        return fields.get("updated")

    return None


def _is_date_in_range(date_str: str | None, start_date: str, end_date: str) -> bool:
    """Check if a date string falls within the given range.

    Args:
        date_str: ISO timestamp (e.g., "2025-01-15T10:00:00.000+0000")
        start_date: Start date in "YYYY-MM-DD" format
        end_date: End date in "YYYY-MM-DD" format

    Returns:
        True if date falls in range (inclusive), False otherwise
    """
    if not date_str:
        return False

    try:
        # Parse the ISO timestamp and extract just the date part
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        issue_date = dt.date().isoformat()

        # Compare as strings (YYYY-MM-DD format)
        return start_date <= issue_date <= end_date
    except (ValueError, AttributeError):
        return False


DONE_STATUSES = ("Verified", "Closed", "Release Pending")
CUSTOMER_CASE_LINK_TYPE = "Account"
CUSTOMER_CASE_KEY_PREFIX = "CIPOE-"


def _extract_customer_cases(issue: dict) -> list[dict]:
    cases = []
    for link in issue.get("fields", {}).get("issuelinks", []):
        if (link.get("type", {}).get("name") or "") != CUSTOMER_CASE_LINK_TYPE:
            continue
        outward = link.get("outwardIssue")
        if not outward:
            continue
        key = outward.get("key", "")
        if not key.startswith(CUSTOMER_CASE_KEY_PREFIX):
            continue
        cases.append(
            {
                "case_id": key,
                "customer_name": (outward.get("fields") or {}).get("summary", ""),
            }
        )
    return cases


def _done_clause(start_date: str, end_date: str) -> str:
    """Fast JQL clause for issues resolved in quarter (Pass 1 - no changelog needed).

    Fetches issues that:
    1. Have resolution in (Done, Done-Errata) OR status in (Verified, Closed, Release Pending)
    2. AND resolutiondate in quarter OR (no resolutiondate AND updated in quarter)

    This catches ~95% of cases without needing changelog data.
    """
    statuses = ", ".join(f'"{s}"' for s in DONE_STATUSES)
    return (
        f'(resolution in (Done, "Done-Errata") OR status in ({statuses}))'
        f" AND ("
        f'(resolutiondate >= "{start_date}" AND resolutiondate <= "{end_date}")'
        f" OR "
        f'(resolutiondate is EMPTY AND updated >= "{start_date}" AND updated <= "{end_date}")'
        f")"
    )


def fetch_verified_bugs(
    cloud_id: str,
    project_keys: list[str],
    start_date: str,
    end_date: str,
    email: str,
    token: str,
) -> int:
    """Fetch verified bug story points for a quarter.

    Uses dual-pass approach:
    - Pass 1 (fast): Issues resolved in quarter via resolutiondate/updated
    - Pass 2 (targeted): Issues verified in quarter but resolved later (uses changelog)

    Args:
        cloud_id: Jira cloud ID
        project_keys: List of project keys to search
        start_date: Quarter start date (YYYY-MM-DD)
        end_date: Quarter end date (YYYY-MM-DD)
        email: Jira email for auth
        token: Jira API token

    Returns:
        Total story points for bugs that first became done in this quarter
    """
    # Pass 1: Fast query - most issues (no changelog needed)
    jql1 = (
        f"issuetype = Bug AND {_done_clause(start_date, end_date)}"
        f" AND {_project_clause(project_keys)}"
    )
    issues_pass1 = _jira_search(cloud_id, jql1, ["summary", SP_FIELD], email, token)
    pass1_keys = {issue["key"] for issue in issues_pass1}
    sp_pass1 = _sum_story_points(issues_pass1)

    # Pass 2: Edge cases - issues verified in quarter but resolved later
    # Use 30-day buffer to catch issues verified near end of quarter
    buffer_end = (
        (datetime.fromisoformat(end_date) + timedelta(days=30)).date().isoformat()
    )
    statuses = ", ".join(f'"{s}"' for s in DONE_STATUSES)
    jql2 = (
        f"issuetype = Bug"
        f' AND (status in ({statuses}) OR resolution in (Done, "Done-Errata"))'
        f' AND resolutiondate > "{end_date}"'  # Resolved AFTER quarter
        f' AND updated >= "{start_date}" AND updated <= "{buffer_end}"'
        f" AND {_project_clause(project_keys)}"
    )
    issues_pass2 = _jira_search_with_changelog(
        cloud_id,
        jql2,
        ["summary", SP_FIELD, "resolutiondate", "status", "updated"],
        email,
        token,
    )

    # Filter: verified in quarter AND not already in pass1
    filtered_pass2 = [
        issue
        for issue in issues_pass2
        if issue["key"] not in pass1_keys
        and _is_date_in_range(_get_first_done_date(issue), start_date, end_date)
    ]
    sp_pass2 = _sum_story_points(filtered_pass2)

    return sp_pass1 + sp_pass2


def fetch_activity_type_sps(
    cloud_id: str,
    project_keys: list[str],
    jira_account_id: str,
    start_date: str,
    end_date: str,
    activity_type: str,
    email: str,
    token: str,
) -> int:
    """Fetch activity type story points for an engineer in a quarter.

    Uses fast query based on resolutiondate/updated fields. This is rarely used
    (mainly for testing individual activity types).

    Args:
        cloud_id: Jira cloud ID
        project_keys: List of project keys to search
        jira_account_id: Engineer's Jira account ID
        start_date: Quarter start date (YYYY-MM-DD)
        end_date: Quarter end date (YYYY-MM-DD)
        activity_type: Activity type to filter by
        email: Jira email for auth
        token: Jira API token

    Returns:
        Total story points for this activity type in this quarter
    """
    safe_id = _jql_escape(jira_account_id)
    safe_at = _jql_escape(activity_type)
    jql = (
        f"{_done_clause(start_date, end_date)}"
        f" AND issuetype in (Bug, Task, Story, Vulnerability)"
        f' AND (assignee = "{safe_id}" OR {QA_CONTACT_FIELD} = "{safe_id}")'
        f' AND "Activity Type" = "{safe_at}"'
        f" AND {_project_clause(project_keys)}"
    )
    issues = _jira_search(cloud_id, jql, ["summary", SP_FIELD], email, token)
    return _sum_story_points(issues)


def fetch_all_activity_type_sps(
    cloud_id: str,
    project_keys: list[str],
    jira_account_id: str,
    start_date: str,
    end_date: str,
    email: str,
    token: str,
    sprint_only: bool = False,
) -> tuple[dict[str, int], list[dict]]:
    """Fetch all activity type story points for an engineer in a quarter.

    Uses dual-pass approach:
    - Pass 1 (fast): Issues resolved in quarter via resolutiondate/updated
    - Pass 2 (targeted): Issues done in quarter but resolved later (uses changelog)

    Args:
        cloud_id: Jira cloud ID
        project_keys: List of project keys to search
        jira_account_id: Engineer's Jira account ID
        start_date: Quarter start date (YYYY-MM-DD)
        end_date: Quarter end date (YYYY-MM-DD)
        email: Jira email for auth
        token: Jira API token
        sprint_only: If True, only include issues in closed sprints

    Returns:
        Tuple of (dict mapping activity type name to story points,
                  list of issue detail dicts with keys: key, summary, sp, type,
                  activity_type, customer_cases)
    """
    safe_id = _jql_escape(jira_account_id)
    detail_fields = [
        "summary",
        SP_FIELD,
        ACTIVITY_TYPE_FIELD,
        "issuetype",
        "issuelinks",
    ]

    # Pass 1: Fast query (no changelog)
    jql1 = (
        f"{_done_clause(start_date, end_date)}"
        f" AND issuetype in (Bug, Task, Story, Vulnerability)"
        f' AND (assignee = "{safe_id}" OR {QA_CONTACT_FIELD} = "{safe_id}")'
        f' AND "Activity Type" is not EMPTY'
        f" AND {_project_clause(project_keys)}"
    )
    if sprint_only:
        jql1 += " AND sprint in closedSprints()"

    issues_pass1 = _jira_search(cloud_id, jql1, detail_fields, email, token)
    pass1_keys = {issue["key"] for issue in issues_pass1}

    by_type: dict[str, int] = {}
    issue_details: list[dict] = []

    def _process_issue(issue: dict) -> None:
        fields = issue.get("fields", {})
        at_field = fields.get(ACTIVITY_TYPE_FIELD)
        if not at_field or not isinstance(at_field, dict):
            return
        at_name = at_field.get("value", "")
        if not at_name:
            return
        sp = fields.get(SP_FIELD)
        points = int(sp) if sp and sp > 0 else DEFAULT_SP
        by_type[at_name] = by_type.get(at_name, 0) + points
        detail = {
            "key": issue["key"],
            "summary": fields.get("summary", ""),
            "sp": points,
            "type": (fields.get("issuetype") or {}).get("name", ""),
            "activity_type": at_name,
        }
        cases = _extract_customer_cases(issue)
        if cases:
            detail["customer_cases"] = cases
        issue_details.append(detail)

    for issue in issues_pass1:
        _process_issue(issue)

    # Pass 2: Edge cases (issues done in quarter but resolved later)
    buffer_end = (
        (datetime.fromisoformat(end_date) + timedelta(days=30)).date().isoformat()
    )
    statuses = ", ".join(f'"{s}"' for s in DONE_STATUSES)
    jql2 = (
        f"issuetype in (Bug, Task, Story, Vulnerability)"
        f' AND (status in ({statuses}) OR resolution in (Done, "Done-Errata"))'
        f' AND resolutiondate > "{end_date}"'
        f' AND updated >= "{start_date}" AND updated <= "{buffer_end}"'
        f' AND (assignee = "{safe_id}" OR {QA_CONTACT_FIELD} = "{safe_id}")'
        f' AND "Activity Type" is not EMPTY'
        f" AND {_project_clause(project_keys)}"
    )
    if sprint_only:
        jql2 += " AND sprint in closedSprints()"

    issues_pass2 = _jira_search_with_changelog(
        cloud_id,
        jql2,
        detail_fields + ["resolutiondate", "status", "updated"],
        email,
        token,
    )

    for issue in issues_pass2:
        if issue["key"] in pass1_keys:
            continue
        if not _is_date_in_range(_get_first_done_date(issue), start_date, end_date):
            continue
        _process_issue(issue)

    return by_type, issue_details


def _empty_phases() -> dict[str, list[float]]:
    return {"dev": [], "build": [], "qe": [], "total": []}


def fetch_cycle_times(
    cloud_id: str,
    project_keys: list[str],
    start_date: str,
    end_date: str,
    email: str,
    token: str,
    account_ids: list[str] | None = None,
) -> dict[str, dict[str, dict[str, list[float]]]]:
    """Fetch cycle time metrics for issues completed in a quarter.

    Uses dual-pass approach since changelog is always needed for cycle time phases.
    - Pass 1: Issues resolved in quarter (fast query, then fetch changelog)
    - Pass 2: Issues done in quarter but resolved later (changelog with filtering)

    Args:
        cloud_id: Jira cloud ID
        project_keys: List of project keys to search
        start_date: Quarter start date (YYYY-MM-DD)
        end_date: Quarter end date (YYYY-MM-DD)
        email: Jira email for auth
        token: Jira API token
        account_ids: Optional list of account IDs to filter by

    Returns:
        Nested dict: {project_key: {issue_type: {phase: [durations]}}}
    """
    # Pass 1: Fast query for issues resolved in quarter
    jql1 = (
        f"issuetype in (Story, Bug, Vulnerability) AND {_done_clause(start_date, end_date)}"
        f" AND {_project_clause(project_keys)}"
    )
    if account_ids:
        ids_clause = ", ".join(f'"{_jql_escape(aid)}"' for aid in account_ids)
        jql1 += (
            f" AND (assignee IN ({ids_clause}) OR {QA_CONTACT_FIELD} IN ({ids_clause}))"
        )

    issues_pass1 = _jira_search_with_changelog(
        cloud_id,
        jql1,
        ["summary", "project", "issuetype", "resolutiondate", "status", "updated"],
        email,
        token,
    )
    pass1_keys = {issue["key"] for issue in issues_pass1}

    # Pass 2: Edge cases (issues done in quarter but resolved later)
    buffer_end = (
        (datetime.fromisoformat(end_date) + timedelta(days=30)).date().isoformat()
    )
    statuses = ", ".join(f'"{s}"' for s in DONE_STATUSES)
    jql2 = (
        f"issuetype in (Story, Bug, Vulnerability)"
        f' AND (status in ({statuses}) OR resolution in (Done, "Done-Errata"))'
        f' AND resolutiondate > "{end_date}"'
        f' AND updated >= "{start_date}" AND updated <= "{buffer_end}"'
        f" AND {_project_clause(project_keys)}"
    )
    if account_ids:
        ids_clause = ", ".join(f'"{_jql_escape(aid)}"' for aid in account_ids)
        jql2 += (
            f" AND (assignee IN ({ids_clause}) OR {QA_CONTACT_FIELD} IN ({ids_clause}))"
        )

    issues_pass2 = _jira_search_with_changelog(
        cloud_id,
        jql2,
        ["summary", "project", "issuetype", "resolutiondate", "status", "updated"],
        email,
        token,
    )

    # Combine both passes
    all_issues = list(issues_pass1)
    for issue in issues_pass2:
        if issue["key"] not in pass1_keys:
            all_issues.append(issue)

    result: dict[str, dict[str, dict[str, list[float]]]] = {}
    for issue in all_issues:
        # Filter to quarter based on first done date
        if not _is_date_in_range(_get_first_done_date(issue), start_date, end_date):
            continue
        fields = issue.get("fields", {})
        project = fields.get("project", {})
        project_key = project.get("key")
        if not project_key:
            continue

        issue_type = fields.get("issuetype", {}).get("name")
        if not issue_type:
            continue

        resolution_date_str = fields.get("resolutiondate")
        if not resolution_date_str:
            continue

        changelog = issue.get("changelog", {})
        dev_start = _find_first_transition_to(changelog, DEV_START_STATUSES)
        dev_end = _find_first_transition_to(changelog, DEV_END_STATUSES)
        qe_start = _find_first_transition_to(changelog, QE_START_STATUSES)
        resolved = datetime.fromisoformat(resolution_date_str.replace("Z", "+00:00"))

        type_data = result.setdefault(project_key, {}).setdefault(
            issue_type, _empty_phases()
        )

        effective_dev_end_dt = (
            datetime.fromisoformat(dev_end.replace("Z", "+00:00"))
            if dev_end
            else resolved
        )
        if dev_start:
            d = _business_days(
                datetime.fromisoformat(dev_start.replace("Z", "+00:00")),
                effective_dev_end_dt,
            )
            if d > 0:
                type_data["dev"].append(d)

        if dev_end and qe_start:
            d = _business_days(
                datetime.fromisoformat(dev_end.replace("Z", "+00:00")),
                datetime.fromisoformat(qe_start.replace("Z", "+00:00")),
            )
            if d > 0:
                type_data["build"].append(d)

        if qe_start:
            d = _business_days(
                datetime.fromisoformat(qe_start.replace("Z", "+00:00")),
                resolved,
            )
            if d > 0:
                type_data["qe"].append(d)

        if dev_start:
            d = _business_days(
                datetime.fromisoformat(dev_start.replace("Z", "+00:00")),
                resolved,
            )
            if d > 0:
                type_data["total"].append(d)

    return result


def _fetch_quarter_jira(
    q: Quarter,
    cloud_id: str,
    project_keys: list[str],
    engineers_with_jira: list,
    email: str,
    token: str,
) -> tuple[
    str,
    int,
    dict[str, dict[str, int]],
    dict[str, dict[str, int]],
    dict,
    dict[str, list[dict]],
]:
    print(f"  Fetching Jira data for {q.label}...", file=sys.stderr)
    q_activities: dict[str, dict[str, int]] = {}
    q_sprint_activities: dict[str, dict[str, int]] = {}
    q_activity_issues: dict[str, list[dict]] = {}

    with ThreadPoolExecutor(max_workers=8) as pool:
        activity_futures = {}
        sprint_activity_futures = {}

        account_ids = [
            e.jira_account_id for e in engineers_with_jira if e.jira_account_id
        ]
        cycle_time_future = pool.submit(
            fetch_cycle_times,
            cloud_id,
            project_keys,
            q.start,
            q.end,
            email,
            token,
            account_ids=account_ids,
        )

        bug_future = pool.submit(
            fetch_verified_bugs,
            cloud_id,
            project_keys,
            q.start,
            q.end,
            email,
            token,
        )

        for eng in engineers_with_jira:
            activity_futures[
                pool.submit(
                    fetch_all_activity_type_sps,
                    cloud_id,
                    project_keys,
                    eng.jira_account_id,
                    q.start,
                    q.end,
                    email,
                    token,
                )
            ] = eng.name

            sprint_activity_futures[
                pool.submit(
                    fetch_all_activity_type_sps,
                    cloud_id,
                    project_keys,
                    eng.jira_account_id,
                    q.start,
                    q.end,
                    email,
                    token,
                    sprint_only=True,
                )
            ] = eng.name

        try:
            q_bugs = bug_future.result()
        except Exception as exc:
            print(f"[WARN] Bug fetch failed: {exc}", file=sys.stderr)
            q_bugs = 0

        for fut in as_completed(activity_futures):
            name = activity_futures[fut]
            try:
                eng_activities, eng_issues = fut.result()
            except Exception as exc:
                print(
                    f"[WARN] Activity fetch failed for {name}: {exc}", file=sys.stderr
                )
                eng_activities = {}
                eng_issues = []
            if eng_activities:
                q_activities[name] = eng_activities
            if eng_issues:
                q_activity_issues[name] = eng_issues

        for fut in as_completed(sprint_activity_futures):
            name = sprint_activity_futures[fut]
            try:
                eng_activities, _ = fut.result()
            except Exception as exc:
                print(
                    f"[WARN] Sprint activity fetch failed for {name}: {exc}",
                    file=sys.stderr,
                )
                eng_activities = {}
            if eng_activities:
                q_sprint_activities[name] = eng_activities

        try:
            q_cycle_times = cycle_time_future.result()
        except Exception as exc:
            print(f"[WARN] Cycle time fetch failed: {exc}", file=sys.stderr)
            q_cycle_times = {}

    return (
        q.label,
        q_bugs,
        q_activities,
        q_sprint_activities,
        q_cycle_times,
        q_activity_issues,
    )


def fetch_all_jira_data(
    config: TeamConfig,
    quarters: list[Quarter],
    email: str,
    token: str,
) -> JiraData:
    if not config.jira:
        return JiraData()

    cloud_id = config.jira.cloud_id
    project_keys = config.jira.project_keys
    bugs: dict[str, int] = {}
    activity_types: dict[str, dict[str, dict[str, int]]] = {}
    sprint_activity_types: dict[str, dict[str, dict[str, int]]] = {}
    cycle_times: dict[str, dict[str, dict[str, dict[str, list[float]]]]] = {}
    activity_issues: dict[str, dict[str, list[dict]]] = {}

    engineers_with_jira = [e for e in config.engineers if e.jira_account_id]

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [
            pool.submit(
                _fetch_quarter_jira,
                q,
                cloud_id,
                project_keys,
                engineers_with_jira,
                email,
                token,
            )
            for q in quarters
        ]
        for fut in as_completed(futures):
            (
                label,
                q_bugs,
                q_activities,
                q_sprint_activities,
                q_cycle_times,
                q_issues,
            ) = fut.result()
            bugs[label] = q_bugs
            if q_activities:
                activity_types[label] = q_activities
            if q_sprint_activities:
                sprint_activity_types[label] = q_sprint_activities
            if q_cycle_times:
                cycle_times[label] = q_cycle_times
            if q_issues:
                activity_issues[label] = q_issues

    return JiraData(
        bugs=bugs,
        activity_types=activity_types,
        sprint_activity_types=sprint_activity_types,
        cycle_times=cycle_times,
        activity_issues=activity_issues,
    )
