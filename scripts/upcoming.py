#!/usr/bin/env python3
"""upcoming.py — next N booked calls (not cancelled / rescheduled / no-show).

Usage:
  python scripts/upcoming.py            # next 5
  python scripts/upcoming.py 10
  python scripts/upcoming.py 10 --json
"""

from __future__ import annotations

import sys
from datetime import date

import _common  # noqa: F401
from client import read


def main(argv: list[str]) -> int:
    n = 5
    for a in argv[1:]:
        if a.isdigit():
            n = int(a)
            break

    today = date.today().isoformat()
    sb = read()

    res = (
        sb.table("entries")
        .select("date,time,customer_name,phone,email,deal_type,program,notes")
        .gte("date", today)
        .is_("parent_entry_id", "null")
        .eq("hidden", False)
        .not_.in_("deal_type", ["Cancelled", "Reschedule", "No show"])
        .order("date")
        .order("time")
        .limit(n)
        .execute()
    )
    rows = res.data or []

    if _common.is_json_mode(argv):
        _common.out_json(rows)
        return 0

    print(f"# Next {n} calls (from {today})")
    print()
    if not rows:
        print("  (none)")
        return 0
    for e in rows:
        d = e.get("date")
        t = e.get("time") or "--:--"
        name = e.get("customer_name") or "?"
        dt = e.get("deal_type") or "(open)"
        program = e.get("program") or ""
        note = (e.get("notes") or "").replace("\n", " ").strip()
        if len(note) > 60:
            note = note[:57] + "..."
        print(f"  {d}  {t}  {name:<28}  {dt:<12} {program:<12}  {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
