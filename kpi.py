"""
KPI calculations — mirror the production app exactly.

Two reference files in the app:
- `src/lib/kpi.ts` (calculateKPIs)
- `src/app/calendar/page.tsx` (DayKPIs) and `src/app/meetings/page.tsx` (KPI block)

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


def is_term_deal(deal_type: str | None) -> bool:
    return (deal_type or "").startswith("Term ")


def main_rows(entries: Iterable[dict]) -> list[dict]:
    """
    Match the meetings page mainRows filter exactly:
      - parent_entry_id IS NULL
      - deal_type is NOT a term ("Term X/Y")
      - deal_type is NOT "Start date"

    Hidden rows must already be filtered out.
    """
    out = []
    for e in entries:
        if e.get("parent_entry_id") is not None:
            continue
        dt = e.get("deal_type")
        if is_term_deal(dt):
            continue
        if dt == "Start date":
            continue
        out.append(e)
    return out


def paid_term_rows(entries: Iterable[dict]) -> list[dict]:
    """
    Term-children rows where the cash has actually been received
    (`checked_claimed = true`). Hidden rows must already be filtered out.
    """
    return [
        e
        for e in entries
        if is_term_deal(e.get("deal_type")) and e.get("checked_claimed") is True
    ]


def compute_kpis(entries: Iterable[dict]) -> dict:
    """
    Returns the same KPI numbers the app shows for the given entries.
    Pass in a date-range slice (already filtered by date in your SELECT).
    This function will filter `hidden` and pick main rows.
    """
    visible = filter_visible(entries)
    main = main_rows(visible)
    terms_paid = paid_term_rows(visible)

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

    # Cash split — matches the meetings page top-row cards:
    #   Cash Collected  = cash_main   (main rows only)
    #   Terms collected = cash_terms  (paid term children)
    #   Total           = cash_total  (the dashboard sum people read mentally)
    cash_main = sum(_num(e.get("cash")) for e in main)
    cash_terms = sum(_num(e.get("cash")) for e in terms_paid)
    cash_total = cash_main + cash_terms

    # Revenue: only count rows whose deal_type is Deposit / PIF / 2T / 3T.
    # Matches the meetings page logic (totalRevenue + depositRevenue) and
    # ignores stray revenue values on No-close / Cancelled / etc rows.
    revenue_excl_deposit = sum(_num(e.get("revenue")) for e in main if e.get("deal_type") in CLOSED_TYPES)
    revenue_deposit = sum(_num(e.get("revenue")) for e in main if e.get("deal_type") == "Deposit")
    revenue_incl_deposit = revenue_excl_deposit + revenue_deposit
    # `revenue` (default field) = incl. deposit, since /calendar Rev card
    # treats deposits as closes.
    revenue = revenue_incl_deposit

    # Commission split — matches the /meetings cards "Commissie excl. terms"
    # and "Commissies from terms".
    commission_main = sum(_num(e.get("commission_payable")) for e in main)
    commission_terms = sum(_num(e.get("commission_payable")) for e in terms_paid)
    commission_total = commission_main + commission_terms

    aov = (sum(_num(e.get("revenue")) for e in closeish) / len(closeish)) if closeish else 0.0
    cash_per_call = (cash_main / calls_taken) if calls_taken else 0.0

    close_rate_incl = (closes_w_dep / calls_taken * 100) if calls_taken else 0.0
    close_rate_excl = (closes_strict / calls_taken * 100) if calls_taken else 0.0

    one_to_one_closes = sum(
        1 for e in main if e.get("deal_type") in CLOSED_TYPES and e.get("program") == "1-1"
    )
    one_to_one_upsell_closes = sum(
        1 for e in main if e.get("deal_type") in CLOSED_TYPES and e.get("program") == "Upsell 1-1"
    )
    one_to_one_rate = (one_to_one_closes / closes_strict * 100) if closes_strict else 0.0
    one_to_one_upsell_rate = (one_to_one_upsell_closes / closes_strict * 100) if closes_strict else 0.0

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
        # cash breakdown matches the /meetings page
        "cash_main": cash_main,
        "cash_terms": cash_terms,
        "cash_total": cash_total,
        # `cash` is the dashboard sum: main rows + paid term children.
        # That's what Khalil reads off /meetings as "cash collected".
        "cash": cash_total,
        # revenue
        "revenue": revenue,
        "revenue_incl_deposit": revenue_incl_deposit,
        "revenue_excl_deposit": revenue_excl_deposit,
        # commission breakdown — matches the /meetings cards
        "commission_main": commission_main,
        "commission_terms": commission_terms,
        "commission_total": commission_total,
        "commission": commission_total,  # default = dashboard sum
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
            f"  Cash (main)    {fmt_eur(k['cash_main'])}",
            f"  Terms paid     {fmt_eur(k['cash_terms'])}",
            f"  Cash TOTAL     {fmt_eur(k['cash_total'])}  (main + paid terms — matches /meetings)",
            f"  Revenue        {fmt_eur(k['revenue'])}",
            f"  Commission     {fmt_eur(k['commission_total'])}  (main {fmt_eur(k['commission_main'])} + terms {fmt_eur(k['commission_terms'])})",
            f"  Close rate     {fmt_pct(k['close_rate_incl'])}  (excl. dep: {fmt_pct(k['close_rate_excl'])})",
            f"  AOV            {fmt_eur(k['aov'])}",
            f"  Cash/Call      {fmt_eur(k['cash_per_call'])}",
        ]
    )
