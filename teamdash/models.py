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
class EngineerQuarterMetrics:
    name: str
    quarter: str
    github_prs: int = 0
    gitlab_mrs: int = 0
    reviews: int = 0
    merge_time_days: float | None = None

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
    def avg_merge_time_days(self) -> float | None:
        vals = [e.merge_time_days for e in self.engineers if e.merge_time_days is not None]
        return round(sum(vals) / len(vals), 1) if vals else None
