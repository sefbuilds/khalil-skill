#!/usr/bin/env python3
"""day.py — detail of one specific day.

Usage:
  python scripts/day.py 2026-04-15
  python scripts/day.py 2026-04-15 --json
"""

from __future__ import annotations

import sys

import _common  # noqa: F401
from client import read
from kpi import compute_kpis, fmt_eur, kpi_block


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    if not args:
        print("usage: day.py <yyyy-MM-dd> [--json]", file=sys.stderr)
        return 2
    d = args[0]
    if len(d) != 10 or d[4] != "-" or d[7] != "-":
        print("date must be yyyy-MM-dd", file=sys.stderr)
        return 2

    sb = read()
    entries = (
        sb.table("entries")
        .select("*")
        .eq("date", d)
        .eq("hidden", False)
        .order("time")
        .execute()
    ).data or []

    note_row = sb.table("daily_notes").select("note").eq("date", d).maybe_single().execute()
    note = note_row.data["note"] if note_row and note_row.data else ""

    k = compute_kpis(entries)

    if _common.is_json_mode(argv):
        _common.out_json({"date": d, "kpis": k, "note": note, "entries": entries})
        return 0

    print(f"# {d}")
    print()
    if note:
        print(f"📝 {note}")
        print()
    print("KPIs")
    print(kpi_block(k))
    print()
    main_rows = [e for e in entries if e.get("parent_entry_id") is None]
    term_rows = [e for e in entries if e.get("parent_entry_id") is not None]
    print(f"Calls ({len(main_rows)} main rows)")
    if not main_rows:
        print("  (none)")
    for e in main_rows:
        time = e.get("time") or "--:--"
        name = e.get("customer_name") or "?"
        dt = e.get("deal_type") or "(no outcome)"
        program = e.get("program") or ""
        cash = fmt_eur(float(e.get("cash") or 0)) if e.get("cash") else ""
        rev = fmt_eur(float(e.get("revenue") or 0)) if e.get("revenue") else ""
        print(f"  {time}  {name:<28}  {dt:<12} {program:<12}  rev {rev:<8} cash {cash}")
    if term_rows:
        print()
        print(f"Term-children on this day ({len(term_rows)})")
        for e in term_rows:
            name = e.get("customer_name") or "?"
            dt = e.get("deal_type") or ""
            cash = fmt_eur(float(e.get("cash") or 0)) if e.get("cash") else ""
            checked = "✓" if e.get("checked_claimed") else " "
            print(f"  [{checked}] {name:<28}  {dt:<12}  cash {cash}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
