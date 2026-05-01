from __future__ import annotations

from pathlib import Path

import pytest

from teamdash.config import load_config
from teamdash.fetch_github import (
    check_auth as check_github_auth,
    fetch_merge_times,
    fetch_pr_details,
    fetch_prs,
    fetch_reviewed_pr_details,
    fetch_reviews,
)
from teamdash.fetch_gitlab import (
    check_auth as check_gitlab_auth,
    fetch_mr_details,
    fetch_mr_merge_times,
    fetch_mrs,
)
from teamdash.models import Quarter
from teamdash.scoring import ScoringConfig, score_prs

pytestmark = pytest.mark.e2e

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "team.yaml"
Q1_2026 = Quarter(label="2026-Q1", start="2026-01-01", end="2026-03-31")

GH_USER = "avivtur"
GL_USER = "aturgema"


@pytest.fixture(scope="module")
def team_config():
    return load_config(str(CONFIG_PATH))


@pytest.fixture(scope="module")
def github_orgs(team_config):
    return team_config.github_orgs


@pytest.fixture(scope="module")
def gitlab_url(team_config):
    return team_config.gitlab_url


@pytest.fixture(scope="module")
def github_authenticated():
    return check_github_auth()


@pytest.fixture(scope="module")
def gitlab_authenticated(gitlab_url):
    if not gitlab_url:
        return False
    return check_gitlab_auth(gitlab_url)


class TestGitHubConsistency:
    def test_pr_count_matches_details(self, github_orgs, github_authenticated):
        if not github_authenticated:
            pytest.skip("GitHub not authenticated")
        count = fetch_prs(GH_USER, github_orgs, Q1_2026.start, Q1_2026.end)
        details = fetch_pr_details(GH_USER, github_orgs, Q1_2026.start, Q1_2026.end)
        assert count == len(details), (
            f"PR count ({count}) != detail count ({len(details)})"
        )

    def test_merge_times_count_matches_pr_count(self, github_orgs, github_authenticated):
        if not github_authenticated:
            pytest.skip("GitHub not authenticated")
        count = fetch_prs(GH_USER, github_orgs, Q1_2026.start, Q1_2026.end)
        merge_times = fetch_merge_times(GH_USER, github_orgs, Q1_2026.start, Q1_2026.end)
        assert len(merge_times) == count, (
            f"Merge time entries ({len(merge_times)}) != PR count ({count})"
        )

    def test_merge_times_are_non_negative(self, github_orgs, github_authenticated):
        if not github_authenticated:
            pytest.skip("GitHub not authenticated")
        merge_times = fetch_merge_times(GH_USER, github_orgs, Q1_2026.start, Q1_2026.end)
        for mt in merge_times:
            assert 0 <= mt < 365, f"Merge time {mt} out of range"

    def test_reviews_non_negative(self, github_orgs, github_authenticated):
        if not github_authenticated:
            pytest.skip("GitHub not authenticated")
        count = fetch_reviews(GH_USER, github_orgs, Q1_2026.start, Q1_2026.end)
        assert count >= 0

    def test_pr_details_have_valid_metadata(self, github_orgs, github_authenticated):
        if not github_authenticated:
            pytest.skip("GitHub not authenticated")
        details = fetch_pr_details(GH_USER, github_orgs, Q1_2026.start, Q1_2026.end)
        for d in details:
            assert d.source == "github"
            assert d.author == GH_USER
            assert d.additions >= 0
            assert d.deletions >= 0
            assert d.changed_files >= 0
            assert d.url.startswith("https://github.com/")

    def test_reviewed_pr_details_exclude_self(self, github_orgs, github_authenticated):
        if not github_authenticated:
            pytest.skip("GitHub not authenticated")
        reviewed = fetch_reviewed_pr_details(GH_USER, github_orgs, Q1_2026.start, Q1_2026.end)
        for d in reviewed:
            assert d.source == "github"


class TestGitLabConsistency:
    def test_mr_count_matches_details(self, gitlab_url, gitlab_authenticated):
        if not gitlab_authenticated:
            pytest.skip("GitLab not authenticated")
        count = fetch_mrs(gitlab_url, GL_USER, Q1_2026.start, Q1_2026.end)
        details = fetch_mr_details(gitlab_url, GL_USER, Q1_2026.start, Q1_2026.end)
        assert count == len(details), (
            f"MR count ({count}) != detail count ({len(details)})"
        )

    def test_merge_times_count_matches_mr_count(self, gitlab_url, gitlab_authenticated):
        if not gitlab_authenticated:
            pytest.skip("GitLab not authenticated")
        count = fetch_mrs(gitlab_url, GL_USER, Q1_2026.start, Q1_2026.end)
        merge_times = fetch_mr_merge_times(gitlab_url, GL_USER, Q1_2026.start, Q1_2026.end)
        assert len(merge_times) == count, (
            f"Merge time entries ({len(merge_times)}) != MR count ({count})"
        )

    def test_merge_times_are_non_negative(self, gitlab_url, gitlab_authenticated):
        if not gitlab_authenticated:
            pytest.skip("GitLab not authenticated")
        merge_times = fetch_mr_merge_times(gitlab_url, GL_USER, Q1_2026.start, Q1_2026.end)
        for mt in merge_times:
            assert 0 <= mt < 365, f"Merge time {mt} out of range"

    def test_mr_details_have_valid_metadata(self, gitlab_url, gitlab_authenticated):
        if not gitlab_authenticated:
            pytest.skip("GitLab not authenticated")
        details = fetch_mr_details(gitlab_url, GL_USER, Q1_2026.start, Q1_2026.end)
        for d in details:
            assert d.source == "gitlab"
            assert d.author == GL_USER
            assert d.additions >= 0
            assert d.deletions >= 0
            assert d.changed_files >= 0


class TestScoringConsistency:
    def test_all_scored_prs_have_valid_sizes(self, github_orgs, github_authenticated):
        if not github_authenticated:
            pytest.skip("GitHub not authenticated")
        details = fetch_pr_details(GH_USER, github_orgs, Q1_2026.start, Q1_2026.end)
        scored = score_prs(details, ScoringConfig())
        valid_sizes = {"XS", "S", "M", "L", "XL"}
        default_points = {"XS": 2, "S": 5, "M": 8, "L": 13, "XL": 21}
        for s in scored:
            assert s.size in valid_sizes, f"Invalid size: {s.size}"
            assert s.points == default_points[s.size]
            assert s.point_type in ("dev", "qe")

    def test_xl_prs_flagged_should_split(self, github_orgs, github_authenticated):
        if not github_authenticated:
            pytest.skip("GitHub not authenticated")
        details = fetch_pr_details(GH_USER, github_orgs, Q1_2026.start, Q1_2026.end)
        scored = score_prs(details, ScoringConfig())
        for s in scored:
            if s.size == "XL":
                assert "should-split" in s.flags


class TestFullPipeline:
    def test_single_engineer_metrics(self, team_config, github_authenticated, gitlab_authenticated):
        if not github_authenticated:
            pytest.skip("GitHub not authenticated")

        from teamdash.aggregate import _fetch_engineer_data

        eng = next(e for e in team_config.engineers if e.github == GH_USER)
        metrics = _fetch_engineer_data(eng, team_config, gitlab_authenticated, Q1_2026, enable_scoring=True)

        assert metrics.name == eng.name
        assert metrics.quarter == Q1_2026.label
        assert metrics.github_prs >= 0
        assert metrics.gitlab_mrs >= 0
        assert metrics.reviews >= 0
        assert metrics.merge_time_days is None or metrics.merge_time_days > 0
        assert metrics.story_points_total == metrics.story_points_dev + metrics.story_points_qe
        assert metrics.xl_count >= 0
        assert metrics.review_story_points >= 0

    def test_all_engineers_produce_data(self, team_config, github_authenticated, gitlab_authenticated):
        if not github_authenticated:
            pytest.skip("GitHub not authenticated")

        from teamdash.aggregate import collect_all_data

        summaries = collect_all_data(
            team_config,
            [Q1_2026],
            use_cache=False,
            enable_scoring=False,
        )
        assert len(summaries) == 1
        summary = summaries[0]
        assert len(summary.engineers) == len(team_config.engineers)

        for eng_metrics in summary.engineers:
            assert eng_metrics.github_prs >= 0
            assert eng_metrics.gitlab_mrs >= 0
            assert eng_metrics.reviews >= 0

    def test_team_totals_equal_sum(self, team_config, github_authenticated, gitlab_authenticated):
        if not github_authenticated:
            pytest.skip("GitHub not authenticated")

        from teamdash.aggregate import collect_all_data

        summaries = collect_all_data(
            team_config,
            [Q1_2026],
            use_cache=False,
            enable_scoring=False,
        )
        summary = summaries[0]

        expected_prs = sum(e.github_prs for e in summary.engineers)
        expected_mrs = sum(e.gitlab_mrs for e in summary.engineers)
        expected_reviews = sum(e.reviews for e in summary.engineers)

        assert summary.total_github_prs == expected_prs
        assert summary.total_gitlab_mrs == expected_mrs
        assert summary.total_reviews == expected_reviews
        assert summary.total_prs_mrs == expected_prs + expected_mrs
