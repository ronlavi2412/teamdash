#!/usr/bin/env python3
"""Generate test dashboard HTML files for Playwright tests."""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from teamdash.config import EngineerConfig, JiraConfig, TeamConfig  # noqa: E402
from teamdash.dashboard import (  # noqa: E402
    build_dashboard_data,
    generate_dashboard,
    generate_dashboard_from_data,
)
from teamdash.models import (  # noqa: E402
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
            source="github",
            author="alice",
            additions=100,
            deletions=20,
            changed_files=4,
        )
        detail2 = PRDetail(
            url="https://github.com/org/repo/pull/2",
            source="github",
            author="alice",
            additions=800,
            deletions=600,
            changed_files=35,
        )
        scored1 = ScoredPR(detail=detail1, size="S", points=5)
        scored2 = ScoredPR(detail=detail2, size="XL", points=21, flags=["should-split"])

        prev = QuarterSummary(
            quarter=q_prev,
            engineers=[
                EngineerQuarterMetrics(
                    name="Alice",
                    quarter="2024-Q4",
                    github_prs=8,
                    gitlab_mrs=4,
                    reviews=6,
                    merge_time_days=2.5,
                    complexity_points=35,
                    xl_count=0,
                    review_complexity_points=18,
                ),
                EngineerQuarterMetrics(
                    name="Bob",
                    quarter="2024-Q4",
                    github_prs=2,
                    gitlab_mrs=1,
                    reviews=3,
                    merge_time_days=3.1,
                    complexity_points=10,
                    xl_count=0,
                    review_complexity_points=10,
                ),
            ],
        )
        cur = QuarterSummary(
            quarter=q_cur,
            engineers=[
                EngineerQuarterMetrics(
                    name="Alice",
                    quarter="2025-Q1",
                    github_prs=10,
                    gitlab_mrs=5,
                    reviews=8,
                    merge_time_days=1.8,
                    complexity_points=34,
                    xl_count=1,
                    scored_prs=[scored1, scored2],
                    review_complexity_points=21,
                ),
                EngineerQuarterMetrics(
                    name="Bob",
                    quarter="2025-Q1",
                    github_prs=3,
                    gitlab_mrs=2,
                    reviews=4,
                    merge_time_days=2.4,
                    complexity_points=16,
                    xl_count=0,
                    review_complexity_points=13,
                ),
            ],
        )
    else:
        prev = QuarterSummary(
            quarter=q_prev,
            engineers=[
                EngineerQuarterMetrics(
                    name="Alice",
                    quarter="2024-Q4",
                    github_prs=8,
                    gitlab_mrs=4,
                    reviews=6,
                    merge_time_days=2.5,
                ),
                EngineerQuarterMetrics(
                    name="Bob",
                    quarter="2024-Q4",
                    github_prs=2,
                    gitlab_mrs=1,
                    reviews=3,
                    merge_time_days=3.1,
                ),
            ],
        )
        cur = QuarterSummary(
            quarter=q_cur,
            engineers=[
                EngineerQuarterMetrics(
                    name="Alice",
                    quarter="2025-Q1",
                    github_prs=10,
                    gitlab_mrs=5,
                    reviews=8,
                    merge_time_days=1.8,
                ),
                EngineerQuarterMetrics(
                    name="Bob",
                    quarter="2025-Q1",
                    github_prs=3,
                    gitlab_mrs=2,
                    reviews=4,
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
            EngineerConfig(
                name="Alice",
                github="alice",
                gitlab="alice_gl",
                jira_account_id="abc-123",
            ),
            EngineerConfig(
                name="Bob", github="bob", gitlab="bob_gl", jira_account_id="def-456"
            ),
        ],
        jira=JiraConfig(cloud_id="test.atlassian.net", project_keys=["PROJ"]),
    )


def make_jira_summaries():
    q_prev = Quarter(label="2024-Q4", start="2024-10-01", end="2024-12-31")
    q_cur = Quarter(label="2025-Q1", start="2025-01-01", end="2025-03-31")
    prev = QuarterSummary(
        quarter=q_prev,
        verified_bugs=8,
        engineers=[
            EngineerQuarterMetrics(
                name="Alice",
                quarter="2024-Q4",
                github_prs=8,
                gitlab_mrs=4,
                reviews=6,
                merge_time_days=2.5,
            ),
            EngineerQuarterMetrics(
                name="Bob",
                quarter="2024-Q4",
                github_prs=2,
                gitlab_mrs=1,
                reviews=3,
                merge_time_days=3.1,
            ),
        ],
    )
    cur = QuarterSummary(
        quarter=q_cur,
        verified_bugs=14,
        engineers=[
            EngineerQuarterMetrics(
                name="Alice",
                quarter="2025-Q1",
                github_prs=10,
                gitlab_mrs=5,
                reviews=8,
                merge_time_days=1.8,
            ),
            EngineerQuarterMetrics(
                name="Bob",
                quarter="2025-Q1",
                github_prs=3,
                gitlab_mrs=2,
                reviews=4,
                merge_time_days=2.4,
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
        verified_bugs=8,
        engineers=[
            EngineerQuarterMetrics(
                name="Alice",
                quarter="2024-Q4",
                github_prs=8,
                gitlab_mrs=4,
                reviews=6,
                merge_time_days=2.5,
                activity_type_counts={
                    "Incidents & Support": 10,
                    "Product / Portfolio Work": 18,
                    "Quality / Stability / Reliability": 5,
                },
                sprint_activity_type_counts={
                    "Incidents & Support": 8,
                    "Product / Portfolio Work": 15,
                    "Quality / Stability / Reliability": 5,
                },
            ),
            EngineerQuarterMetrics(
                name="Bob",
                quarter="2024-Q4",
                github_prs=2,
                gitlab_mrs=1,
                reviews=3,
                merge_time_days=3.1,
                activity_type_counts={
                    "Incidents & Support": 2,
                    "Security & Compliance": 3,
                },
                sprint_activity_type_counts={
                    "Incidents & Support": 2,
                    "Security & Compliance": 3,
                },
            ),
        ],
    )
    cur = QuarterSummary(
        quarter=q_cur,
        verified_bugs=14,
        engineers=[
            EngineerQuarterMetrics(
                name="Alice",
                quarter="2025-Q1",
                github_prs=10,
                gitlab_mrs=5,
                reviews=8,
                merge_time_days=1.8,
                activity_type_counts={
                    "Incidents & Support": 14,
                    "Product / Portfolio Work": 22,
                    "Quality / Stability / Reliability": 8,
                    "Security & Compliance": 3,
                },
                sprint_activity_type_counts={
                    "Incidents & Support": 10,
                    "Product / Portfolio Work": 18,
                    "Quality / Stability / Reliability": 6,
                    "Security & Compliance": 3,
                },
            ),
            EngineerQuarterMetrics(
                name="Bob",
                quarter="2025-Q1",
                github_prs=3,
                gitlab_mrs=2,
                reviews=4,
                merge_time_days=2.4,
                activity_type_counts={
                    "Product / Portfolio Work": 10,
                    "Future Sustainability": 5,
                },
                sprint_activity_type_counts={
                    "Product / Portfolio Work": 8,
                    "Future Sustainability": 5,
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


cycle_time_data = {
    "2024-Q4": {
        "PROJ-A": {
            "Story": {
                "dev": [3.0, 5.0],
                "build": [1.0, 2.0],
                "qe": [2.0, 4.0],
                "total": [6.0, 11.0],
            },
            "Bug": {"dev": [8.0], "build": [1.5], "qe": [3.0], "total": [12.5]},
        },
        "PROJ-B": {
            "Story": {
                "dev": [4.0, 6.0],
                "build": [1.0, 2.5],
                "qe": [3.0, 5.0],
                "total": [8.0, 13.5],
            },
        },
    },
    "2025-Q1": {
        "PROJ-A": {
            "Story": {
                "dev": [2.0, 4.0, 6.0],
                "build": [1.0, 1.5, 2.0],
                "qe": [2.0, 3.0, 4.0],
                "total": [5.0, 8.5, 12.0],
            },
        },
        "PROJ-B": {
            "Bug": {
                "dev": [5.0, 7.0],
                "build": [2.0, 3.0],
                "qe": [4.0, 6.0],
                "total": [11.0, 16.0],
            },
        },
    },
}

ct_data = build_dashboard_data(
    make_jira_config(),
    make_jira_summaries(),
    cycle_time_data=cycle_time_data,
)
generate_dashboard_from_data(
    ct_data, str(fixtures_dir / "test-dashboard-cycle-time.html")
)

print("Generated test HTML fixtures.")
