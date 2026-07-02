from __future__ import annotations

from calendar import monthrange
from datetime import date

from teamdash.models import Quarter


def get_quarters(
    num_quarters: int,
    reference_date: date | None = None,
    include_current: bool = False,
) -> list[Quarter]:
    ref = reference_date or date.today()
    q = (ref.month - 1) // 3 + 1
    y = ref.year

    if not include_current:
        end_month = (q - 1) * 3 + 3
        last_day = monthrange(y, end_month)[1]
        if ref <= date(y, end_month, last_day):
            q -= 1
            if q == 0:
                q = 4
                y -= 1

    quarters: list[Quarter] = []
    for _ in range(num_quarters):
        start_month = (q - 1) * 3 + 1
        end_month = start_month + 2
        last_day = monthrange(y, end_month)[1]

        quarters.append(
            Quarter(
                label=f"{y}-Q{q}",
                start=date(y, start_month, 1).isoformat(),
                end=date(y, end_month, last_day).isoformat(),
            )
        )

        q -= 1
        if q == 0:
            q = 4
            y -= 1

    quarters.reverse()
    return quarters
