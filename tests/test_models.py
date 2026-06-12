from __future__ import annotations

from teamdash.models import EngineerQuarterMetrics, PRDetail, Quarter, QuarterSummary, ScoredPR


class TestQuarter:
    def test_short_label(self):
        assert Quarter("2025-Q1", "", "").short_label == "Q1'25"

    def test_short_label_different_year(self):
        assert Quarter("2024-Q4", "", "").short_label == "Q4'24"

    def test_short_label_malformed_falls_back(self):
        q = Quarter("badlabel", "", "")
        assert q.short_label == "badlabel"


class TestPRDetail:
    def test_total_lines(self):
        d = PRDetail(url="", source="github", author="a", additions=100, deletions=50, changed_files=3)
        assert d.total_lines == 150

    def test_total_lines_zero(self):
        d = PRDetail(url="", source="github", author="a", additions=0, deletions=0, changed_files=0)
        assert d.total_lines == 0


class TestScoredPR:
    def test_defaults(self):
        detail = PRDetail(url="", source="github", author="a", additions=0, deletions=0, changed_files=0)
        sp = ScoredPR(detail=detail, size="M", points=8)
        assert sp.flags == []


class TestEngineerQuarterMetrics:
    def test_total(self, sample_metrics):
        assert sample_metrics.total == 15

    def test_total_defaults_to_zero(self):
        m = EngineerQuarterMetrics(name="X", quarter="Q1")
        assert m.total == 0

    def test_story_points(self):
        m = EngineerQuarterMetrics(name="X", quarter="Q1", story_points=15)
        assert m.story_points == 15

    def test_story_points_default_zero(self):
        m = EngineerQuarterMetrics(name="X", quarter="Q1")
        assert m.story_points == 0


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

    def test_median_merge_time_days(self, sample_quarter):
        engineers = [
            EngineerQuarterMetrics(name="A", quarter="Q1", merge_time_days=2.0),
            EngineerQuarterMetrics(name="B", quarter="Q1", merge_time_days=4.0),
        ]
        s = QuarterSummary(quarter=sample_quarter, engineers=engineers)
        assert s.median_merge_time_days == 3.0

    def test_median_merge_time_days_skips_none(self, sample_quarter):
        engineers = [
            EngineerQuarterMetrics(name="A", quarter="Q1", merge_time_days=6.0),
            EngineerQuarterMetrics(name="B", quarter="Q1", merge_time_days=None),
        ]
        s = QuarterSummary(quarter=sample_quarter, engineers=engineers)
        assert s.median_merge_time_days == 6.0

    def test_median_merge_time_days_all_none(self, sample_quarter):
        engineers = [
            EngineerQuarterMetrics(name="A", quarter="Q1"),
            EngineerQuarterMetrics(name="B", quarter="Q1"),
        ]
        s = QuarterSummary(quarter=sample_quarter, engineers=engineers)
        assert s.median_merge_time_days is None

    def test_total_story_points(self, sample_quarter):
        engineers = [
            EngineerQuarterMetrics(name="A", quarter="Q1", story_points=15),
            EngineerQuarterMetrics(name="B", quarter="Q1", story_points=8),
        ]
        s = QuarterSummary(quarter=sample_quarter, engineers=engineers)
        assert s.total_story_points == 23

    def test_total_xl_count(self, sample_quarter):
        engineers = [
            EngineerQuarterMetrics(name="A", quarter="Q1", xl_count=2),
            EngineerQuarterMetrics(name="B", quarter="Q1", xl_count=1),
        ]
        s = QuarterSummary(quarter=sample_quarter, engineers=engineers)
        assert s.total_xl_count == 3

    def test_total_verified_bugs(self, sample_quarter):
        engineers = [
            EngineerQuarterMetrics(name="A", quarter="Q1", verified_bugs=5),
            EngineerQuarterMetrics(name="B", quarter="Q1", verified_bugs=3),
        ]
        s = QuarterSummary(quarter=sample_quarter, engineers=engineers)
        assert s.total_verified_bugs == 8

    def test_verified_bugs_default_zero(self):
        m = EngineerQuarterMetrics(name="X", quarter="Q1")
        assert m.verified_bugs == 0

    def test_activity_type_counts_default_empty(self):
        m = EngineerQuarterMetrics(name="X", quarter="Q1")
        assert m.activity_type_counts == {}

    def test_total_activity_type_counts(self, sample_quarter):
        engineers = [
            EngineerQuarterMetrics(
                name="A", quarter="Q1",
                activity_type_counts={"Incidents & Support": 3, "Security & Compliance": 1},
            ),
            EngineerQuarterMetrics(
                name="B", quarter="Q1",
                activity_type_counts={"Incidents & Support": 2, "Product / Portfolio Work": 4},
            ),
        ]
        s = QuarterSummary(quarter=sample_quarter, engineers=engineers)
        totals = s.total_activity_type_counts
        assert totals == {
            "Incidents & Support": 5,
            "Security & Compliance": 1,
            "Product / Portfolio Work": 4,
        }

    def test_total_activity_type_counts_empty(self, sample_quarter):
        engineers = [
            EngineerQuarterMetrics(name="A", quarter="Q1"),
            EngineerQuarterMetrics(name="B", quarter="Q1"),
        ]
        s = QuarterSummary(quarter=sample_quarter, engineers=engineers)
        assert s.total_activity_type_counts == {}
