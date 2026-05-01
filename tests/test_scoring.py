from __future__ import annotations

import pytest

from teamdash.models import PRDetail, ScoredPR
from teamdash.scoring import (
    ScoringConfig,
    _classify,
    _detect_label_size,
    _is_qe_pr,
    _max_size,
    _signal_diff_size,
    _signal_files_changed,
    _signal_merge_time,
    _signal_review_friction,
    score_pr,
    score_prs,
)


def _make_detail(**kwargs) -> PRDetail:
    defaults = dict(
        url="https://github.com/org/repo/pull/1",
        source="github",
        author="alice",
        additions=0,
        deletions=0,
        changed_files=1,
    )
    defaults.update(kwargs)
    return PRDetail(**defaults)


@pytest.fixture
def config():
    return ScoringConfig()


class TestClassify:
    def test_below_first_threshold(self):
        assert _classify(10, (50, 200, 500, 1200)) == "XS"

    def test_at_threshold(self):
        assert _classify(50, (50, 200, 500, 1200)) == "XS"

    def test_above_first_threshold(self):
        assert _classify(51, (50, 200, 500, 1200)) == "S"

    def test_above_last_threshold(self):
        assert _classify(1201, (50, 200, 500, 1200)) == "XL"

    def test_zero(self):
        assert _classify(0, (50, 200, 500, 1200)) == "XS"


class TestSignalDiffSize:
    @pytest.mark.parametrize("lines,expected", [
        (0, "XS"), (50, "XS"), (51, "S"), (200, "S"),
        (201, "M"), (500, "M"), (501, "L"), (1200, "L"), (1201, "XL"),
    ])
    def test_thresholds(self, lines, expected):
        assert _signal_diff_size(lines, (50, 200, 500, 1200)) == expected


class TestSignalFilesChanged:
    @pytest.mark.parametrize("files,expected", [
        (1, "XS"), (3, "XS"), (4, "S"), (8, "S"),
        (9, "M"), (15, "M"), (16, "L"), (30, "L"), (31, "XL"),
    ])
    def test_thresholds(self, files, expected):
        assert _signal_files_changed(files, (3, 8, 15, 30)) == expected


class TestSignalReviewFriction:
    def test_no_friction(self):
        assert _signal_review_friction(0, 0) == "XS"

    def test_one_changes_requested(self):
        assert _signal_review_friction(1, 0) == "S"

    def test_many_comments_adds_friction(self):
        assert _signal_review_friction(0, 6) == "S"

    def test_combined(self):
        assert _signal_review_friction(1, 6) == "M"

    def test_high_friction(self):
        assert _signal_review_friction(3, 0) == "L"

    def test_five_comments_no_extra_friction(self):
        assert _signal_review_friction(0, 5) == "XS"


class TestSignalMergeTime:
    @pytest.mark.parametrize("days,expected", [
        (0.0, "XS"), (0.5, "XS"), (0.6, "S"), (2.0, "S"),
        (2.1, "M"), (5.0, "M"), (5.1, "L"), (10.0, "L"), (10.1, "XL"),
    ])
    def test_thresholds(self, days, expected):
        assert _signal_merge_time(days, (0.5, 2.0, 5.0, 10.0)) == expected

    def test_none_returns_xs(self):
        assert _signal_merge_time(None, (0.5, 2.0, 5.0, 10.0)) == "XS"


class TestDetectLabelSize:
    def test_matching_label(self):
        patterns = {"M": ["size/m"]}
        assert _detect_label_size(["size/m"], patterns) == "M"

    def test_no_match(self):
        patterns = {"M": ["size/m"]}
        assert _detect_label_size(["other"], patterns) is None

    def test_case_insensitive(self):
        patterns = {"L": ["size/l"]}
        assert _detect_label_size(["SIZE/L"], patterns) == "L"

    def test_picks_first_matching_size(self):
        patterns = {"S": ["size/s"], "L": ["size/l"]}
        assert _detect_label_size(["size/l", "size/s"], patterns) == "S"

    def test_empty_labels(self):
        patterns = {"M": ["size/m"]}
        assert _detect_label_size([], patterns) is None


class TestIsQePr:
    def test_qe_label_present(self):
        assert _is_qe_pr(["qe-task", "other"], ["qe-task"]) is True

    def test_no_qe_label(self):
        assert _is_qe_pr(["feature", "other"], ["qe-task"]) is False

    def test_case_insensitive(self):
        assert _is_qe_pr(["QE-TASK"], ["qe-task"]) is True

    def test_empty_labels(self):
        assert _is_qe_pr([], ["qe-task"]) is False


class TestMaxSize:
    def test_single(self):
        assert _max_size("M") == "M"

    def test_picks_largest(self):
        assert _max_size("XS", "L", "S") == "L"

    def test_all_xs(self):
        assert _max_size("XS", "XS") == "XS"

    def test_xl_wins(self):
        assert _max_size("S", "XL", "M") == "XL"


class TestScorePr:
    def test_xs_pr(self, config):
        detail = _make_detail(additions=10, deletions=5, changed_files=1)
        result = score_pr(detail, config)
        assert result.size == "XS"
        assert result.points == 2

    def test_large_diff_scores_higher(self, config):
        detail = _make_detail(additions=400, deletions=200, changed_files=5)
        result = score_pr(detail, config)
        assert result.size in ("L", "XL")

    def test_xl_gets_should_split_flag(self, config):
        detail = _make_detail(additions=1000, deletions=500, changed_files=35)
        result = score_pr(detail, config)
        assert result.size == "XL"
        assert "should-split" in result.flags

    def test_label_override(self, config):
        detail = _make_detail(
            additions=1000, deletions=500, changed_files=35,
            labels=["size/xs"],
        )
        result = score_pr(detail, config)
        assert result.size == "XS"
        assert result.points == 2

    def test_qe_label_sets_point_type(self, config):
        detail = _make_detail(additions=10, deletions=5, labels=["qe-task"])
        result = score_pr(detail, config)
        assert result.point_type == "qe"

    def test_no_qe_label_defaults_dev(self, config):
        detail = _make_detail(additions=10, deletions=5, labels=["feature"])
        result = score_pr(detail, config)
        assert result.point_type == "dev"

    def test_review_friction_elevates_size(self, config):
        detail = _make_detail(
            additions=10, deletions=5,
            changes_requested_count=3, comments_count=10,
        )
        result = score_pr(detail, config)
        assert result.size in ("L", "XL")

    def test_merge_time_elevates_size(self, config):
        detail = _make_detail(additions=10, deletions=5, merge_time_days=15.0)
        result = score_pr(detail, config)
        assert result.size == "XL"

    def test_max_of_all_signals(self, config):
        detail = _make_detail(
            additions=100, deletions=50, changed_files=10,
            merge_time_days=3.0, changes_requested_count=1,
        )
        result = score_pr(detail, config)
        assert result.size == "M"


class TestScorePrs:
    def test_batch(self, config):
        details = [
            _make_detail(additions=10, deletions=5),
            _make_detail(additions=300, deletions=100),
        ]
        results = score_prs(details, config)
        assert len(results) == 2
        assert results[0].size == "XS"
        assert results[1].size in ("M", "L")

    def test_empty_list(self, config):
        assert score_prs([], config) == []


class TestScoringConfig:
    def test_defaults(self):
        c = ScoringConfig()
        assert c.size_points["XS"] == 2
        assert c.size_points["XL"] == 21
        assert c.diff_thresholds == (50, 200, 500, 1200)
        assert c.file_thresholds == (3, 8, 15, 30)

    def test_custom_points(self):
        c = ScoringConfig(size_points={"XS": 1, "S": 3, "M": 5, "L": 8, "XL": 13})
        assert c.size_points["XS"] == 1
        assert c.size_points["XL"] == 13

    def test_custom_thresholds(self):
        c = ScoringConfig(diff_thresholds=(10, 50, 100, 200))
        detail = _make_detail(additions=15, deletions=0)
        result = score_pr(detail, c)
        assert result.size == "S"
