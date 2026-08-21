from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Quarter:
    label: str  # "2026-Q1"
    start: str  # "2026-01-01"
    end: str  # "2026-03-31"

    @property
    def short_label(self) -> str:
        parts = self.label.split("-")
        return f"{parts[1]}'{parts[0][2:]}" if len(parts) == 2 else self.label


@dataclass
class PRDetail:
    url: str
    source: str
    author: str
    additions: int
    deletions: int
    changed_files: int
    title: str = ""
    labels: list[str] = field(default_factory=list)
    review_count: int = 0
    changes_requested_count: int = 0
    comments_count: int = 0
    merge_time_days: float | None = None
    created_at: str = ""
    closed_at: str | None = None

    @property
    def total_lines(self) -> int:
        return self.additions + self.deletions


@dataclass
class ScoredPR:
    detail: PRDetail
    size: str
    points: int
    flags: list[str] = field(default_factory=list)


@dataclass
class EngineerQuarterMetrics:
    name: str
    quarter: str
    github_prs: int = 0
    gitlab_mrs: int = 0
    reviews: int = 0
    github_reviews: int = 0
    merge_time_days: float | None = None
    complexity_points: int = 0
    scored_prs: list[ScoredPR] = field(default_factory=list)
    xl_count: int = 0
    review_complexity_points: int = 0
    scored_reviews: list[ScoredPR] = field(default_factory=list)
    github_merge_times: list[float] = field(default_factory=list)
    gitlab_merge_times: list[float] = field(default_factory=list)
    activity_type_counts: dict[str, int] = field(default_factory=dict)
    sprint_activity_type_counts: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return self.github_prs + self.gitlab_mrs


@dataclass
class QuarterSummary:
    quarter: Quarter
    engineers: list[EngineerQuarterMetrics] = field(default_factory=list)

    @property
    def total_prs_mrs(self) -> int:
        return sum(e.total for e in self.engineers)

    @property
    def total_github_prs(self) -> int:
        return sum(e.github_prs for e in self.engineers)

    @property
    def total_gitlab_mrs(self) -> int:
        return sum(e.gitlab_mrs for e in self.engineers)

    @property
    def total_reviews(self) -> int:
        return sum(e.reviews for e in self.engineers)

    @property
    def median_merge_time_days(self) -> float | None:
        vals = sorted(
            e.merge_time_days for e in self.engineers if e.merge_time_days is not None
        )
        if not vals:
            return None
        n = len(vals)
        mid = n // 2
        return round((vals[mid] if n % 2 else (vals[mid - 1] + vals[mid]) / 2), 1)

    @property
    def total_complexity_points(self) -> int:
        return sum(e.complexity_points for e in self.engineers)

    @property
    def total_review_complexity_points(self) -> int:
        return sum(e.review_complexity_points for e in self.engineers)

    @property
    def total_xl_count(self) -> int:
        return sum(e.xl_count for e in self.engineers)

    verified_bugs: int = 0

    @property
    def total_activity_type_counts(self) -> dict[str, int]:
        totals: dict[str, int] = {}
        for e in self.engineers:
            for at, count in e.activity_type_counts.items():
                totals[at] = totals.get(at, 0) + count
        return totals
