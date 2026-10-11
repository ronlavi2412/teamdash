from __future__ import annotations

import csv
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path


def _date_to_short_quarter(d: date) -> str:
    q = (d.month - 1) // 3 + 1
    return f"Q{q}'{str(d.year)[2:]}"


def load_pto_data(
    path: str,
    target_names: list[str] | None = None,
    pto_name_map: dict[str, str] | None = None,
) -> dict[str, dict[str, float]]:
    """Load PTO data from CSV or XLSX. Returns {quarter_label: {name: days}}.

    pto_name_map: {pto_first_name -> config_name} from config pto_name fields.
    target_names: fallback list for last-name matching when no pto_name_map hit.
    """
    p = Path(path)
    if p.suffix in (".xlsx", ".xls"):
        raw = _load_xlsx(p)
    else:
        raw = _load_csv(p)

    if not target_names:
        return raw

    return _remap_names(raw, target_names, pto_name_map or {})


def _load_xlsx(path: Path) -> dict[str, dict[str, float]]:
    try:
        import openpyxl
    except ImportError:
        print(
            "[ERROR] openpyxl is required for XLSX files: pip install openpyxl",
            file=sys.stderr,
        )
        sys.exit(1)

    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return {}

    header = [str(c).strip() if c else "" for c in rows[0]]
    col = {name: i for i, name in enumerate(header)}

    worker_idx = col.get("Worker")
    date_idx = col.get("Time Off Date")
    amount_idx = col.get("Approved")
    unit_idx = col.get("Unit of Time")

    if any(idx is None for idx in (worker_idx, date_idx, amount_idx, unit_idx)):
        print(
            f"[ERROR] XLSX missing required columns. Found: {header}",
            file=sys.stderr,
        )
        sys.exit(1)

    result: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in rows[1:]:
        if not row[worker_idx]:
            continue
        name = str(row[worker_idx]).strip()
        raw_date = row[date_idx]
        if isinstance(raw_date, datetime):
            d = raw_date.date()
        elif isinstance(raw_date, date):
            d = raw_date
        else:
            d = datetime.strptime(str(raw_date).split()[0], "%Y-%m-%d").date()

        amount = float(row[amount_idx])
        unit = str(row[unit_idx]).strip()

        days = amount / 8.0 if unit == "Hours" else amount

        quarter = _date_to_short_quarter(d)
        result[quarter][name] += days

    wb.close()

    for q in result:
        for name in result[q]:
            result[q][name] = round(result[q][name], 1)

    return dict(result)


def _remap_names(
    data: dict[str, dict[str, float]],
    target_names: list[str],
    pto_name_map: dict[str, str],
) -> dict[str, dict[str, float]]:
    all_pto_names = {n for q in data.values() for n in q}
    name_map: dict[str, str] = {}
    target_set = set(target_names)

    first_name_index: dict[str, str] = {}
    for pto_first, config_name in pto_name_map.items():
        first_name_index[pto_first.lower()] = config_name

    for pn in all_pto_names:
        if pn in target_set:
            name_map[pn] = pn
            continue
        first = pn.split(None, 1)[0].lower()
        if first in first_name_index:
            name_map[pn] = first_name_index[first]
            continue
        print(f"[WARN] PTO name '{pn}' not found in config, skipping", file=sys.stderr)

    result: dict[str, dict[str, float]] = {}
    for quarter, names in data.items():
        mapped: dict[str, float] = {}
        for pn, days in names.items():
            tn = name_map.get(pn)
            if tn:
                mapped[tn] = mapped.get(tn, 0) + days
        if mapped:
            result[quarter] = mapped
    return result


def _load_csv(path: Path) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["name"].strip()
            quarter = row["quarter"].strip()
            days = float(row["days"])
            result[quarter][name] += days

    for q in result:
        for name in result[q]:
            result[q][name] = round(result[q][name], 1)

    return dict(result)
