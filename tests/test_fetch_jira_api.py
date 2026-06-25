from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

from teamdash.fetch_jira_api import _business_days, _find_first_transition_to, DEV_START_STATUSES, DEV_END_STATUSES, QE_START_STATUSES, fetch_cycle_times


class TestBusinessDays:
    def test_same_day(self):
        start = datetime(2025, 1, 6, 9, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 6, 17, 0, tzinfo=timezone.utc)
        assert _business_days(start, end) == 0.0

    def test_mon_to_fri(self):
        start = datetime(2025, 1, 6, 9, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 10, 17, 0, tzinfo=timezone.utc)
        assert _business_days(start, end) == 4.0

    def test_fri_to_mon(self):
        start = datetime(2025, 1, 10, 9, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 13, 9, 0, tzinfo=timezone.utc)
        assert _business_days(start, end) == 1.0

    def test_two_week_span(self):
        start = datetime(2025, 1, 6, 9, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 17, 17, 0, tzinfo=timezone.utc)
        assert _business_days(start, end) == 9.0

    def test_start_on_saturday(self):
        start = datetime(2025, 1, 11, 9, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 13, 9, 0, tzinfo=timezone.utc)
        assert _business_days(start, end) == 1.0

    def test_end_before_start(self):
        start = datetime(2025, 1, 10, 9, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 6, 9, 0, tzinfo=timezone.utc)
        assert _business_days(start, end) == 0.0

    def test_equal_times(self):
        t = datetime(2025, 1, 6, 9, 0, tzinfo=timezone.utc)
        assert _business_days(t, t) == 0.0


class TestFindFirstTransitionTo:
    def test_finds_dev_start(self):
        changelog = {
            "histories": [
                {
                    "created": "2025-01-06T10:00:00.000+0000",
                    "items": [{"field": "status", "toString": "In Progress"}],
                }
            ]
        }
        assert _find_first_transition_to(changelog, DEV_START_STATUSES) == "2025-01-06T10:00:00.000+0000"

    def test_finds_dev_end(self):
        changelog = {
            "histories": [
                {
                    "created": "2025-01-08T10:00:00.000+0000",
                    "items": [{"field": "status", "toString": "MODIFIED"}],
                }
            ]
        }
        assert _find_first_transition_to(changelog, DEV_END_STATUSES) == "2025-01-08T10:00:00.000+0000"

    def test_finds_qe_start(self):
        changelog = {
            "histories": [
                {
                    "created": "2025-01-10T10:00:00.000+0000",
                    "items": [{"field": "status", "toString": "ON_QA"}],
                }
            ]
        }
        assert _find_first_transition_to(changelog, QE_START_STATUSES) == "2025-01-10T10:00:00.000+0000"

    def test_no_match(self):
        changelog = {
            "histories": [
                {
                    "created": "2025-01-06T10:00:00.000+0000",
                    "items": [{"field": "status", "toString": "To Do"}],
                }
            ]
        }
        assert _find_first_transition_to(changelog, DEV_START_STATUSES) is None

    def test_uses_first_match(self):
        changelog = {
            "histories": [
                {
                    "created": "2025-01-10T10:00:00.000+0000",
                    "items": [{"field": "status", "toString": "In Progress"}],
                },
                {
                    "created": "2025-01-06T10:00:00.000+0000",
                    "items": [{"field": "status", "toString": "Assigned"}],
                },
            ]
        }
        assert _find_first_transition_to(changelog, DEV_START_STATUSES) == "2025-01-06T10:00:00.000+0000"

    def test_case_insensitive(self):
        changelog = {
            "histories": [
                {
                    "created": "2025-01-06T10:00:00.000+0000",
                    "items": [{"field": "status", "toString": "ASSIGNED"}],
                }
            ]
        }
        assert _find_first_transition_to(changelog, DEV_START_STATUSES) == "2025-01-06T10:00:00.000+0000"

    def test_empty_changelog(self):
        assert _find_first_transition_to({}, DEV_START_STATUSES) is None
        assert _find_first_transition_to({"histories": []}, DEV_START_STATUSES) is None

    def test_non_status_fields_ignored(self):
        changelog = {
            "histories": [
                {
                    "created": "2025-01-06T10:00:00.000+0000",
                    "items": [
                        {"field": "assignee", "toString": "In Progress"},
                        {"field": "status", "toString": "Dev Complete"},
                    ],
                }
            ]
        }
        assert _find_first_transition_to(changelog, DEV_END_STATUSES) == "2025-01-06T10:00:00.000+0000"


def _make_issue(project_key, changelog_transitions, resolution_date="2025-01-17T10:00:00.000+0000"):
    histories = []
    for ts, status in changelog_transitions:
        histories.append({
            "created": ts,
            "items": [{"field": "status", "toString": status}],
        })
    return {
        "fields": {
            "project": {"key": project_key},
            "resolutiondate": resolution_date,
        },
        "changelog": {"histories": histories},
    }


class TestFetchCycleTimes:
    def test_groups_by_project(self):
        issues = [
            _make_issue("CNV", [
                ("2025-01-06T10:00:00.000+0000", "In Progress"),
                ("2025-01-10T10:00:00.000+0000", "MODIFIED"),
                ("2025-01-13T10:00:00.000+0000", "ON_QA"),
            ]),
            _make_issue("MTV", [
                ("2025-01-06T10:00:00.000+0000", "Assigned"),
                ("2025-01-08T10:00:00.000+0000", "Dev Complete"),
                ("2025-01-10T10:00:00.000+0000", "Testing"),
            ]),
        ]

        with patch("teamdash.fetch_jira_api._jira_search_with_changelog", return_value=issues):
            result = fetch_cycle_times(
                "test.atlassian.net", ["CNV", "MTV"], "2025-01-01", "2025-03-31",
                "email", "token",
            )

        assert "CNV" in result
        assert "MTV" in result
        assert len(result["CNV"]["dev"]) == 1
        assert len(result["CNV"]["build"]) == 1
        assert len(result["CNV"]["qe"]) == 1
        assert len(result["CNV"]["total"]) == 1

    def test_phase_calculation(self):
        issues = [
            _make_issue("CNV", [
                ("2025-01-06T10:00:00.000+0000", "In Progress"),
                ("2025-01-10T10:00:00.000+0000", "MODIFIED"),
                ("2025-01-13T10:00:00.000+0000", "ON_QA"),
            ], resolution_date="2025-01-17T10:00:00.000+0000"),
        ]

        with patch("teamdash.fetch_jira_api._jira_search_with_changelog", return_value=issues):
            result = fetch_cycle_times(
                "test.atlassian.net", ["CNV"], "2025-01-01", "2025-03-31",
                "email", "token",
            )

        assert result["CNV"]["dev"] == [4.0]
        assert result["CNV"]["build"] == [1.0]
        assert result["CNV"]["qe"] == [4.0]
        assert result["CNV"]["total"] == [9.0]

    def test_missing_dev_end(self):
        issues = [
            _make_issue("CNV", [
                ("2025-01-06T10:00:00.000+0000", "In Progress"),
                ("2025-01-13T10:00:00.000+0000", "ON_QA"),
            ], resolution_date="2025-01-17T10:00:00.000+0000"),
        ]

        with patch("teamdash.fetch_jira_api._jira_search_with_changelog", return_value=issues):
            result = fetch_cycle_times(
                "test.atlassian.net", ["CNV"], "2025-01-01", "2025-03-31",
                "email", "token",
            )

        assert result["CNV"]["dev"] == []
        assert result["CNV"]["build"] == []
        assert result["CNV"]["qe"] == [4.0]
        assert result["CNV"]["total"] == [9.0]

    def test_skips_no_dev_start(self):
        issues = [
            _make_issue("CNV", [
                ("2025-01-10T10:00:00.000+0000", "MODIFIED"),
            ], resolution_date="2025-01-17T10:00:00.000+0000"),
        ]

        with patch("teamdash.fetch_jira_api._jira_search_with_changelog", return_value=issues):
            result = fetch_cycle_times(
                "test.atlassian.net", ["CNV"], "2025-01-01", "2025-03-31",
                "email", "token",
            )

        assert result["CNV"]["total"] == []

    def test_empty_issues(self):
        with patch("teamdash.fetch_jira_api._jira_search_with_changelog", return_value=[]):
            result = fetch_cycle_times(
                "test.atlassian.net", ["CNV"], "2025-01-01", "2025-03-31",
                "email", "token",
            )

        assert result == {}

    def test_skips_no_project(self):
        issues = [
            {
                "fields": {
                    "project": {},
                    "resolutiondate": "2025-01-17T10:00:00.000+0000",
                },
                "changelog": {"histories": []},
            },
        ]

        with patch("teamdash.fetch_jira_api._jira_search_with_changelog", return_value=issues):
            result = fetch_cycle_times(
                "test.atlassian.net", ["CNV"], "2025-01-01", "2025-03-31",
                "email", "token",
            )

        assert result == {}
