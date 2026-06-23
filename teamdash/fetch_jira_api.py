from __future__ import annotations

import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

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
QA_CONTACT_FIELD = "cf[10470]"
MAX_RESULTS = 100


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
                f"[WARN] Jira search failed ({resp.status_code}): {resp.text[:200]}",
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


def _sum_story_points(issues: list[dict]) -> int:
    total = 0
    for issue in issues:
        sp = issue.get("fields", {}).get(SP_FIELD)
        total += int(sp) if sp and sp > 0 else DEFAULT_SP
    return total


def _project_clause(project_keys: list[str]) -> str:
    return "project in (" + ", ".join(project_keys) + ")"


def fetch_verified_bugs(
    cloud_id: str,
    project_keys: list[str],
    jira_account_id: str,
    start_date: str,
    end_date: str,
    email: str,
    token: str,
) -> int:
    jql = (
        f'issuetype = Bug AND resolution in (Done, "Done-Errata")'
        f' AND resolutiondate >= "{start_date}" AND resolutiondate <= "{end_date}"'
        f' AND {QA_CONTACT_FIELD} = "{jira_account_id}"'
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
    jql = (
        f'resolution in (Done, "Done-Errata")'
        f" AND issuetype in (Bug, Task, Story, Vulnerability)"
        f' AND resolutiondate >= "{start_date}" AND resolutiondate <= "{end_date}"'
        f' AND (assignee = "{jira_account_id}" OR {QA_CONTACT_FIELD} = "{jira_account_id}")'
        f' AND "Activity Type" = "{activity_type}"'
        f" AND {_project_clause(project_keys)}"
    )
    issues = _jira_search(cloud_id, jql, ["summary", SP_FIELD], email, token)
    return _sum_story_points(issues)


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

    engineers_with_jira = [
        e for e in config.engineers if e.jira_account_id
    ]

    for q in quarters:
        print(f"  Fetching Jira data for {q.label}...", file=sys.stderr)
        q_bugs: dict[str, int] = {}
        q_activities: dict[str, dict[str, int]] = {}

        with ThreadPoolExecutor(max_workers=4) as pool:
            bug_futures = {}
            activity_futures = {}

            for eng in engineers_with_jira:
                bug_futures[pool.submit(
                    fetch_verified_bugs,
                    cloud_id, project_keys, eng.jira_account_id,
                    q.start, q.end, email, token,
                )] = eng.name

                for at in ACTIVITY_TYPES:
                    activity_futures[pool.submit(
                        fetch_activity_type_sps,
                        cloud_id, project_keys, eng.jira_account_id,
                        q.start, q.end, at, email, token,
                    )] = (eng.name, at)

            for fut in as_completed(bug_futures):
                name = bug_futures[fut]
                try:
                    q_bugs[name] = fut.result()
                except Exception as exc:
                    print(f"[WARN] Bug fetch failed for {name}: {exc}", file=sys.stderr)
                    q_bugs[name] = 0

            for fut in as_completed(activity_futures):
                name, at = activity_futures[fut]
                try:
                    sp = fut.result()
                except Exception as exc:
                    print(f"[WARN] Activity fetch failed for {name}/{at}: {exc}", file=sys.stderr)
                    sp = 0
                if sp > 0:
                    q_activities.setdefault(name, {})[at] = sp

        bugs[q.label] = q_bugs
        if q_activities:
            activity_types[q.label] = q_activities

    return JiraData(bugs=bugs, activity_types=activity_types)
