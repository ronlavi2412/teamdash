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

DEV_START_STATUSES = ["assigned", "in progress"]
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
    cloud_id: str, issue_key: str, email: str, token: str,
) -> dict:
    url = f"https://{cloud_id}/rest/api/3/issue/{issue_key}/changelog"
    histories: list[dict] = []
    start_at = 0

    while True:
        resp = requests.get(
            url, params={"startAt": start_at, "maxResults": MAX_RESULTS},
            auth=(email, token), timeout=30,
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
    changelog: dict, target_statuses: list[str],
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


def fetch_verified_bugs(
    cloud_id: str,
    project_keys: list[str],
    jira_account_id: str,
    start_date: str,
    end_date: str,
    email: str,
    token: str,
) -> int:
    safe_id = _jql_escape(jira_account_id)
    jql = (
        f'issuetype = Bug AND resolution in (Done, "Done-Errata")'
        f' AND resolutiondate >= "{start_date}" AND resolutiondate <= "{end_date}"'
        f' AND {QA_CONTACT_FIELD} = "{safe_id}"'
        f" AND {_project_clause(project_keys)}"
    )
    issues = _jira_search(cloud_id, jql, ["summary", SP_FIELD], email, token)
    return _sum_story_points(issues)


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
    safe_id = _jql_escape(jira_account_id)
    safe_at = _jql_escape(activity_type)
    jql = (
        f'resolution in (Done, "Done-Errata")'
        f" AND issuetype in (Bug, Task, Story, Vulnerability)"
        f' AND resolutiondate >= "{start_date}" AND resolutiondate <= "{end_date}"'
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
) -> dict[str, int]:
    safe_id = _jql_escape(jira_account_id)
    jql = (
        f'resolution in (Done, "Done-Errata")'
        f" AND issuetype in (Bug, Task, Story, Vulnerability)"
        f' AND resolutiondate >= "{start_date}" AND resolutiondate <= "{end_date}"'
        f' AND (assignee = "{safe_id}" OR {QA_CONTACT_FIELD} = "{safe_id}")'
        f' AND "Activity Type" is not EMPTY'
        f" AND {_project_clause(project_keys)}"
    )
    issues = _jira_search(cloud_id, jql, ["summary", SP_FIELD, ACTIVITY_TYPE_FIELD], email, token)
    by_type: dict[str, int] = {}
    for issue in issues:
        fields = issue.get("fields", {})
        at_field = fields.get(ACTIVITY_TYPE_FIELD)
        if not at_field or not isinstance(at_field, dict):
            continue
        at_name = at_field.get("value", "")
        if not at_name:
            continue
        sp = fields.get(SP_FIELD)
        points = int(sp) if sp and sp > 0 else DEFAULT_SP
        by_type[at_name] = by_type.get(at_name, 0) + points
    return by_type


def _empty_phases() -> dict[str, list[float]]:
    return {"dev": [], "build": [], "qe": [], "total": []}


def fetch_cycle_times(
    cloud_id: str,
    project_keys: list[str],
    start_date: str,
    end_date: str,
    email: str,
    token: str,
) -> dict[str, dict[str, dict[str, list[float]]]]:
    jql = (
        f'issuetype in (Story, Bug, Vulnerability) AND resolution in (Done, "Done-Errata")'
        f' AND resolutiondate >= "{start_date}" AND resolutiondate <= "{end_date}"'
        f" AND {_project_clause(project_keys)}"
    )
    issues = _jira_search_with_changelog(
        cloud_id, jql, ["summary", "project", "issuetype", "resolutiondate"], email, token,
    )

    result: dict[str, dict[str, dict[str, list[float]]]] = {}
    for issue in issues:
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

        type_data = result.setdefault(project_key, {}).setdefault(issue_type, _empty_phases())

        effective_dev_end_dt = (
            datetime.fromisoformat(dev_end.replace("Z", "+00:00")) if dev_end else resolved
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
) -> tuple[str, dict[str, int], dict[str, dict[str, int]], dict]:
    print(f"  Fetching Jira data for {q.label}...", file=sys.stderr)
    q_bugs: dict[str, int] = {}
    q_activities: dict[str, dict[str, int]] = {}

    with ThreadPoolExecutor(max_workers=8) as pool:
        bug_futures = {}
        activity_futures = {}

        cycle_time_future = pool.submit(
            fetch_cycle_times,
            cloud_id, project_keys, q.start, q.end, email, token,
        )

        for eng in engineers_with_jira:
            bug_futures[pool.submit(
                fetch_verified_bugs,
                cloud_id, project_keys, eng.jira_account_id,
                q.start, q.end, email, token,
            )] = eng.name

            activity_futures[pool.submit(
                fetch_all_activity_type_sps,
                cloud_id, project_keys, eng.jira_account_id,
                q.start, q.end, email, token,
            )] = eng.name

        for fut in as_completed(bug_futures):
            name = bug_futures[fut]
            try:
                q_bugs[name] = fut.result()
            except Exception as exc:
                print(f"[WARN] Bug fetch failed for {name}: {exc}", file=sys.stderr)
                q_bugs[name] = 0

        for fut in as_completed(activity_futures):
            name = activity_futures[fut]
            try:
                eng_activities = fut.result()
            except Exception as exc:
                print(f"[WARN] Activity fetch failed for {name}: {exc}", file=sys.stderr)
                eng_activities = {}
            if eng_activities:
                q_activities[name] = eng_activities

        try:
            q_cycle_times = cycle_time_future.result()
        except Exception as exc:
            print(f"[WARN] Cycle time fetch failed: {exc}", file=sys.stderr)
            q_cycle_times = {}

    return q.label, q_bugs, q_activities, q_cycle_times


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
    bugs: dict[str, dict[str, int]] = {}
    activity_types: dict[str, dict[str, dict[str, int]]] = {}
    cycle_times: dict[str, dict[str, dict[str, dict[str, list[float]]]]] = {}

    engineers_with_jira = [
        e for e in config.engineers if e.jira_account_id
    ]

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [
            pool.submit(
                _fetch_quarter_jira, q, cloud_id, project_keys,
                engineers_with_jira, email, token,
            )
            for q in quarters
        ]
        for fut in as_completed(futures):
            label, q_bugs, q_activities, q_cycle_times = fut.result()
            bugs[label] = q_bugs
            if q_activities:
                activity_types[label] = q_activities
            if q_cycle_times:
                cycle_times[label] = q_cycle_times

    return JiraData(bugs=bugs, activity_types=activity_types, cycle_times=cycle_times)
