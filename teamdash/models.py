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
    point_type: str = "dev"


@dataclass
class EngineerQuarterMetrics:
    name: str
    quarter: str
    github_prs: int = 0
    gitlab_mrs: int = 0
    reviews: int = 0
    merge_time_days: float | None = None
    story_points_dev: int = 0
    story_points_qe: int = 0
    scored_prs: list[ScoredPR] = field(default_factory=list)
    xl_count: int = 0
    review_story_points: int = 0
    scored_reviews: list[ScoredPR] = field(default_factory=list)
    github_merge_times: list[float] = field(default_factory=list)
    gitlab_merge_times: list[float] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.github_prs + self.gitlab_mrs

    @property
    def story_points_total(self) -> int:
        return self.story_points_dev + self.story_points_qe


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
    def avg_merge_time_days(self) -> float | None:
        vals = [e.merge_time_days for e in self.engineers if e.merge_time_days is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    @property
    def total_story_points(self) -> int:
        return sum(e.story_points_total for e in self.engineers)

    @property
    def total_story_points_dev(self) -> int:
        return sum(e.story_points_dev for e in self.engineers)

    @property
    def total_story_points_qe(self) -> int:
        return sum(e.story_points_qe for e in self.engineers)

    @property
    def total_review_story_points(self) -> int:
        return sum(e.review_story_points for e in self.engineers)

    @property
    def total_xl_count(self) -> int:
        return sum(e.xl_count for e in self.engineers)
