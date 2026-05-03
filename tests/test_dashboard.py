from __future__ import annotations

import os

from teamdash.dashboard import (
    _build_data_block,
    _build_summary_cards,
    _build_table_headers,
    _build_table_rows,
    _build_team_tab,
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


class TestBuildDataBlock:
    def test_contains_js_const(self, two_quarter_summaries):
        result = _build_data_block(two_quarter_summaries, ["Alice", "Bob"])
        assert result.startswith("const Q = [")
        assert result.endswith("];")

    def test_contains_quarter_labels(self, two_quarter_summaries):
        result = _build_data_block(two_quarter_summaries, ["Alice", "Bob"])
        assert "Q4'24" in result
        assert "Q1'25" in result

    def test_contains_data_arrays(self, two_quarter_summaries):
        result = _build_data_block(two_quarter_summaries, ["Alice", "Bob"])
        assert "gh_prs:" in result
        assert "gl_mrs:" in result
        assert "reviews:" in result
        assert "merge_time:" in result


class TestBuildSummaryCards:
    def test_returns_empty(self, two_quarter_summaries):
        result = _build_summary_cards(two_quarter_summaries)
        assert result == ""


class TestBuildTableHeaders:
    def test_contains_engineer_column(self, two_quarter_summaries):
        result = _build_table_headers(two_quarter_summaries)
        assert "Engineer" in result

    def test_contains_quarter_labels(self, two_quarter_summaries):
        result = _build_table_headers(two_quarter_summaries)
        assert "Q4'24" in result
        assert "Q1'25" in result


class TestBuildTableRows:
    def test_contains_engineer_names(self, two_quarter_summaries):
        result = _build_table_rows(two_quarter_summaries, ["Alice", "Bob"])
        assert "Alice" in result
        assert "Bob" in result

    def test_contains_metrics(self, two_quarter_summaries):
        result = _build_table_rows(two_quarter_summaries, ["Alice", "Bob"])
        assert "<tr>" in result


class TestGenerateDashboard:
    def test_writes_html_file(self, tmp_path, two_quarter_summaries, sample_config):
        out = str(tmp_path / "test.html")
        generate_dashboard(sample_config, two_quarter_summaries, out)
        assert os.path.exists(out)
        content = open(out).read()
        assert "<!DOCTYPE html>" in content
        assert "Test Team" in content

    def test_contains_chart_js(self, tmp_path, two_quarter_summaries, sample_config):
        out = str(tmp_path / "test.html")
        generate_dashboard(sample_config, two_quarter_summaries, out)
        content = open(out).read()
        assert "chart.js" in content

    def test_contains_engineer_names(self, tmp_path, two_quarter_summaries, sample_config):
        out = str(tmp_path / "test.html")
        generate_dashboard(sample_config, two_quarter_summaries, out)
        content = open(out).read()
        assert "Alice" in content
        assert "Bob" in content


class TestTeamTab:
    def test_team_tab_present(self, tmp_path, two_quarter_summaries, sample_config):
        out = str(tmp_path / "test.html")
        generate_dashboard(sample_config, two_quarter_summaries, out)
        content = open(out).read()
        assert 'id="tab-team"' in content
        assert "chart-team-prs" in content
        assert "chart-team-reviews" in content
        assert "chart-team-merge-time" in content

    def test_team_tab_is_default(self, tmp_path, two_quarter_summaries, sample_config):
        out = str(tmp_path / "test.html")
        generate_dashboard(sample_config, two_quarter_summaries, out)
        content = open(out).read()
        assert 'id="tab-team" class="tab-content active"' in content
        assert 'id="tab-overview" class="tab-content">' in content

    def test_team_tab_nav(self, tmp_path, two_quarter_summaries, sample_config):
        out = str(tmp_path / "test.html")
        generate_dashboard(sample_config, two_quarter_summaries, out)
        content = open(out).read()
        assert "switchTab('team')" in content
        assert "Overall Team View" in content

    def test_team_sp_with_scoring(self, tmp_path, two_quarter_summaries_with_scoring, sample_config):
        out = str(tmp_path / "test.html")
        generate_dashboard(sample_config, two_quarter_summaries_with_scoring, out)
        content = open(out).read()
        assert "chart-team-sp" in content

    def test_team_sp_without_scoring(self, tmp_path, two_quarter_summaries, sample_config):
        out = str(tmp_path / "test.html")
        generate_dashboard(sample_config, two_quarter_summaries, out)
        content = open(out).read()
        assert '<canvas id="chart-team-sp">' not in content

    def test_build_team_tab_unit(self):
        result = _build_team_tab(has_scoring=False)
        assert "tab-team" in result
        assert "chart-team-prs" in result
        assert "chart-team-reviews" in result
        assert "chart-team-merge-time" in result
        assert "chart-team-sp" not in result
        assert "chart-team-review-sp" not in result

    def test_build_team_tab_scoring_unit(self):
        result = _build_team_tab(has_scoring=True)
        assert "chart-team-sp" in result
        assert "chart-team-review-sp" in result


class TestScoringDashboard:
    def test_complexity_chart_present(self, tmp_path, two_quarter_summaries_with_scoring, sample_config):
        out = str(tmp_path / "test.html")
        generate_dashboard(sample_config, two_quarter_summaries_with_scoring, out)
        content = open(out).read()
        assert "chart-complexity-trend" in content

    def test_no_scoring_hides_complexity(self, tmp_path, two_quarter_summaries, sample_config):
        out = str(tmp_path / "test.html")
        generate_dashboard(sample_config, two_quarter_summaries, out)
        content = open(out).read()
        assert "tab-storypoints" not in content
        assert '<div class="label">Dev Points</div>' not in content

    def test_scoring_data_block(self, two_quarter_summaries_with_scoring):
        from teamdash.dashboard import _build_data_block
        result = _build_data_block(two_quarter_summaries_with_scoring, ["Alice", "Bob"])
        assert "sp:" in result
        assert "xl_count:" in result
        assert "review_sp:" in result
        assert "size_dist:" in result

    def test_scoring_table_headers(self, two_quarter_summaries_with_scoring):
        from teamdash.dashboard import _build_table_headers
        result = _build_table_headers(two_quarter_summaries_with_scoring, has_scoring=True)
        assert "Complexity " in result

    def test_scoring_table_rows(self, two_quarter_summaries_with_scoring):
        from teamdash.dashboard import _build_table_rows
        result = _build_table_rows(two_quarter_summaries_with_scoring, ["Alice", "Bob"], has_scoring=True)
        assert "Alice" in result

    def test_review_complexity_chart_present(self, tmp_path, two_quarter_summaries_with_scoring, sample_config):
        out = str(tmp_path / "test.html")
        generate_dashboard(sample_config, two_quarter_summaries_with_scoring, out)
        content = open(out).read()
        assert "chart-review-complexity-trend" in content

    def test_review_complexity_hidden_without_scoring(self, tmp_path, two_quarter_summaries, sample_config):
        out = str(tmp_path / "test.html")
        generate_dashboard(sample_config, two_quarter_summaries, out)
        content = open(out).read()
        assert 'id="overview-review-complexity" style="display:none;"' in content

    def test_team_review_sp_with_scoring(self, tmp_path, two_quarter_summaries_with_scoring, sample_config):
        out = str(tmp_path / "test.html")
        generate_dashboard(sample_config, two_quarter_summaries_with_scoring, out)
        content = open(out).read()
        assert "chart-team-review-sp" in content

    def test_team_review_sp_without_scoring(self, tmp_path, two_quarter_summaries, sample_config):
        out = str(tmp_path / "test.html")
        generate_dashboard(sample_config, two_quarter_summaries, out)
        content = open(out).read()
        assert '<canvas id="chart-team-review-sp">' not in content
