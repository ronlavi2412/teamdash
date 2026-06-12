#!/usr/bin/env python3
"""Generate test dashboard HTML files for Playwright tests."""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from teamdash.config import EngineerConfig, JiraConfig, TeamConfig
from teamdash.dashboard import generate_dashboard
from teamdash.models import (
    EngineerQuarterMetrics,
    PRDetail,
    Quarter,
    QuarterSummary,
    ScoredPR,
)

fixtures_dir = Path(__file__).parent


def make_config():
    return TeamConfig(
        team_name="Test Team",
        gitlab_url="https://gitlab.example.com",
        github_orgs=["test-org"],
        engineers=[
            EngineerConfig(name="Alice", github="alice", gitlab="alice_gl"),
            EngineerConfig(name="Bob", github="bob", gitlab="bob_gl"),
        ],
    )


def make_summaries(with_scoring=False):
    q_prev = Quarter(label="2024-Q4", start="2024-10-01", end="2024-12-31")
    q_cur = Quarter(label="2025-Q1", start="2025-01-01", end="2025-03-31")

    if with_scoring:
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
        scored1 = ScoredPR(detail=detail1, size="S", points=5)
        scored2 = ScoredPR(detail=detail2, size="XL", points=21, flags=["should-split"])

        prev = QuarterSummary(
            quarter=q_prev,
            engineers=[
                EngineerQuarterMetrics(
                    name="Alice", quarter="2024-Q4",
                    github_prs=8, gitlab_mrs=4, reviews=6,
                    merge_time_days=2.5,
                    story_points=35, xl_count=0, review_story_points=18,
                ),
                EngineerQuarterMetrics(
                    name="Bob", quarter="2024-Q4",
                    github_prs=2, gitlab_mrs=1, reviews=3,
                    merge_time_days=3.1,
                    story_points=10, xl_count=0, review_story_points=10,
                ),
            ],
        )
        cur = QuarterSummary(
            quarter=q_cur,
            engineers=[
                EngineerQuarterMetrics(
                    name="Alice", quarter="2025-Q1",
                    github_prs=10, gitlab_mrs=5, reviews=8,
                    merge_time_days=1.8,
                    story_points=34, xl_count=1,
                    scored_prs=[scored1, scored2],
                    review_story_points=21,
                ),
                EngineerQuarterMetrics(
                    name="Bob", quarter="2025-Q1",
                    github_prs=3, gitlab_mrs=2, reviews=4,
                    merge_time_days=2.4,
                    story_points=16, xl_count=0, review_story_points=13,
                ),
            ],
        )
    else:
        prev = QuarterSummary(
            quarter=q_prev,
            engineers=[
                EngineerQuarterMetrics(
                    name="Alice", quarter="2024-Q4",
                    github_prs=8, gitlab_mrs=4, reviews=6,
                    merge_time_days=2.5,
                ),
                EngineerQuarterMetrics(
                    name="Bob", quarter="2024-Q4",
                    github_prs=2, gitlab_mrs=1, reviews=3,
                    merge_time_days=3.1,
                ),
            ],
        )
        cur = QuarterSummary(
            quarter=q_cur,
            engineers=[
                EngineerQuarterMetrics(
                    name="Alice", quarter="2025-Q1",
                    github_prs=10, gitlab_mrs=5, reviews=8,
                    merge_time_days=1.8,
                ),
                EngineerQuarterMetrics(
                    name="Bob", quarter="2025-Q1",
                    github_prs=3, gitlab_mrs=2, reviews=4,
                    merge_time_days=2.4,
                ),
            ],
        )
    return [prev, cur]


config = make_config()

generate_dashboard(
    config,
    make_summaries(with_scoring=False),
    str(fixtures_dir / "test-dashboard.html"),
)

generate_dashboard(
    config,
    make_summaries(with_scoring=True),
    str(fixtures_dir / "test-dashboard-scoring.html"),
)


def make_jira_config():
    return TeamConfig(
        team_name="Test Team",
        gitlab_url="https://gitlab.example.com",
        github_orgs=["test-org"],
        engineers=[
            EngineerConfig(name="Alice", github="alice", gitlab="alice_gl", jira_account_id="abc-123"),
            EngineerConfig(name="Bob", github="bob", gitlab="bob_gl", jira_account_id="def-456"),
        ],
        jira=JiraConfig(cloud_id="test.atlassian.net", project_keys=["PROJ"]),
    )


def make_jira_summaries():
    q_prev = Quarter(label="2024-Q4", start="2024-10-01", end="2024-12-31")
    q_cur = Quarter(label="2025-Q1", start="2025-01-01", end="2025-03-31")
    prev = QuarterSummary(
        quarter=q_prev,
        engineers=[
            EngineerQuarterMetrics(
                name="Alice", quarter="2024-Q4",
                github_prs=8, gitlab_mrs=4, reviews=6,
                merge_time_days=2.5, verified_bugs=3,
            ),
            EngineerQuarterMetrics(
                name="Bob", quarter="2024-Q4",
                github_prs=2, gitlab_mrs=1, reviews=3,
                merge_time_days=3.1, verified_bugs=1,
            ),
        ],
    )
    cur = QuarterSummary(
        quarter=q_cur,
        engineers=[
            EngineerQuarterMetrics(
                name="Alice", quarter="2025-Q1",
                github_prs=10, gitlab_mrs=5, reviews=8,
                merge_time_days=1.8, verified_bugs=5,
            ),
            EngineerQuarterMetrics(
                name="Bob", quarter="2025-Q1",
                github_prs=3, gitlab_mrs=2, reviews=4,
                merge_time_days=2.4, verified_bugs=2,
            ),
        ],
    )
    return [prev, cur]


generate_dashboard(
    make_jira_config(),
    make_jira_summaries(),
    str(fixtures_dir / "test-dashboard-jira.html"),
)


def make_activity_type_summaries():
    q_prev = Quarter(label="2024-Q4", start="2024-10-01", end="2024-12-31")
    q_cur = Quarter(label="2025-Q1", start="2025-01-01", end="2025-03-31")
    prev = QuarterSummary(
        quarter=q_prev,
        engineers=[
            EngineerQuarterMetrics(
                name="Alice", quarter="2024-Q4",
                github_prs=8, gitlab_mrs=4, reviews=6,
                merge_time_days=2.5, verified_bugs=3,
                activity_type_counts={
                    "Incidents & Support": 2,
                    "Product / Portfolio Work": 4,
                    "Quality / Stability / Reliability": 1,
                },
            ),
            EngineerQuarterMetrics(
                name="Bob", quarter="2024-Q4",
                github_prs=2, gitlab_mrs=1, reviews=3,
                merge_time_days=3.1, verified_bugs=1,
                activity_type_counts={
                    "Incidents & Support": 1,
                    "Security & Compliance": 1,
                },
            ),
        ],
    )
    cur = QuarterSummary(
        quarter=q_cur,
        engineers=[
            EngineerQuarterMetrics(
                name="Alice", quarter="2025-Q1",
                github_prs=10, gitlab_mrs=5, reviews=8,
                merge_time_days=1.8, verified_bugs=5,
                activity_type_counts={
                    "Incidents & Support": 3,
                    "Product / Portfolio Work": 5,
                    "Quality / Stability / Reliability": 2,
                    "Security & Compliance": 1,
                },
            ),
            EngineerQuarterMetrics(
                name="Bob", quarter="2025-Q1",
                github_prs=3, gitlab_mrs=2, reviews=4,
                merge_time_days=2.4, verified_bugs=2,
                activity_type_counts={
                    "Product / Portfolio Work": 2,
                    "Future Sustainability": 1,
                },
            ),
        ],
    )
    return [prev, cur]


generate_dashboard(
    make_jira_config(),
    make_activity_type_summaries(),
    str(fixtures_dir / "test-dashboard-activity-types.html"),
)

print("Generated test HTML fixtures.")
