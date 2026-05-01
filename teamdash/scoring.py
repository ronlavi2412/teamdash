from __future__ import annotations

from dataclasses import dataclass, field

from teamdash.models import PRDetail, ScoredPR

SIZES = ("XS", "S", "M", "L", "XL")


@dataclass
class ScoringConfig:
    size_points: dict[str, int] = field(default_factory=lambda: {
        "XS": 2, "S": 5, "M": 8, "L": 13, "XL": 21,
    })
    diff_thresholds: tuple[int, ...] = (50, 200, 500, 1200)
    file_thresholds: tuple[int, ...] = (3, 8, 15, 30)
    merge_time_thresholds: tuple[float, ...] = (0.5, 2.0, 5.0, 10.0)
    size_label_patterns: dict[str, list[str]] = field(default_factory=lambda: {
        "XS": ["size/xs", "t-shirt/xs"],
        "S": ["size/s", "t-shirt/s"],
        "M": ["size/m", "t-shirt/m"],
        "L": ["size/l", "t-shirt/l"],
        "XL": ["size/xl", "t-shirt/xl"],
    })
    qe_labels: list[str] = field(default_factory=lambda: [
        "qe-task", "needs-qe-validation", "bug", "type/bug",
    ])


def _classify(value: int | float, thresholds: tuple[int | float, ...]) -> str:
    for i, t in enumerate(thresholds):
        if value <= t:
            return SIZES[i]
    return SIZES[-1]


def _signal_diff_size(total_lines: int, thresholds: tuple[int, ...]) -> str:
    return _classify(total_lines, thresholds)


def _signal_files_changed(changed_files: int, thresholds: tuple[int, ...]) -> str:
    return _classify(changed_files, thresholds)


def _signal_review_friction(changes_requested: int, comments: int) -> str:
    friction = changes_requested + (1 if comments > 5 else 0)
    if friction == 0:
        return "XS"
    if friction == 1:
        return "S"
    if friction == 2:
        return "M"
    return "L"


def _signal_merge_time(days: float | None, thresholds: tuple[float, ...]) -> str:
    if days is None:
        return "XS"
    return _classify(days, thresholds)


def _detect_label_size(
    labels: list[str], patterns: dict[str, list[str]]
) -> str | None:
    lower_labels = [l.lower() for l in labels]
    for size in SIZES:
        for pattern in patterns.get(size, []):
            if pattern.lower() in lower_labels:
                return size
    return None


def _is_qe_pr(labels: list[str], qe_patterns: list[str]) -> bool:
    lower_labels = {l.lower() for l in labels}
    return any(p.lower() in lower_labels for p in qe_patterns)


def _max_size(*sizes: str) -> str:
    indices = [SIZES.index(s) for s in sizes if s in SIZES]
    return SIZES[max(indices)] if indices else "XS"


def score_pr(detail: PRDetail, config: ScoringConfig) -> ScoredPR:
    label_size = _detect_label_size(detail.labels, config.size_label_patterns)

    if label_size is not None:
        size = label_size
    else:
        size = _max_size(
            _signal_diff_size(detail.total_lines, config.diff_thresholds),
            _signal_files_changed(detail.changed_files, config.file_thresholds),
            _signal_review_friction(
                detail.changes_requested_count, detail.comments_count
            ),
            _signal_merge_time(detail.merge_time_days, config.merge_time_thresholds),
        )

    points = config.size_points.get(size, 0)
    flags: list[str] = []
    if size == "XL":
        flags.append("should-split")

    point_type = "qe" if _is_qe_pr(detail.labels, config.qe_labels) else "dev"

    return ScoredPR(
        detail=detail,
        size=size,
        points=points,
        flags=flags,
        point_type=point_type,
    )


def score_prs(details: list[PRDetail], config: ScoringConfig) -> list[ScoredPR]:
    return [score_pr(d, config) for d in details]
