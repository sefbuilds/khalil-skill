#!/usr/bin/env python3
"""recap.py — weekly recap (Mon–Sun).

Usage:
  python scripts/recap.py                # this ISO week
  python scripts/recap.py 2026-W17       # specific ISO week
  python scripts/recap.py --json
"""

from __future__ import annotations

import sys
from datetime import date, timedelta

import _common  # noqa: F401
from client import read
from kpi import compute_kpis, kpi_block


def parse_week(argv: list[str]) -> tuple[date, date]:
    for a in argv[1:]:
        if a.startswith("--"):
            continue
        if "W" in a or "-w" in a.lower():
            year_s, week_s = a.upper().split("-W")
            year = int(year_s)
            week = int(week_s)
            # ISO week: Mon = day 1
            mon = date.fromisocalendar(year, week, 1)
            sun = mon + timedelta(days=6)
            return mon, sun
    today = date.today()
    weekday = today.weekday()  # Mon = 0
    mon = today - timedelta(days=weekday)
    sun = mon + timedelta(days=6)
    return mon, sun


def main(argv: list[str]) -> int:
    mon, sun = parse_week(argv)
    sb = read()

    entries = (
        sb.table("entries")
        .select("*")
        .gte("date", mon.isoformat())
        .lte("date", sun.isoformat())
        .eq("hidden", False)
        .execute()
    ).data or []

    k = compute_kpis(entries)

    # Daily breakdown
    daily: dict[str, list[dict]] = {}
    for e in entries:
        daily.setdefault(e["date"], []).append(e)

    if _common.is_json_mode(argv):
        days_payload = {d: compute_kpis(rows) for d, rows in daily.items()}
        _common.out_json({"week_start": mon.isoformat(), "week_end": sun.isoformat(), "kpis": k, "daily": days_payload})
        return 0

    iso = mon.isocalendar()
    print(f"# Week {iso.year}-W{iso.week:02d}  ({mon} → {sun})")
    print()
    print("Totals")
    print(kpi_block(k))
    print()
    print("Daily")
    for offset in range(7):
        d = mon + timedelta(days=offset)
        if d.weekday() == 6:  # Sunday — skip; calendar excludes it
            continue
        rows = daily.get(d.isoformat(), [])
        dk = compute_kpis(rows)
        wd = d.strftime("%a")
        print(f"  {wd} {d}  taken={dk['calls_taken']:<2} closes={dk['closes_incl_deposits']:<2} rev={int(dk['revenue']):>5}  cash={int(dk["cash_total"]):>5}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
