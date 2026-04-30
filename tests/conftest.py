from __future__ import annotations

import pytest

from teamdash.config import EngineerConfig, TeamConfig
from teamdash.models import EngineerQuarterMetrics, Quarter, QuarterSummary


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
