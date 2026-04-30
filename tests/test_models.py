from __future__ import annotations

from teamdash.models import EngineerQuarterMetrics, Quarter, QuarterSummary


class TestQuarter:
    def test_short_label(self):
        assert Quarter("2025-Q1", "", "").short_label == "Q1'25"

    def test_short_label_different_year(self):
        assert Quarter("2024-Q4", "", "").short_label == "Q4'24"

    def test_short_label_malformed_falls_back(self):
        q = Quarter("badlabel", "", "")
        assert q.short_label == "badlabel"


class TestEngineerQuarterMetrics:
    def test_total(self, sample_metrics):
        assert sample_metrics.total == 15

    def test_total_defaults_to_zero(self):
        m = EngineerQuarterMetrics(name="X", quarter="Q1")
        assert m.total == 0


class TestQuarterSummary:
    def test_total_prs_mrs(self, sample_summary):
        assert sample_summary.total_prs_mrs == 20

    def test_total_github_prs(self, sample_summary):
        assert sample_summary.total_github_prs == 13

    def test_total_gitlab_mrs(self, sample_summary):
        assert sample_summary.total_gitlab_mrs == 7

    def test_total_reviews(self, sample_summary):
        assert sample_summary.total_reviews == 12

    def test_empty_engineers(self, sample_quarter):
        s = QuarterSummary(quarter=sample_quarter)
        assert s.total_prs_mrs == 0
        assert s.total_reviews == 0
