#!/usr/bin/env python3
"""search.py — search clients by name / phone / email.

Usage:
  python scripts/search.py "Aron"
  python scripts/search.py "+31 6 81" --json
"""

from __future__ import annotations

import sys

import _common  # noqa: F401
from client import read


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    if not args:
        print("usage: search.py <query> [--json]", file=sys.stderr)
        return 2
    q = args[0].strip()

    sb = read()
    pat = f"%{q}%"
    # Supabase PostgREST `or` filter — match name OR email OR phone (ilike).
    res = (
        sb.table("entries")
        .select("date,time,customer_name,phone,email,deal_type,program,revenue,cash,notes")
        .or_(f"customer_name.ilike.{pat},email.ilike.{pat},phone.ilike.{pat}")
        .eq("hidden", False)
        .order("date", desc=True)
        .limit(30)
        .execute()
    )
    rows = res.data or []

    if _common.is_json_mode(argv):
        _common.out_json(rows)
        return 0

    print(f"# Search: \"{q}\" — {len(rows)} hit(s) (newest first)")
    print()
    if not rows:
        print("  (no matches)")
        return 0
    for e in rows:
        d = e.get("date") or "?"
        t = e.get("time") or "--:--"
        name = e.get("customer_name") or "?"
        dt = e.get("deal_type") or ""
        program = e.get("program") or ""
        phone = e.get("phone") or ""
        email = e.get("email") or ""
        print(f"  {d}  {t}  {name:<28}  {dt:<12} {program:<12} {phone:<18} {email}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
