from __future__ import annotations

import json
import os

from teamdash.config import EngineerConfig, TeamConfig
from teamdash.models import EngineerQuarterMetrics, QuarterSummary
from teamdash.dashboard import (
    _build_dashboard_data,
    _build_config_data,
    _build_table_row_data,
    _delta_class,
    _pct,
    generate_dashboard,
)


class TestPct:
    def test_increase(self):
        assert _pct(120, 100) == "+20%"

    def test_decrease(self):
        assert _pct(80, 100) == "-20%"

    def test_no_change(self):
        assert _pct(100, 100) == "+0%"

    def test_old_zero_new_positive(self):
        assert _pct(5, 0) == "+999%"

    def test_old_zero_new_zero(self):
        assert _pct(0, 0) == "0%"

    def test_rounding(self):
        assert _pct(101, 100) == "+1%"


class TestDeltaClass:
    def test_up(self):
        assert _delta_class(110, 100) == "up"

    def test_down(self):
        assert _delta_class(90, 100) == "down"

    def test_flat_within_threshold(self):
        assert _delta_class(100, 100) == "flat"

    def test_flat_just_above_threshold(self):
        assert _delta_class(101, 100) == "flat"

    def test_old_zero_new_positive(self):
        assert _delta_class(5, 0) == "up"

    def test_old_zero_new_zero(self):
        assert _delta_class(0, 0) == "flat"

    def test_lower_is_better_inverts(self):
        assert _delta_class(110, 100, lower_is_better=True) == "down"
        assert _delta_class(90, 100, lower_is_better=True) == "up"


class TestBuildDashboardData:
    def test_contains_names(self, two_quarter_summaries, sample_config):
        data = _build_dashboard_data(sample_config, two_quarter_summaries)
        assert data["names"] == ["Alice", "Bob"]

    def test_contains_quarter_labels(self, two_quarter_summaries, sample_config):
        data = _build_dashboard_data(sample_config, two_quarter_summaries)
        assert data["quarterLabels"] == ["Q4'24", "Q1'25"]

    def test_contains_quarters_data(self, two_quarter_summaries, sample_config):
        data = _build_dashboard_data(sample_config, two_quarter_summaries)
        assert len(data["quarters"]) == 2
        q = data["quarters"][0]
        assert "gh_prs" in q
        assert "gl_mrs" in q
        assert "reviews" in q
        assert "merge_time" in q

    def test_has_scoring_false_without_scoring(self, two_quarter_summaries, sample_config):
        data = _build_dashboard_data(sample_config, two_quarter_summaries)
        assert data["hasScoring"] is False

    def test_has_scoring_true_with_scoring(self, two_quarter_summaries_with_scoring, sample_config):
        data = _build_dashboard_data(sample_config, two_quarter_summaries_with_scoring)
        assert data["hasScoring"] is True

    def test_colors_match_engineers(self, two_quarter_summaries, sample_config):
        data = _build_dashboard_data(sample_config, two_quarter_summaries)
        assert len(data["colors"]) == 2

    def test_title_contains_team_name(self, two_quarter_summaries, sample_config):
        data = _build_dashboard_data(sample_config, two_quarter_summaries)
        assert "Test Team" in data["title"]

    def test_data_is_json_serializable(self, two_quarter_summaries, sample_config):
        data = _build_dashboard_data(sample_config, two_quarter_summaries)
        json.dumps(data)


class TestBuildConfigData:
    def test_github_orgs(self, sample_config):
        data = _build_config_data(sample_config, has_scoring=False)
        assert data["github_orgs"] == ["test-org"]

    def test_gitlab_url(self, sample_config):
        data = _build_config_data(sample_config, has_scoring=False)
        assert data["gitlab_url"] == "https://gitlab.example.com"

    def test_engineers(self, sample_config):
        data = _build_config_data(sample_config, has_scoring=False)
        assert len(data["engineers"]) == 2
        assert data["engineers"][0]["name"] == "Alice"

    def test_scoring_none_without_scoring(self, sample_config):
        data = _build_config_data(sample_config, has_scoring=False)
        assert data["scoring"] is None

    def test_scoring_present_with_scoring(self, sample_config):
        data = _build_config_data(sample_config, has_scoring=True)
        assert data["scoring"] is not None
        assert "size_points" in data["scoring"]
        assert "diff_thresholds" in data["scoring"]


class TestBuildTableRowData:
    def test_contains_engineer_names(self, two_quarter_summaries):
        rows = _build_table_row_data(two_quarter_summaries, ["Alice", "Bob"], has_scoring=False)
        assert rows[0]["name"] == "Alice"
        assert rows[1]["name"] == "Bob"

    def test_quarters_data(self, two_quarter_summaries):
        rows = _build_table_row_data(two_quarter_summaries, ["Alice", "Bob"], has_scoring=False)
        assert len(rows[0]["quarters"]) == 2
        assert rows[0]["quarters"][1]["total"] == 15

    def test_growth(self, two_quarter_summaries):
        rows = _build_table_row_data(two_quarter_summaries, ["Alice", "Bob"], has_scoring=False)
        assert "%" in rows[0]["growth"]


class TestGenerateDashboard:
    def test_writes_html_file(self, tmp_path, two_quarter_summaries, sample_config):
        out = str(tmp_path / "test.html")
        generate_dashboard(sample_config, two_quarter_summaries, out)
        assert os.path.exists(out)
        content = open(out).read()
        assert "<!DOCTYPE html>" in content
        assert "Test Team" in content

    def test_contains_dashboard_data(self, tmp_path, two_quarter_summaries, sample_config):
        out = str(tmp_path / "test.html")
        generate_dashboard(sample_config, two_quarter_summaries, out)
        content = open(out).read()
        assert "window.__DASHBOARD_DATA__" in content

    def test_contains_engineer_names(self, tmp_path, two_quarter_summaries, sample_config):
        out = str(tmp_path / "test.html")
        generate_dashboard(sample_config, two_quarter_summaries, out)
        content = open(out).read()
        assert "Alice" in content
        assert "Bob" in content

    def test_contains_react_bundle(self, tmp_path, two_quarter_summaries, sample_config):
        out = str(tmp_path / "test.html")
        generate_dashboard(sample_config, two_quarter_summaries, out)
        content = open(out).read()
        assert "react" in content.lower() or "createElement" in content


class TestJiraDashboard:
    def test_has_jira_false_without_bugs(self, two_quarter_summaries, sample_config):
        data = _build_dashboard_data(sample_config, two_quarter_summaries)
        assert data["hasJira"] is False

    def test_has_jira_true_with_bugs(self, sample_config, sample_quarter, sample_quarter_prev):
        from teamdash.models import EngineerQuarterMetrics
        summaries = [
            QuarterSummary(
                quarter=sample_quarter_prev,
                engineers=[
                    EngineerQuarterMetrics(name="Alice", quarter="2024-Q4", github_prs=8, gitlab_mrs=4, reviews=6),
                    EngineerQuarterMetrics(name="Bob", quarter="2024-Q4", github_prs=2, gitlab_mrs=1, reviews=3),
                ],
            ),
            QuarterSummary(
                quarter=sample_quarter,
                engineers=[
                    EngineerQuarterMetrics(name="Alice", quarter="2025-Q1", github_prs=10, gitlab_mrs=5, reviews=8, verified_bugs=5),
                    EngineerQuarterMetrics(name="Bob", quarter="2025-Q1", github_prs=3, gitlab_mrs=2, reviews=4, verified_bugs=3),
                ],
            ),
        ]
        data = _build_dashboard_data(sample_config, summaries)
        assert data["hasJira"] is True

    def test_verified_bugs_in_quarter_data(self, sample_config, sample_quarter, sample_quarter_prev):
        from teamdash.models import EngineerQuarterMetrics
        summaries = [
            QuarterSummary(
                quarter=sample_quarter_prev,
                engineers=[
                    EngineerQuarterMetrics(name="Alice", quarter="2024-Q4", github_prs=8, gitlab_mrs=4, reviews=6, verified_bugs=2),
                    EngineerQuarterMetrics(name="Bob", quarter="2024-Q4", github_prs=2, gitlab_mrs=1, reviews=3, verified_bugs=1),
                ],
            ),
            QuarterSummary(
                quarter=sample_quarter,
                engineers=[
                    EngineerQuarterMetrics(name="Alice", quarter="2025-Q1", github_prs=10, gitlab_mrs=5, reviews=8, verified_bugs=5),
                    EngineerQuarterMetrics(name="Bob", quarter="2025-Q1", github_prs=3, gitlab_mrs=2, reviews=4, verified_bugs=3),
                ],
            ),
        ]
        data = _build_dashboard_data(sample_config, summaries)
        assert data["quarters"][1]["verified_bugs"] == [5, 3]

    def test_verified_bugs_in_table_rows(self, sample_config, sample_quarter, sample_quarter_prev):
        from teamdash.models import EngineerQuarterMetrics
        summaries = [
            QuarterSummary(
                quarter=sample_quarter_prev,
                engineers=[
                    EngineerQuarterMetrics(name="Alice", quarter="2024-Q4", github_prs=8, gitlab_mrs=4, reviews=6, verified_bugs=2),
                    EngineerQuarterMetrics(name="Bob", quarter="2024-Q4", github_prs=2, gitlab_mrs=1, reviews=3),
                ],
            ),
            QuarterSummary(
                quarter=sample_quarter,
                engineers=[
                    EngineerQuarterMetrics(name="Alice", quarter="2025-Q1", github_prs=10, gitlab_mrs=5, reviews=8, verified_bugs=5),
                    EngineerQuarterMetrics(name="Bob", quarter="2025-Q1", github_prs=3, gitlab_mrs=2, reviews=4),
                ],
            ),
        ]
        rows = _build_table_row_data(summaries, ["Alice", "Bob"], has_scoring=False)
        assert rows[0]["quarters"][1]["verified_bugs"] == 5
        assert rows[1]["quarters"][1]["verified_bugs"] == 0


class TestJiraConfigData:
    def test_jira_config_present(self):
        from teamdash.config import JiraConfig
        config = TeamConfig(
            team_name="Test",
            gitlab_url=None,
            github_orgs=["org"],
            engineers=[EngineerConfig(name="A", github="a")],
            jira=JiraConfig(cloud_id="redhat.atlassian.net", project_keys=["CNV", "MTV"]),
        )
        data = _build_config_data(config, has_scoring=False)
        assert data["jira_cloud_id"] == "redhat.atlassian.net"
        assert data["jira_project_keys"] == ["CNV", "MTV"]

    def test_jira_config_absent(self, sample_config):
        data = _build_config_data(sample_config, has_scoring=False)
        assert data["jira_cloud_id"] is None
        assert data["jira_project_keys"] == []


class TestScoringDashboard:
    def test_scoring_data_present(self, two_quarter_summaries_with_scoring, sample_config):
        data = _build_dashboard_data(sample_config, two_quarter_summaries_with_scoring)
        q = data["quarters"][1]
        assert q["sp"] == [34, 16]
        assert q["xl_count"] == [1, 0]
        assert q["review_sp"] == [21, 13]
        assert q["size_dist"][0]["XL"] == 1

    def test_scoring_table_rows(self, two_quarter_summaries_with_scoring):
        rows = _build_table_row_data(
            two_quarter_summaries_with_scoring, ["Alice", "Bob"], has_scoring=True,
        )
        assert rows[0]["quarters"][1]["story_points"] == 34

    def test_scoring_config_data(self, sample_config):
        data = _build_config_data(sample_config, has_scoring=True)
        assert data["scoring"]["size_points"]["XL"] == 21


class TestActivityTypeDashboard:
    def test_has_activity_types_false_without_data(self, two_quarter_summaries, sample_config):
        data = _build_dashboard_data(sample_config, two_quarter_summaries)
        assert data["hasActivityTypes"] is False
        assert data["activityTypeNames"] == []

    def test_has_activity_types_true_with_data(self, sample_config, sample_quarter, sample_quarter_prev):
        from teamdash.models import EngineerQuarterMetrics
        summaries = [
            QuarterSummary(
                quarter=sample_quarter_prev,
                engineers=[
                    EngineerQuarterMetrics(name="Alice", quarter="2024-Q4", github_prs=8, gitlab_mrs=4, reviews=6),
                    EngineerQuarterMetrics(name="Bob", quarter="2024-Q4", github_prs=2, gitlab_mrs=1, reviews=3),
                ],
            ),
            QuarterSummary(
                quarter=sample_quarter,
                engineers=[
                    EngineerQuarterMetrics(
                        name="Alice", quarter="2025-Q1", github_prs=10, gitlab_mrs=5, reviews=8,
                        activity_type_counts={"Incidents & Support": 3, "Security & Compliance": 1},
                    ),
                    EngineerQuarterMetrics(name="Bob", quarter="2025-Q1", github_prs=3, gitlab_mrs=2, reviews=4),
                ],
            ),
        ]
        data = _build_dashboard_data(sample_config, summaries)
        assert data["hasActivityTypes"] is True
        assert "Incidents & Support" in data["activityTypeNames"]
        assert "Security & Compliance" in data["activityTypeNames"]

    def test_activity_types_in_quarter_data(self, sample_config, sample_quarter, sample_quarter_prev):
        from teamdash.models import EngineerQuarterMetrics
        summaries = [
            QuarterSummary(
                quarter=sample_quarter_prev,
                engineers=[
                    EngineerQuarterMetrics(name="Alice", quarter="2024-Q4", github_prs=8, gitlab_mrs=4, reviews=6),
                    EngineerQuarterMetrics(name="Bob", quarter="2024-Q4", github_prs=2, gitlab_mrs=1, reviews=3),
                ],
            ),
            QuarterSummary(
                quarter=sample_quarter,
                engineers=[
                    EngineerQuarterMetrics(
                        name="Alice", quarter="2025-Q1", github_prs=10, gitlab_mrs=5, reviews=8,
                        activity_type_counts={"Incidents & Support": 3},
                    ),
                    EngineerQuarterMetrics(name="Bob", quarter="2025-Q1", github_prs=3, gitlab_mrs=2, reviews=4),
                ],
            ),
        ]
        data = _build_dashboard_data(sample_config, summaries)
        assert data["quarters"][1]["activity_types"][0] == {"Incidents & Support": 3}
        assert data["quarters"][1]["activity_types"][1] == {}
