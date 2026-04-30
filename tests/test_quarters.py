from __future__ import annotations

from datetime import date

from teamdash.quarters import get_quarters


class TestGetQuarters:
    def test_basic_four_quarters(self):
        qs = get_quarters(4, reference_date=date(2025, 4, 15))
        assert len(qs) == 4
        labels = [q.label for q in qs]
        assert labels == ["2024-Q2", "2024-Q3", "2024-Q4", "2025-Q1"]

    def test_include_current(self):
        qs = get_quarters(4, reference_date=date(2025, 4, 15), include_current=True)
        labels = [q.label for q in qs]
        assert labels == ["2024-Q3", "2024-Q4", "2025-Q1", "2025-Q2"]

    def test_single_quarter(self):
        qs = get_quarters(1, reference_date=date(2025, 7, 1))
        assert len(qs) == 1
        assert qs[0].label == "2025-Q2"

    def test_quarter_boundaries_start_of_quarter(self):
        qs = get_quarters(1, reference_date=date(2025, 1, 1))
        assert qs[0].label == "2024-Q4"

    def test_quarter_boundaries_end_of_quarter(self):
        qs = get_quarters(1, reference_date=date(2025, 3, 31))
        assert qs[0].label == "2024-Q4"

    def test_end_of_quarter_include_current(self):
        qs = get_quarters(1, reference_date=date(2025, 3, 31), include_current=True)
        assert qs[0].label == "2025-Q1"

    def test_quarter_start_end_dates(self):
        qs = get_quarters(1, reference_date=date(2025, 4, 15))
        q = qs[0]
        assert q.start == "2025-01-01"
        assert q.end == "2025-03-31"

    def test_q4_dates(self):
        qs = get_quarters(1, reference_date=date(2026, 1, 15))
        q = qs[0]
        assert q.label == "2025-Q4"
        assert q.start == "2025-10-01"
        assert q.end == "2025-12-31"

    def test_year_boundary(self):
        qs = get_quarters(2, reference_date=date(2025, 2, 1))
        labels = [q.label for q in qs]
        assert labels == ["2024-Q3", "2024-Q4"]

    def test_oldest_first(self):
        qs = get_quarters(3, reference_date=date(2025, 7, 1))
        labels = [q.label for q in qs]
        assert labels == ["2024-Q4", "2025-Q1", "2025-Q2"]

    def test_february_end_date(self):
        qs = get_quarters(1, reference_date=date(2025, 4, 1))
        assert qs[0].label == "2025-Q1"
        assert qs[0].end == "2025-03-31"

    def test_leap_year_february(self):
        qs = get_quarters(1, reference_date=date(2024, 4, 1))
        assert qs[0].label == "2024-Q1"
        assert qs[0].end == "2024-03-31"
