#!/usr/bin/env python3
"""today.py — snapshot of today.

Usage:
  python scripts/today.py            # human-readable
  python scripts/today.py --json     # raw JSON
"""

from __future__ import annotations

import sys
from datetime import date

import _common  # noqa: F401 — sets sys.path
from client import read
from kpi import compute_kpis, fmt_eur, kpi_block


def main(argv: list[str]) -> int:
    today = date.today().isoformat()
    sb = read()

    entries = (
        sb.table("entries")
        .select("*")
        .eq("date", today)
        .eq("hidden", False)
        .order("time")
        .execute()
    ).data or []

    note_row = (
        sb.table("daily_notes").select("note").eq("date", today).maybe_single().execute()
    )
    note = note_row.data["note"] if note_row and note_row.data else ""

    k = compute_kpis(entries)

    if _common.is_json_mode(argv):
        _common.out_json({"date": today, "kpis": k, "note": note, "entries": entries})
        return 0

    print(f"# Today — {today}")
    print()
    if note:
        print(f"📝 {note}")
        print()
    print("KPIs")
    print(kpi_block(k))
    print()
    print(f"Today's calls ({len(entries)} rows, hidden filtered):")
    if not entries:
        print("  (none)")
    for e in entries:
        if e.get("parent_entry_id"):
            continue  # only main rows
        time = e.get("time") or "--:--"
        name = e.get("customer_name") or "?"
        dt = e.get("deal_type") or "(no outcome)"
        program = e.get("program") or ""
        cash = fmt_eur(float(e.get("cash") or 0)) if e.get("cash") else ""
        print(f"  {time}  {name:<28}  {dt:<12} {program:<12} {cash}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
