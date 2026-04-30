#!/usr/bin/env python3
"""month.py — full month KPIs vs goals.

Usage:
  python scripts/month.py              # current month
  python scripts/month.py 2026-04      # specific month
  python scripts/month.py --json
"""

from __future__ import annotations

import sys
from calendar import monthrange
from datetime import date

import _common  # noqa: F401
from client import read
from kpi import compute_kpis, fmt_eur, fmt_pct, kpi_block


def parse_args(argv: list[str]) -> str:
    for a in argv[1:]:
        if a.startswith("--"):
            continue
        if len(a) == 7 and a[4] == "-":
            return a
    today = date.today()
    return f"{today.year}-{today.month:02d}"


def main(argv: list[str]) -> int:
    month_key = parse_args(argv)
    year, month = int(month_key[:4]), int(month_key[5:7])
    last_day = monthrange(year, month)[1]
    start = f"{month_key}-01"
    end = f"{month_key}-{last_day:02d}"

    sb = read()
    # Explicit limit: PostgREST defaults to 1000 rows; busy months can exceed
    # that with all the term children + start-date children + main calls.
    entries = (
        sb.table("entries")
        .select("*")
        .gte("date", start)
        .lte("date", end)
        .eq("hidden", False)
        .limit(10000)
        .execute()
    ).data or []

    goals_row = (
        sb.table("goals").select("*").eq("month", month_key).maybe_single().execute()
    )
    goals = goals_row.data if goals_row and goals_row.data else {}

    k = compute_kpis(entries)

    if _common.is_json_mode(argv):
        _common.out_json({"month": month_key, "kpis": k, "goals": goals})
        return 0

    print(f"# {month_key} — month-to-date snapshot ({len(entries)} rows pulled)")
    print()
    print("KPIs")
    print(kpi_block(k))
    print()
    if goals:
        print("Goal pacing  (cash target compared against TOTAL cash — main + paid terms — to match the /meetings dashboard)")
        _line("Cash TOTAL", k["cash_total"], goals.get("cash_target"), money=True)
        _line("  ↳ main only", k["cash_main"], None, money=True)
        _line("  ↳ paid terms", k["cash_terms"], None, money=True)
        _line("Revenue", k["revenue"], goals.get("revenue_target"), money=True)
        _line("Calls booked", k["booked"], goals.get("calls_booked_target"))
        _line("Calls taken", k["calls_taken"], goals.get("calls_taken_target"))
        _line("Close rate (incl.)", k["close_rate_incl"], goals.get("closing_rate_incl_deposits_target"), pct=True)
        _line("Close rate (excl.)", k["close_rate_excl"], goals.get("closing_rate_excl_deposits_target"), pct=True)
        _line("1-1 rate", k["one_to_one_rate"], goals.get("one_to_one_rate_target"), pct=True)
        _line("1-1 upsell rate", k["one_to_one_upsell_rate"], goals.get("one_to_one_upsell_rate_target"), pct=True)
    else:
        print("(no goals set for this month)")
    return 0


def _line(label: str, current, target, money: bool = False, pct: bool = False) -> None:
    target = float(target or 0)
    cur = float(current or 0)
    if money:
        cur_s, tgt_s = fmt_eur(cur), fmt_eur(target) if target else "—"
    elif pct:
        cur_s, tgt_s = fmt_pct(cur), fmt_pct(target) if target else "—"
    else:
        cur_s, tgt_s = f"{int(cur)}", f"{int(target)}" if target else "—"
    pace = (cur / target * 100) if target else 0
    bar = f"  ({pace:.0f}%)" if target else ""
    print(f"  {label:<22} {cur_s:>10} / {tgt_s:>10}{bar}")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
