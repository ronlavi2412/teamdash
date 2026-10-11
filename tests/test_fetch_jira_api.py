from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

from teamdash.fetch_jira_api import (
    _business_days,
    _extract_customer_cases,
    _find_first_transition_to,
    _get_first_done_date,
    _is_date_in_range,
    _done_clause,
    DEV_START_STATUSES,
    DEV_END_STATUSES,
    QE_START_STATUSES,
    fetch_all_activity_type_sps,
    fetch_cycle_times,
    fetch_verified_bugs,
)


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
        assert (
            _find_first_transition_to(changelog, DEV_START_STATUSES)
            == "2025-01-06T10:00:00.000+0000"
        )

    def test_finds_dev_start_post(self):
        changelog = {
            "histories": [
                {
                    "created": "2025-01-06T10:00:00.000+0000",
                    "items": [{"field": "status", "toString": "POST"}],
                }
            ]
        }
        assert (
            _find_first_transition_to(changelog, DEV_START_STATUSES)
            == "2025-01-06T10:00:00.000+0000"
        )

    def test_finds_dev_end(self):
        changelog = {
            "histories": [
                {
                    "created": "2025-01-08T10:00:00.000+0000",
                    "items": [{"field": "status", "toString": "MODIFIED"}],
                }
            ]
        }
        assert (
            _find_first_transition_to(changelog, DEV_END_STATUSES)
            == "2025-01-08T10:00:00.000+0000"
        )

    def test_finds_qe_start(self):
        changelog = {
            "histories": [
                {
                    "created": "2025-01-10T10:00:00.000+0000",
                    "items": [{"field": "status", "toString": "ON_QA"}],
                }
            ]
        }
        assert (
            _find_first_transition_to(changelog, QE_START_STATUSES)
            == "2025-01-10T10:00:00.000+0000"
        )

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
        assert (
            _find_first_transition_to(changelog, DEV_START_STATUSES)
            == "2025-01-06T10:00:00.000+0000"
        )

    def test_case_insensitive(self):
        changelog = {
            "histories": [
                {
                    "created": "2025-01-06T10:00:00.000+0000",
                    "items": [{"field": "status", "toString": "ASSIGNED"}],
                }
            ]
        }
        assert (
            _find_first_transition_to(changelog, DEV_START_STATUSES)
            == "2025-01-06T10:00:00.000+0000"
        )

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
        assert (
            _find_first_transition_to(changelog, DEV_END_STATUSES)
            == "2025-01-06T10:00:00.000+0000"
        )


def _make_issue(
    project_key,
    changelog_transitions,
    issue_type="Story",
    resolution_date="2025-01-17T10:00:00.000+0000",
    key=None,
):
    histories = []
    for ts, status in changelog_transitions:
        histories.append(
            {
                "created": ts,
                "items": [{"field": "status", "toString": status}],
            }
        )
    # Auto-generate key if not provided
    if key is None:
        import random

        key = f"{project_key}-{random.randint(1, 9999)}"

    return {
        "key": key,
        "fields": {
            "project": {"key": project_key},
            "issuetype": {"name": issue_type},
            "resolutiondate": resolution_date,
        },
        "changelog": {"histories": histories},
    }


class TestFetchCycleTimes:
    def test_groups_by_project_and_type(self):
        issues = [
            _make_issue(
                "CNV",
                [
                    ("2025-01-06T10:00:00.000+0000", "In Progress"),
                    ("2025-01-10T10:00:00.000+0000", "MODIFIED"),
                    ("2025-01-13T10:00:00.000+0000", "ON_QA"),
                ],
                issue_type="Story",
            ),
            _make_issue(
                "CNV",
                [
                    ("2025-01-06T10:00:00.000+0000", "Assigned"),
                    ("2025-01-08T10:00:00.000+0000", "Dev Complete"),
                    ("2025-01-10T10:00:00.000+0000", "Testing"),
                ],
                issue_type="Bug",
            ),
        ]

        with patch(
            "teamdash.fetch_jira_api._jira_search_with_changelog", return_value=issues
        ):
            result = fetch_cycle_times(
                "test.atlassian.net",
                ["CNV"],
                "2025-01-01",
                "2025-03-31",
                "email",
                "token",
            )

        assert "CNV" in result
        assert "Story" in result["CNV"]
        assert "Bug" in result["CNV"]
        assert len(result["CNV"]["Story"]["dev"]) == 1
        assert len(result["CNV"]["Bug"]["dev"]) == 1

    def test_phase_calculation(self):
        issues = [
            _make_issue(
                "CNV",
                [
                    ("2025-01-06T10:00:00.000+0000", "In Progress"),
                    ("2025-01-10T10:00:00.000+0000", "MODIFIED"),
                    ("2025-01-13T10:00:00.000+0000", "ON_QA"),
                ],
                issue_type="Story",
                resolution_date="2025-01-17T10:00:00.000+0000",
            ),
        ]

        with patch(
            "teamdash.fetch_jira_api._jira_search_with_changelog", return_value=issues
        ):
            result = fetch_cycle_times(
                "test.atlassian.net",
                ["CNV"],
                "2025-01-01",
                "2025-03-31",
                "email",
                "token",
            )

        assert result["CNV"]["Story"]["dev"] == [4.0]
        assert result["CNV"]["Story"]["build"] == [1.0]
        assert result["CNV"]["Story"]["qe"] == [4.0]
        assert result["CNV"]["Story"]["total"] == [9.0]

    def test_missing_dev_end(self):
        issues = [
            _make_issue(
                "CNV",
                [
                    ("2025-01-06T10:00:00.000+0000", "In Progress"),
                    ("2025-01-13T10:00:00.000+0000", "ON_QA"),
                ],
                resolution_date="2025-01-17T10:00:00.000+0000",
            ),
        ]

        with patch(
            "teamdash.fetch_jira_api._jira_search_with_changelog", return_value=issues
        ):
            result = fetch_cycle_times(
                "test.atlassian.net",
                ["CNV"],
                "2025-01-01",
                "2025-03-31",
                "email",
                "token",
            )

        assert result["CNV"]["Story"]["dev"] == [9.0]
        assert result["CNV"]["Story"]["build"] == []
        assert result["CNV"]["Story"]["qe"] == [4.0]
        assert result["CNV"]["Story"]["total"] == [9.0]

    def test_missing_dev_end_no_qe(self):
        """MTA-style: In Progress → Done with no intermediate statuses."""
        issues = [
            _make_issue(
                "MTA",
                [
                    ("2025-01-06T10:00:00.000+0000", "In Progress"),
                ],
                resolution_date="2025-01-10T10:00:00.000+0000",
            ),
        ]

        with patch(
            "teamdash.fetch_jira_api._jira_search_with_changelog", return_value=issues
        ):
            result = fetch_cycle_times(
                "test.atlassian.net",
                ["MTA"],
                "2025-01-01",
                "2025-03-31",
                "email",
                "token",
            )

        assert result["MTA"]["Story"]["dev"] == [4.0]
        assert result["MTA"]["Story"]["build"] == []
        assert result["MTA"]["Story"]["qe"] == []
        assert result["MTA"]["Story"]["total"] == [4.0]

    def test_skips_no_dev_start(self):
        issues = [
            _make_issue(
                "CNV",
                [
                    ("2025-01-10T10:00:00.000+0000", "MODIFIED"),
                ],
                resolution_date="2025-01-17T10:00:00.000+0000",
            ),
        ]

        with patch(
            "teamdash.fetch_jira_api._jira_search_with_changelog", return_value=issues
        ):
            result = fetch_cycle_times(
                "test.atlassian.net",
                ["CNV"],
                "2025-01-01",
                "2025-03-31",
                "email",
                "token",
            )

        assert result["CNV"]["Story"]["total"] == []

    def test_empty_issues(self):
        with patch(
            "teamdash.fetch_jira_api._jira_search_with_changelog", return_value=[]
        ):
            result = fetch_cycle_times(
                "test.atlassian.net",
                ["CNV"],
                "2025-01-01",
                "2025-03-31",
                "email",
                "token",
            )

        assert result == {}

    def test_skips_no_project(self):
        issues = [
            {
                "key": "CNV-1",
                "fields": {
                    "project": {},
                    "issuetype": {"name": "Story"},
                    "resolutiondate": "2025-01-17T10:00:00.000+0000",
                },
                "changelog": {"histories": []},
            },
        ]

        with patch(
            "teamdash.fetch_jira_api._jira_search_with_changelog", return_value=issues
        ):
            result = fetch_cycle_times(
                "test.atlassian.net",
                ["CNV"],
                "2025-01-01",
                "2025-03-31",
                "email",
                "token",
            )

        assert result == {}

    def test_account_ids_filter_in_jql(self):
        with patch(
            "teamdash.fetch_jira_api._jira_search_with_changelog", return_value=[]
        ) as mock_search:
            fetch_cycle_times(
                "test.atlassian.net",
                ["CNV"],
                "2025-01-01",
                "2025-03-31",
                "email",
                "token",
                account_ids=["abc123", "def456"],
            )

        jql = mock_search.call_args[0][1]
        assert 'assignee IN ("abc123", "def456")' in jql
        assert 'cf[10470] IN ("abc123", "def456")' in jql

    def test_no_account_ids_no_filter(self):
        with patch(
            "teamdash.fetch_jira_api._jira_search_with_changelog", return_value=[]
        ) as mock_search:
            fetch_cycle_times(
                "test.atlassian.net",
                ["CNV"],
                "2025-01-01",
                "2025-03-31",
                "email",
                "token",
            )

        jql = mock_search.call_args[0][1]
        assert "assignee" not in jql


class TestGetFirstDoneDate:
    def test_from_changelog_verified(self):
        """Issue with changelog showing VERIFIED transition."""
        issue = {
            "fields": {"resolutiondate": "2025-04-01T10:00:00.000+0000"},
            "changelog": {
                "histories": [
                    {
                        "created": "2025-03-15T10:00:00.000+0000",
                        "items": [{"field": "status", "toString": "VERIFIED"}],
                    }
                ]
            },
        }
        # Should return March date from changelog, not April resolutiondate
        assert _get_first_done_date(issue) == "2025-03-15T10:00:00.000+0000"

    def test_from_changelog_closed(self):
        """Issue with changelog showing Closed transition."""
        issue = {
            "fields": {},
            "changelog": {
                "histories": [
                    {
                        "created": "2025-03-20T14:30:00.000+0000",
                        "items": [{"field": "status", "toString": "Closed"}],
                    }
                ]
            },
        }
        assert _get_first_done_date(issue) == "2025-03-20T14:30:00.000+0000"

    def test_from_changelog_release_pending(self):
        """Issue with changelog showing Release Pending transition."""
        issue = {
            "fields": {},
            "changelog": {
                "histories": [
                    {
                        "created": "2025-03-25T08:00:00.000+0000",
                        "items": [{"field": "status", "toString": "Release Pending"}],
                    }
                ]
            },
        }
        assert _get_first_done_date(issue) == "2025-03-25T08:00:00.000+0000"

    def test_uses_earliest_transition(self):
        """Issue with multiple transitions should use the earliest done transition."""
        issue = {
            "changelog": {
                "histories": [
                    {
                        "created": "2025-03-20T10:00:00.000+0000",
                        "items": [{"field": "status", "toString": "Closed"}],
                    },
                    {
                        "created": "2025-03-15T10:00:00.000+0000",
                        "items": [{"field": "status", "toString": "Verified"}],
                    },
                ]
            }
        }
        # Should return Verified date (earlier), not Closed
        assert _get_first_done_date(issue) == "2025-03-15T10:00:00.000+0000"

    def test_fallback_to_resolutiondate(self):
        """Issue with no changelog should use resolutiondate."""
        issue = {
            "fields": {"resolutiondate": "2025-03-15T10:00:00.000+0000"},
            "changelog": {"histories": []},
        }
        assert _get_first_done_date(issue) == "2025-03-15T10:00:00.000+0000"

    def test_fallback_to_resolutiondate_no_changelog(self):
        """Issue with no changelog key should use resolutiondate."""
        issue = {
            "fields": {"resolutiondate": "2025-03-15T10:00:00.000+0000"},
        }
        assert _get_first_done_date(issue) == "2025-03-15T10:00:00.000+0000"

    def test_fallback_to_updated_for_verified_status(self):
        """Issue in Verified status with no resolutiondate should use updated."""
        issue = {
            "fields": {
                "status": {"name": "Verified"},
                "updated": "2025-03-15T10:00:00.000+0000",
            },
            "changelog": {"histories": []},
        }
        assert _get_first_done_date(issue) == "2025-03-15T10:00:00.000+0000"

    def test_fallback_to_updated_for_closed_status(self):
        """Issue in Closed status with no resolutiondate should use updated."""
        issue = {
            "fields": {
                "status": {"name": "Closed"},
                "updated": "2025-03-20T10:00:00.000+0000",
            },
            "changelog": {"histories": []},
        }
        assert _get_first_done_date(issue) == "2025-03-20T10:00:00.000+0000"

    def test_not_done_returns_none(self):
        """Issue not in done status should return None."""
        issue = {
            "fields": {
                "status": {"name": "In Progress"},
            },
            "changelog": {"histories": []},
        }
        assert _get_first_done_date(issue) is None

    def test_no_changelog_no_fields_returns_none(self):
        """Issue with no useful data should return None."""
        issue = {}
        assert _get_first_done_date(issue) is None


class TestIsDateInRange:
    def test_date_within_range(self):
        """Date in the middle of range should return True."""
        assert (
            _is_date_in_range(
                "2025-03-15T10:00:00.000+0000", "2025-01-01", "2025-03-31"
            )
            is True
        )

    def test_date_at_start_boundary(self):
        """Date at start of range should return True."""
        assert (
            _is_date_in_range(
                "2025-01-01T00:00:00.000+0000", "2025-01-01", "2025-03-31"
            )
            is True
        )

    def test_date_at_end_boundary(self):
        """Date at end of range should return True."""
        assert (
            _is_date_in_range(
                "2025-03-31T23:59:59.000+0000", "2025-01-01", "2025-03-31"
            )
            is True
        )

    def test_date_before_range(self):
        """Date before range should return False."""
        assert (
            _is_date_in_range(
                "2024-12-31T10:00:00.000+0000", "2025-01-01", "2025-03-31"
            )
            is False
        )

    def test_date_after_range(self):
        """Date after range should return False."""
        assert (
            _is_date_in_range(
                "2025-04-01T00:00:00.000+0000", "2025-01-01", "2025-03-31"
            )
            is False
        )

    def test_none_date_returns_false(self):
        """None date should return False."""
        assert _is_date_in_range(None, "2025-01-01", "2025-03-31") is False

    def test_invalid_date_format_returns_false(self):
        """Invalid date format should return False."""
        assert _is_date_in_range("not-a-date", "2025-01-01", "2025-03-31") is False

    def test_z_timezone_format(self):
        """Date with Z timezone should work."""
        assert (
            _is_date_in_range("2025-03-15T10:00:00.000Z", "2025-01-01", "2025-03-31")
            is True
        )


class TestDoneClause:
    def test_generates_valid_jql(self):
        """Done clause should generate valid JQL for fast pass-1 query."""
        jql = _done_clause("2025-01-01", "2025-03-31")
        assert "status in" in jql
        assert "Verified" in jql
        assert "Closed" in jql
        assert "Release Pending" in jql
        assert "resolution in (Done, " in jql
        # Should use exact quarter dates (no buffer)
        assert "2025-01-01" in jql
        assert "2025-03-31" in jql

    def test_no_buffer(self):
        """Done clause should not use buffered dates (dual-pass approach)."""
        jql = _done_clause("2025-01-01", "2025-03-31")
        # Should NOT have dates outside the quarter
        assert "2024-" not in jql
        assert "2025-04-" not in jql


class TestFetchVerifiedBugsQuarterAttribution:
    def test_counts_by_first_done_date(self):
        """Issue verified in Q1 but closed in Q2 should count in Q1 (via pass2)."""
        # Pass 1 finds nothing (resolutiondate is in Q2)
        with patch("teamdash.fetch_jira_api._jira_search", return_value=[]):
            # Pass 2 finds the bug (verified in Q1, resolved in Q2)
            with patch(
                "teamdash.fetch_jira_api._jira_search_with_changelog",
                return_value=[
                    {
                        "key": "BUG-1",
                        "fields": {
                            "summary": "Bug 1",
                            "customfield_10028": 3,
                            "resolutiondate": "2025-04-15T10:00:00.000+0000",  # Q2
                            "status": {"name": "Closed"},
                            "updated": "2025-04-15T10:00:00.000+0000",
                        },
                        "changelog": {
                            "histories": [
                                {
                                    "created": "2025-03-20T10:00:00.000+0000",  # Q1
                                    "items": [
                                        {"field": "status", "toString": "Verified"}
                                    ],
                                }
                            ]
                        },
                    }
                ],
            ):
                # Fetch for Q1 (Jan-Mar)
                result = fetch_verified_bugs(
                    "test.atlassian.net",
                    ["PROJ"],
                    "2025-01-01",
                    "2025-03-31",
                    "email",
                    "token",
                )

                # Should count the bug (3 SP) - caught by pass2
                assert result == 3

    def test_excludes_wrong_quarter(self):
        """Issue verified in Q2 should not count in Q1."""
        # Pass 1 finds nothing
        with patch("teamdash.fetch_jira_api._jira_search", return_value=[]):
            # Pass 2 finds a bug verified in Q2 (should be filtered out)
            with patch(
                "teamdash.fetch_jira_api._jira_search_with_changelog",
                return_value=[
                    {
                        "key": "BUG-1",
                        "fields": {
                            "summary": "Bug 1",
                            "customfield_10028": 5,
                            "resolutiondate": "2025-04-15T10:00:00.000+0000",  # Q2
                            "status": {"name": "Closed"},
                            "updated": "2025-04-15T10:00:00.000+0000",
                        },
                        "changelog": {
                            "histories": [
                                {
                                    "created": "2025-04-10T10:00:00.000+0000",  # Q2
                                    "items": [
                                        {"field": "status", "toString": "Verified"}
                                    ],
                                }
                            ]
                        },
                    }
                ],
            ):
                # Fetch for Q1 (Jan-Mar)
                result = fetch_verified_bugs(
                    "test.atlassian.net",
                    ["PROJ"],
                    "2025-01-01",
                    "2025-03-31",
                    "email",
                    "token",
                )

                # Should NOT count the bug since it was verified in Q2
                assert result == 0


class TestExtractCustomerCases:
    def test_extracts_cipoe_links(self):
        issue = {
            "fields": {
                "issuelinks": [
                    {
                        "type": {"name": "Account"},
                        "outwardIssue": {
                            "key": "CIPOE-12345",
                            "fields": {"summary": "ACME Corp"},
                        },
                    }
                ]
            }
        }
        cases = _extract_customer_cases(issue)
        assert len(cases) == 1
        assert cases[0]["case_id"] == "CIPOE-12345"
        assert cases[0]["customer_name"] == "ACME Corp"

    def test_ignores_non_account_links(self):
        issue = {
            "fields": {
                "issuelinks": [
                    {
                        "type": {"name": "Blocks"},
                        "outwardIssue": {
                            "key": "CIPOE-99999",
                            "fields": {"summary": "X"},
                        },
                    }
                ]
            }
        }
        assert _extract_customer_cases(issue) == []

    def test_ignores_non_cipoe_keys(self):
        issue = {
            "fields": {
                "issuelinks": [
                    {
                        "type": {"name": "Account"},
                        "outwardIssue": {"key": "PROJ-100", "fields": {"summary": "X"}},
                    }
                ]
            }
        }
        assert _extract_customer_cases(issue) == []

    def test_ignores_inward_issues(self):
        issue = {
            "fields": {
                "issuelinks": [
                    {
                        "type": {"name": "Account"},
                        "inwardIssue": {"key": "CIPOE-111", "fields": {"summary": "X"}},
                    }
                ]
            }
        }
        assert _extract_customer_cases(issue) == []

    def test_empty_issuelinks(self):
        issue = {"fields": {"issuelinks": []}}
        assert _extract_customer_cases(issue) == []

    def test_no_issuelinks_field(self):
        issue = {"fields": {}}
        assert _extract_customer_cases(issue) == []

    def test_multiple_customer_cases(self):
        issue = {
            "fields": {
                "issuelinks": [
                    {
                        "type": {"name": "Account"},
                        "outwardIssue": {
                            "key": "CIPOE-100",
                            "fields": {"summary": "IBM"},
                        },
                    },
                    {
                        "type": {"name": "Account"},
                        "outwardIssue": {
                            "key": "CIPOE-200",
                            "fields": {"summary": "GE"},
                        },
                    },
                ]
            }
        }
        cases = _extract_customer_cases(issue)
        assert len(cases) == 2
        assert cases[0]["customer_name"] == "IBM"
        assert cases[1]["customer_name"] == "GE"


class TestFetchAllActivityTypeSps:
    def test_returns_tuple_with_issues(self):
        """Should return (by_type, issue_details) tuple."""
        issues = [
            {
                "key": "PROJ-1",
                "fields": {
                    "summary": "Fix login bug",
                    "customfield_10028": 3,
                    "customfield_10464": {"value": "Quality / Stability / Reliability"},
                    "issuetype": {"name": "Bug"},
                    "issuelinks": [],
                },
            },
            {
                "key": "PROJ-2",
                "fields": {
                    "summary": "Add feature",
                    "customfield_10028": 5,
                    "customfield_10464": {"value": "Product / Portfolio Work"},
                    "issuetype": {"name": "Story"},
                    "issuelinks": [],
                },
            },
        ]
        with patch("teamdash.fetch_jira_api._jira_search", return_value=issues):
            with patch(
                "teamdash.fetch_jira_api._jira_search_with_changelog",
                return_value=[],
            ):
                by_type, details = fetch_all_activity_type_sps(
                    "test.atlassian.net",
                    ["PROJ"],
                    "acc-123",
                    "2025-01-01",
                    "2025-03-31",
                    "email",
                    "token",
                )

        assert by_type == {
            "Quality / Stability / Reliability": 3,
            "Product / Portfolio Work": 5,
        }
        assert len(details) == 2
        assert details[0]["key"] == "PROJ-1"
        assert details[0]["summary"] == "Fix login bug"
        assert details[0]["sp"] == 3
        assert details[0]["type"] == "Bug"
        assert details[0]["activity_type"] == "Quality / Stability / Reliability"
        assert "customer_cases" not in details[0]

    def test_includes_customer_cases(self):
        """Issues with CIPOE links should have customer_cases."""
        issues = [
            {
                "key": "BUG-1",
                "fields": {
                    "summary": "Customer-facing bug",
                    "customfield_10028": 8,
                    "customfield_10464": {"value": "Incidents & Support"},
                    "issuetype": {"name": "Bug"},
                    "issuelinks": [
                        {
                            "type": {"name": "Account"},
                            "outwardIssue": {
                                "key": "CIPOE-999",
                                "fields": {"summary": "Paychex"},
                            },
                        }
                    ],
                },
            }
        ]
        with patch("teamdash.fetch_jira_api._jira_search", return_value=issues):
            with patch(
                "teamdash.fetch_jira_api._jira_search_with_changelog",
                return_value=[],
            ):
                _, details = fetch_all_activity_type_sps(
                    "test.atlassian.net",
                    ["PROJ"],
                    "acc-123",
                    "2025-01-01",
                    "2025-03-31",
                    "email",
                    "token",
                )

        assert len(details) == 1
        assert details[0]["customer_cases"] == [
            {"case_id": "CIPOE-999", "customer_name": "Paychex"}
        ]
