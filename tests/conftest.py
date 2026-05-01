from __future__ import annotations

import pytest

from teamdash.config import EngineerConfig, TeamConfig
from teamdash.models import EngineerQuarterMetrics, PRDetail, Quarter, QuarterSummary, ScoredPR
from teamdash.scoring import ScoringConfig


@pytest.fixture
def sample_quarter():
    return Quarter(label="2025-Q1", start="2025-01-01", end="2025-03-31")


@pytest.fixture
def sample_quarter_prev():
    return Quarter(label="2024-Q4", start="2024-10-01", end="2024-12-31")


@pytest.fixture
def sample_metrics():
    return EngineerQuarterMetrics(
        name="Alice", quarter="2025-Q1", github_prs=10, gitlab_mrs=5, reviews=8,
    )


@pytest.fixture
def sample_summary(sample_quarter, sample_metrics):
    bob = EngineerQuarterMetrics(
        name="Bob", quarter="2025-Q1", github_prs=3, gitlab_mrs=2, reviews=4,
    )
    return QuarterSummary(quarter=sample_quarter, engineers=[sample_metrics, bob])


@pytest.fixture
def sample_config():
    return TeamConfig(
        team_name="Test Team",
        gitlab_url="https://gitlab.example.com",
        github_orgs=["test-org"],
        engineers=[
            EngineerConfig(name="Alice", github="alice", gitlab="alice_gl"),
            EngineerConfig(name="Bob", github="bob", gitlab="bob_gl"),
        ],
    )


@pytest.fixture
def two_quarter_summaries(sample_quarter, sample_quarter_prev):
    prev_summary = QuarterSummary(
        quarter=sample_quarter_prev,
        engineers=[
            EngineerQuarterMetrics(name="Alice", quarter="2024-Q4", github_prs=8, gitlab_mrs=4, reviews=6),
            EngineerQuarterMetrics(name="Bob", quarter="2024-Q4", github_prs=2, gitlab_mrs=1, reviews=3),
        ],
    )
    cur_summary = QuarterSummary(
        quarter=sample_quarter,
        engineers=[
            EngineerQuarterMetrics(name="Alice", quarter="2025-Q1", github_prs=10, gitlab_mrs=5, reviews=8),
            EngineerQuarterMetrics(name="Bob", quarter="2025-Q1", github_prs=3, gitlab_mrs=2, reviews=4),
        ],
    )
    return [prev_summary, cur_summary]


@pytest.fixture
def sample_pr_detail():
    return PRDetail(
        url="https://github.com/org/repo/pull/42",
        source="github",
        author="alice",
        additions=120,
        deletions=30,
        changed_files=5,
        labels=["feature"],
        review_count=2,
        changes_requested_count=0,
        comments_count=3,
        merge_time_days=1.5,
        created_at="2025-01-10T00:00:00Z",
        closed_at="2025-01-11T12:00:00Z",
    )


@pytest.fixture
def sample_scored_pr(sample_pr_detail):
    return ScoredPR(
        detail=sample_pr_detail,
        size="S",
        points=5,
        flags=[],
        point_type="dev",
    )


@pytest.fixture
def sample_scoring_config():
    return ScoringConfig()


@pytest.fixture
def two_quarter_summaries_with_scoring(sample_quarter, sample_quarter_prev):
    detail1 = PRDetail(
        url="https://github.com/org/repo/pull/1",
        source="github", author="alice",
        additions=100, deletions=20, changed_files=4,
    )
    detail2 = PRDetail(
        url="https://github.com/org/repo/pull/2",
        source="github", author="alice",
        additions=800, deletions=600, changed_files=35,
    )
    scored1 = ScoredPR(detail=detail1, size="S", points=5, point_type="dev")
    scored2 = ScoredPR(detail=detail2, size="XL", points=21, flags=["should-split"], point_type="dev")

    prev_summary = QuarterSummary(
        quarter=sample_quarter_prev,
        engineers=[
            EngineerQuarterMetrics(
                name="Alice", quarter="2024-Q4",
                github_prs=8, gitlab_mrs=4, reviews=6,
                story_points_dev=30, story_points_qe=5, xl_count=0,
            ),
            EngineerQuarterMetrics(
                name="Bob", quarter="2024-Q4",
                github_prs=2, gitlab_mrs=1, reviews=3,
                story_points_dev=10, story_points_qe=0, xl_count=0,
            ),
        ],
    )
    cur_summary = QuarterSummary(
        quarter=sample_quarter,
        engineers=[
            EngineerQuarterMetrics(
                name="Alice", quarter="2025-Q1",
                github_prs=10, gitlab_mrs=5, reviews=8,
                story_points_dev=26, story_points_qe=8, xl_count=1,
                scored_prs=[scored1, scored2],
            ),
            EngineerQuarterMetrics(
                name="Bob", quarter="2025-Q1",
                github_prs=3, gitlab_mrs=2, reviews=4,
                story_points_dev=16, story_points_qe=0, xl_count=0,
            ),
        ],
    )
    return [prev_summary, cur_summary]
