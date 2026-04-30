from __future__ import annotations

import os

from teamdash.dashboard import (
    _build_data_block,
    _build_summary_cards,
    _build_table_headers,
    _build_table_rows,
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


class TestBuildSummaryCards:
    def test_contains_card_labels(self, two_quarter_summaries):
        result = _build_summary_cards(two_quarter_summaries)
        assert "Total PRs + MRs" in result
        assert "GitHub PRs" in result
        assert "GitLab MRs" in result
        assert "Code Reviews" in result

    def test_contains_values(self, two_quarter_summaries):
        result = _build_summary_cards(two_quarter_summaries)
        assert "20" in result  # cur total_prs_mrs
        assert "12" in result  # cur reviews


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
    def test_writes_html_file(self, tmp_path, two_quarter_summaries):
        out = str(tmp_path / "test.html")
        generate_dashboard("Test Team", two_quarter_summaries, out)
        assert os.path.exists(out)
        content = open(out).read()
        assert "<!DOCTYPE html>" in content
        assert "Test Team" in content

    def test_contains_chart_js(self, tmp_path, two_quarter_summaries):
        out = str(tmp_path / "test.html")
        generate_dashboard("Test Team", two_quarter_summaries, out)
        content = open(out).read()
        assert "chart.js" in content

    def test_contains_engineer_names(self, tmp_path, two_quarter_summaries):
        out = str(tmp_path / "test.html")
        generate_dashboard("Test Team", two_quarter_summaries, out)
        content = open(out).read()
        assert "Alice" in content
        assert "Bob" in content
