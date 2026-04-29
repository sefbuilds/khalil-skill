"""
KPI calculations — mirror src/lib/kpi.ts and src/app/calendar/page.tsx.

If a number you compute disagrees with the app, the app wins. Re-read this
file and SCHEMA.md to find the divergence.
"""

from __future__ import annotations

from typing import Iterable

CLOSED_TYPES = {"PIF", "2T", "3T"}
CLOSEISH_TYPES = {"PIF", "2T", "3T", "Deposit"}
NOT_TAKEN_TYPES = {"Cancelled", "Reschedule", "No show", "Unqualified"}
NEGATIVE_TYPES = {"No show", "Cancelled", "Reschedule"}


def _num(v) -> float:
    if v is None:
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def filter_visible(entries: Iterable[dict]) -> list[dict]:
    """Drop hidden rows. Always do this before anything else."""
    return [e for e in entries if not e.get("hidden")]


def main_rows(entries: Iterable[dict]) -> list[dict]:
    """Main entries = no parent_entry_id. Hidden already filtered."""
    return [e for e in entries if e.get("parent_entry_id") is None]


def compute_kpis(entries: Iterable[dict]) -> dict:
    """
    Returns the same KPI numbers the app shows for the given entries.
    Pass in a date-range slice of entries (already filtered by date in your
    SELECT). This function will filter `hidden` and select main rows.
    """
    visible = filter_visible(entries)
    main = main_rows(visible)
    booked = len(main)

    cancelled = sum(1 for e in main if e.get("deal_type") == "Cancelled")
    rescheduled = sum(1 for e in main if e.get("deal_type") == "Reschedule")
    no_shows = sum(1 for e in main if e.get("deal_type") == "No show")
    unqualified = sum(1 for e in main if e.get("deal_type") == "Unqualified")

    # Khalil's "calls taken" excludes Unqualified.
    calls_taken = max(booked - cancelled - rescheduled - no_shows - unqualified, 0)

    closes_strict = sum(1 for e in main if e.get("deal_type") in CLOSED_TYPES)
    deposits = sum(1 for e in main if e.get("deal_type") == "Deposit")
    closes_w_dep = closes_strict + deposits

    closeish = [e for e in main if e.get("deal_type") in CLOSEISH_TYPES]

    # Cash and revenue: MAIN rows only — never term children.
    cash = sum(_num(e.get("cash")) for e in main)
    revenue = sum(_num(e.get("revenue")) for e in main)

    aov = (sum(_num(e.get("revenue")) for e in closeish) / len(closeish)) if closeish else 0.0
    cash_per_call = (cash / calls_taken) if calls_taken else 0.0

    # Close rates
    close_rate_incl = (closes_w_dep / calls_taken * 100) if calls_taken else 0.0
    close_rate_excl = (closes_strict / calls_taken * 100) if calls_taken else 0.0

    # 1-1 share within all PIF/2T/3T closes (matches GoalsProgress card)
    one_to_one_closes = sum(1 for e in main if e.get("deal_type") in CLOSED_TYPES and e.get("program") == "1-1")
    one_to_one_upsell_closes = sum(1 for e in main if e.get("deal_type") in CLOSED_TYPES and e.get("program") == "Upsell 1-1")
    one_to_one_rate = (one_to_one_closes / closes_strict * 100) if closes_strict else 0.0
    one_to_one_upsell_rate = (one_to_one_upsell_closes / closes_strict * 100) if closes_strict else 0.0

    # Negatives
    negatives = no_shows + cancelled + rescheduled
    neg_per_taken = (negatives / calls_taken * 100) if calls_taken else 0.0
    neg_per_booked = (negatives / booked * 100) if booked else 0.0

    return {
        "booked": booked,
        "calls_taken": calls_taken,
        "cancelled": cancelled,
        "rescheduled": rescheduled,
        "no_shows": no_shows,
        "unqualified": unqualified,
        "closes_strict": closes_strict,
        "deposits": deposits,
        "closes_incl_deposits": closes_w_dep,
        "cash": cash,
        "revenue": revenue,
        "aov": aov,
        "cash_per_call": cash_per_call,
        "close_rate_incl": close_rate_incl,
        "close_rate_excl": close_rate_excl,
        "one_to_one_rate": one_to_one_rate,
        "one_to_one_upsell_rate": one_to_one_upsell_rate,
        "negatives": negatives,
        "neg_per_taken": neg_per_taken,
        "neg_per_booked": neg_per_booked,
    }


# ---------- formatting helpers ----------


def fmt_eur(n: float) -> str:
    return f"€{int(round(n)):,}".replace(",", ".")


def fmt_pct(n: float) -> str:
    return f"{n:.0f}%"


def kpi_block(k: dict) -> str:
    """Pretty-print KPIs for human-readable output."""
    return "\n".join(
        [
            f"  Booked         {k['booked']}",
            f"  Calls taken    {k['calls_taken']}",
            f"  Closes (incl.) {k['closes_incl_deposits']}  (PIF+2T+3T+Dep)",
            f"  Negatives      {k['negatives']}  (NS {k['no_shows']} / CX {k['cancelled']} / RS {k['rescheduled']})",
            f"  Cash           {fmt_eur(k['cash'])}",
            f"  Revenue        {fmt_eur(k['revenue'])}",
            f"  Close rate     {fmt_pct(k['close_rate_incl'])}  (excl. dep: {fmt_pct(k['close_rate_excl'])})",
            f"  AOV            {fmt_eur(k['aov'])}",
            f"  Cash/Call      {fmt_eur(k['cash_per_call'])}",
        ]
    )
