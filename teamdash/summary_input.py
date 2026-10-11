"""Prepare a small, representative input for AI-written dashboard summaries."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys


CURRENT_FIELDS = (
    "gh_prs",
    "gl_mrs",
    "reviews",
    "cp",
    "review_cp",
    "merge_time",
    "size_dist",
    "xl_count",
    "pto_days",
)
PREVIOUS_FIELDS = ("gh_prs", "gl_mrs", "reviews", "cp", "review_cp", "merge_time")
SIZE_ORDER = {"XL": 0, "L": 1, "M": 2, "S": 3, "XS": 4}
MAX_TITLES = 12
MAX_TITLE_LENGTH = 120
MAX_JIRA_ISSUES = 15
MAX_JIRA_PER_TYPE = 3


def _metrics(quarter: dict, index: int, fields: tuple[str, ...]) -> dict:
    return {
        field: quarter[field][index]
        for field in fields
        if field in quarter and index < len(quarter[field])
    }


def _notable_prs(prs: list[dict]) -> tuple[dict[str, int], list[dict]]:
    counts = Counter(pr.get("repo") or "unknown" for pr in prs)
    repos = sorted(counts, key=lambda repo: (-counts[repo], repo))
    candidates = [
        (index, pr) for index, pr in enumerate(prs) if pr.get("title", "").strip()
    ]

    def rank(item: tuple[int, dict]) -> tuple[int, int]:
        index, pr = item
        return SIZE_ORDER.get(pr.get("size"), 5), index

    selected: list[tuple[int, dict]] = []
    for repo in repos[:3]:
        matches = [
            item for item in candidates if (item[1].get("repo") or "unknown") == repo
        ]
        if matches:
            selected.append(min(matches, key=rank))

    selected_indexes = {index for index, _ in selected}
    for item in sorted(candidates, key=rank):
        if len(selected) >= MAX_TITLES:
            break
        if item[0] not in selected_indexes:
            selected.append(item)
            selected_indexes.add(item[0])

    titles = [
        {
            "repo": pr.get("repo") or "unknown",
            "size": pr.get("size", ""),
            "source": pr.get("source", ""),
            "title": pr["title"].strip()[:MAX_TITLE_LENGTH],
        }
        for _, pr in selected
    ]
    return {repo: counts[repo] for repo in repos}, titles


def _short_to_full_label(short: str) -> str:
    parts = short.split("'")
    if len(parts) == 2:
        return f"20{parts[1]}-{parts[0]}"
    return short


def _notable_jira_issues(issues: list[dict]) -> list[dict]:
    if not issues:
        return []
    customer_issues = [i for i in issues if i.get("customer_cases")]
    other_issues = [i for i in issues if not i.get("customer_cases")]

    by_type: dict[str, list[dict]] = {}
    for issue in other_issues:
        at = issue.get("activity_type", "")
        by_type.setdefault(at, []).append(issue)

    selected_keys: set[str] = set()
    selected: list[dict] = []
    for ci in customer_issues:
        if len(selected) >= MAX_JIRA_ISSUES:
            break
        selected.append(ci)
        selected_keys.add(ci["key"])

    for at_name in sorted(by_type, key=lambda t: -sum(i["sp"] for i in by_type[t])):
        type_issues = sorted(by_type[at_name], key=lambda i: -i["sp"])
        added = 0
        for issue in type_issues:
            if len(selected) >= MAX_JIRA_ISSUES:
                break
            if issue["key"] not in selected_keys:
                selected.append(issue)
                selected_keys.add(issue["key"])
                added += 1
                if added >= MAX_JIRA_PER_TYPE:
                    break

    return selected


def extract_summary_input(data: dict) -> dict:
    """Keep only the latest quarter and the comparison data needed for summaries."""
    labels = data["quarterLabels"]
    quarters = data["quarters"]
    if not labels or not quarters:
        raise ValueError("Dashboard data has no quarters")

    current = quarters[-1]
    previous = quarters[-2] if len(quarters) > 1 else None
    label = labels[-1]
    previous_label = labels[-2] if previous is not None else None
    details = data.get("pr_details", {}).get(label, {})
    jira_raw = data.get("jiraData", {})
    full_label = _short_to_full_label(label)
    jira_issues_by_eng = jira_raw.get("activity_issues", {}).get(full_label, {})
    engineers = []

    for index, name in enumerate(data["names"]):
        metrics = _metrics(current, index, CURRENT_FIELDS)
        activity_list = current.get("activity_types", [])
        activity = activity_list[index] if index < len(activity_list) else {}
        activity = {key: value for key, value in activity.items() if value}
        prs = details.get(name, [])
        eng_jira = jira_issues_by_eng.get(name, [])
        if not (
            any(metrics.get(field, 0) for field in PREVIOUS_FIELDS) or activity or prs
        ):
            continue

        repo_counts, notable = _notable_prs(prs)
        engineer = {"name": name, "current": metrics}
        if activity:
            engineer["current"]["activity_types"] = activity
        if previous is not None:
            engineer["previous"] = _metrics(previous, index, PREVIOUS_FIELDS)
        if repo_counts:
            engineer["repo_counts"] = repo_counts
        if notable:
            engineer["notable_prs"] = notable
        jira_notable = _notable_jira_issues(eng_jira)
        if jira_notable:
            engineer["jira_issues"] = jira_notable
        engineers.append(engineer)

    result: dict = {"quarter": label, "engineers": engineers}
    if previous_label is not None:
        result["previous_quarter"] = previous_label
    verified_bugs = current.get("verified_bugs", 0)
    if verified_bugs:
        result["verified_bugs"] = verified_bugs
    return result


def clear_summaries(path: Path) -> bool:
    """Remove stored narratives so a skipped run cannot show old summaries."""
    with path.open() as source:
        data = json.load(source)
    if "summaries" not in data:
        return False
    del data["summaries"]
    with path.open("w") as output:
        json.dump(data, output, indent=2)
        output.write("\n")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    extract = commands.add_parser("extract", help="Write compact summary input")
    extract.add_argument("data", type=Path)
    extract.add_argument("-o", "--output", type=Path, required=True)
    clear = commands.add_parser("clear", help="Remove existing summaries")
    clear.add_argument("data", type=Path)
    args = parser.parse_args()

    if args.command == "clear":
        changed = clear_summaries(args.data)
        print(
            "Stored summaries removed" if changed else "No stored summaries",
            file=sys.stderr,
        )
        return

    with args.data.open() as source:
        data = json.load(source)
    compact = json.dumps(
        extract_summary_input(data), ensure_ascii=False, separators=(",", ":")
    )
    args.output.write_text(compact + "\n")
    print(
        f"Summary input written to {args.output} ({len(compact)} characters)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
