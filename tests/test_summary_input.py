from __future__ import annotations

import json

from teamdash.summary_input import (
    _notable_jira_issues,
    _short_to_full_label,
    clear_summaries,
    extract_summary_input,
)


def _quarter(prs: list[int], reviews: list[int]) -> dict:
    return {
        "gh_prs": prs,
        "gl_mrs": [0] * len(prs),
        "reviews": reviews,
        "cp": [13 if count else 0 for count in prs],
        "review_cp": [5 if count else 0 for count in reviews],
        "merge_time": [2.5 if count else 0 for count in prs],
        "size_dist": [{"L": count} for count in prs],
        "xl_count": [1 if count else 0 for count in prs],
        "pto_days": [0] * len(prs),
        "activity_types": [{} for _ in prs],
        "verified_bugs": 7,
    }


def test_extracts_only_latest_active_engineers_and_comparison_metrics():
    data = {
        "names": ["Alice", "Bob", "Carol"],
        "quarterLabels": ["Q1'26", "Q2'26"],
        "quarters": [
            _quarter([2, 1, 1], [0, 0, 0]),
            _quarter([3, 0, 0], [2, 0, 0]),
        ],
        "pr_details": {
            "Q1'26": {"Carol": [{"title": "Old work"}]},
            "Q2'26": {"Alice": [{"title": "New work", "repo": "api", "size": "L"}]},
        },
    }
    data["quarters"][-1]["activity_types"][1] = {"Support": 2, "Other": 0}

    result = extract_summary_input(data)

    assert result["quarter"] == "Q2'26"
    assert result["previous_quarter"] == "Q1'26"
    assert [engineer["name"] for engineer in result["engineers"]] == ["Alice", "Bob"]
    alice, bob = result["engineers"]
    assert alice["previous"]["gh_prs"] == 2
    assert alice["current"]["merge_time"] == 2.5
    assert alice["notable_prs"][0]["title"] == "New work"
    assert bob["current"]["activity_types"] == {"Support": 2}
    assert result["verified_bugs"] == 7
    assert "Old work" not in json.dumps(result)


def test_representative_titles_cover_repos_and_have_a_limit():
    prs = [
        {"title": f"Small change {i}", "repo": "api", "size": "S", "source": "github"}
        for i in range(10)
    ]
    prs += [
        {"title": "Important UI change", "repo": "ui", "size": "XL", "source": "gitlab"},
        {"title": "Important docs change", "repo": "docs", "size": "L", "source": "github"},
        {"title": "Long " + "x" * 200, "repo": "api", "size": "XL", "source": "github"},
    ]
    data = {
        "names": ["Alice"],
        "quarterLabels": ["Q2'26"],
        "quarters": [_quarter([13], [0])],
        "pr_details": {"Q2'26": {"Alice": prs}},
    }

    alice = extract_summary_input(data)["engineers"][0]
    titles = alice["notable_prs"]

    assert alice["repo_counts"] == {"api": 11, "docs": 1, "ui": 1}
    assert len(titles) == 12
    assert {pr["repo"] for pr in titles} == {"api", "ui", "docs"}
    assert any(pr["title"] == "Important UI change" for pr in titles)
    assert all(len(pr["title"]) <= 120 for pr in titles)


def test_missing_pr_details_and_previous_quarter_are_allowed():
    data = {
        "names": ["Alice"],
        "quarterLabels": ["Q2'26"],
        "quarters": [_quarter([0], [1])],
    }

    result = extract_summary_input(data)

    assert result["engineers"] == [{"name": "Alice", "current": {
        "gh_prs": 0, "gl_mrs": 0, "reviews": 1, "cp": 0, "review_cp": 5,
        "merge_time": 0, "size_dist": {"L": 0}, "xl_count": 0, "pto_days": 0,
    }}]
    assert "previous_quarter" not in result


def test_short_to_full_label():
    assert _short_to_full_label("Q3'26") == "2026-Q3"
    assert _short_to_full_label("Q1'25") == "2025-Q1"
    assert _short_to_full_label("plain") == "plain"


def test_notable_jira_issues_prioritizes_customer_cases():
    issues = [
        {"key": "BUG-1", "summary": "Regular bug", "sp": 5, "type": "Bug",
         "activity_type": "Quality / Stability / Reliability"},
        {"key": "BUG-2", "summary": "Customer bug", "sp": 2, "type": "Bug",
         "activity_type": "Incidents & Support",
         "customer_cases": [{"case_id": "CIPOE-1", "customer_name": "IBM"}]},
    ]
    result = _notable_jira_issues(issues)
    assert result[0]["key"] == "BUG-2"


def test_notable_jira_issues_limits_per_type():
    issues = [
        {"key": f"Q-{i}", "summary": f"Quality issue {i}", "sp": 10 - i,
         "type": "Bug", "activity_type": "Quality / Stability / Reliability"}
        for i in range(5)
    ]
    result = _notable_jira_issues(issues)
    assert len(result) == 3


def test_notable_jira_issues_caps_total():
    issues = [
        {"key": f"I-{i}", "summary": f"Issue {i}", "sp": 2,
         "type": "Task", "activity_type": f"Type {i % 6}"}
        for i in range(30)
    ]
    result = _notable_jira_issues(issues)
    assert len(result) <= 15


def test_extracts_jira_issues_from_jiraData():
    data = {
        "names": ["Alice"],
        "quarterLabels": ["Q2'26"],
        "quarters": [_quarter([3], [2])],
        "pr_details": {"Q2'26": {"Alice": [{"title": "PR", "repo": "api", "size": "S"}]}},
        "jiraData": {
            "activity_issues": {
                "2026-Q2": {
                    "Alice": [
                        {"key": "PROJ-1", "summary": "Fix bug", "sp": 3,
                         "type": "Bug", "activity_type": "Quality / Stability / Reliability"},
                    ]
                }
            }
        },
    }
    result = extract_summary_input(data)
    alice = result["engineers"][0]
    assert "jira_issues" in alice
    assert alice["jira_issues"][0]["key"] == "PROJ-1"


def test_clear_summaries_preserves_other_data(tmp_path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps({"names": ["Alice"], "summaries": {"Q2'26": {"Alice": "old"}}}))

    assert clear_summaries(path) is True
    assert json.loads(path.read_text()) == {"names": ["Alice"]}
    assert clear_summaries(path) is False
