# SCHEMA.md — Khalil's Sales Tracker Data Model

Everything KS-9 needs to know about the Supabase database behind the app. **Read this before interpreting raw rows.**

## Project

- Postgres (Supabase managed)
- Public schema only — no auth schema queries
- RLS is enabled on every table with permissive "Allow all" policies, so the **anon key has read access**. The app uses the same anon key.
- Project ref: see `TOOLS.md`.

## Tables

### `entries` — the heart of the app

One row per call, deal, term-payment, start-date reminder, follow-up reminder. **Most queries hit this table.**

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | PK |
| `date` | date | The day this row belongs to (call date, term-due date, etc.) |
| `customer_name` | text | Display name |
| `phone`, `email` | text | Contact |
| `notes` | text | Free-form per-row note |
| `time` | text | "HH:MM" — call slot when imported from Calendly |
| `deal_type` | text | See "deal_type values" below |
| `program` | text | "1-1", "Upsell 1-1", "Groeps", or null |
| `betaling` | text | Payment method label ("PP", "Bank", etc.) |
| `betaling_uit_deposit_fu` | bool | true if first payment came from a separate deposit row |
| `commission_pct` | numeric | e.g. 13.5 |
| `revenue` | numeric | Total deal value (only set on main rows for closes/deposits) |
| `cash` | numeric | Money received on this row (set on every row that received money) |
| `commission_payable` | numeric | Computed |
| `moet_nog_betalen` | numeric | Remaining balance |
| `parent_entry_id` | uuid (FK → entries.id) | **Non-null on term-children and start-date children.** Null on main rows. |
| `offer_made` | bool | True if Khalil pitched on this call |
| `is_follow_up` | bool | True if this row is from a follow-up call |
| `start_date` | date | Set on a "Start date" reminder child |
| `follow_up_date` | date | Set on a "Follow up date" reminder child |
| `hidden` | bool | **Soft-delete flag. Always filter `hidden = false`.** |
| `calendly_event_uri` | text | Calendly event URI when row came from Calendly import |
| `flagged`, `name_highlighted`, `checked_claimed` | bool | UI flags Khalil sets manually |
| `last_modified_by` | text | Audit-tag set by the writer ("ui", "sync_button", "ui_create_terms", etc.) |
| `created_at`, `updated_at` | timestamptz | Auto |

#### `deal_type` values

| Value | Meaning |
|---|---|
| `PIF` | Paid in full (close) |
| `2T` | 2-termijn close |
| `3T` | 3-termijn close |
| `Deposit` | Commitment + first payment, balance comes later |
| `Term 2/2`, `Term 2/3`, `Term 3/3` etc. | **Term children** — payments that follow a 2T/3T parent. `parent_entry_id` is set. |
| `Start date` | Reminder child for when a closed program starts. `parent_entry_id` is set. |
| `Follow up date` | Reminder child for a planned follow-up. `parent_entry_id` is set. |
| `Follow up` | The call itself was a follow-up (parent_entry_id is null) |
| `No show` | Booked but didn't show |
| `Cancelled` | Booked and cancelled |
| `Reschedule` | Booked and rescheduled |
| `Unqualified` | Took the call, lead wasn't qualified |
| `No close` | Took the call, didn't close (older app convention; "Lost") |
| `Refund` | Refunded after closing |
| (null) | Outcome not yet logged |

#### Critical filters every query needs

- **Always** `hidden = false`. Soft-deleted rows must be ignored.
- "Main rows" = `parent_entry_id IS NULL`. Use this for booking/calls counts and revenue.
- "Term children" = `parent_entry_id IS NOT NULL` AND `deal_type LIKE 'Term %'`. Cash from these is real money received but tied to an earlier close.

### `goals`

Per-month targets and operational thresholds. One row per `month` (yyyy-MM string).

| Column | Type |
|---|---|
| `id` | uuid PK |
| `month` | text, unique (e.g. "2026-04") |
| `cash_target` | numeric (€) |
| `revenue_target` | numeric (€) |
| `calls_booked_target` | int |
| `calls_taken_target` | int |
| `closing_rate_incl_deposits_target` | numeric (% 0–100) |
| `closing_rate_excl_deposits_target` | numeric |
| `one_to_one_rate_target` | numeric |
| `one_to_one_upsell_rate_target` | numeric |
| `no_show_green_max`, `no_show_orange_max` | numeric (% — stay under green for green-zone) |
| `reschedule_green_max` | numeric |
| `cancel_green_max` | numeric |
| `total_negative_green_max`, `total_negative_orange_max` | numeric |
| `created_at`, `updated_at` | timestamptz |

### `daily_notes`

Free-text note per day, surfaced on calendar cells and chart tooltips.

| Column | Type |
|---|---|
| `id` | uuid PK |
| `date` | date, unique |
| `note` | text |
| `created_at`, `updated_at` | timestamptz |

### `app_settings`

Key/value bag. Currently used for: Calendly token, deleted-Calendly-URIs blocklist. KS-9 normally doesn't need this.

### `entries_audit`

Audit log of inserts/updates/deletes on `entries`. Useful for "who changed what when" diagnostics. Not needed for normal KPI reads.

### `clients`, `programs`, `deals`, `scheduled_payments`

Older / legacy tables from the initial schema. The app now uses `entries` for everything. **Don't query these for current data.**

## Relationships

```
entries (main row)
  └─ entries (term children)        parent_entry_id → entries.id
  └─ entries (Start date child)     parent_entry_id → entries.id
  └─ entries (Follow up date child) parent_entry_id → entries.id

goals          one row per yyyy-MM month
daily_notes    one row per yyyy-MM-dd date
```

## KPI Definitions (mirror the app — `src/lib/kpi.ts` + `src/app/calendar/page.tsx`)

These must match exactly or KS-9's numbers will disagree with the app.

```python
visible = [e for e in entries if not e['hidden']]

# Strict main filter — matches the meetings page mainRows filter:
#   parent_entry_id IS NULL
#   AND deal_type NOT LIKE 'Term %'
#   AND deal_type != 'Start date'
def _is_main(e):
    if e.get('parent_entry_id') is not None:
        return False
    dt = e.get('deal_type') or ''
    if dt.startswith('Term '):
        return False
    if dt == 'Start date':
        return False
    return True

main = [e for e in visible if _is_main(e)]
booked = len(main)
cancelled  = sum(1 for e in main if e['deal_type'] == 'Cancelled')
rescheduled = sum(1 for e in main if e['deal_type'] == 'Reschedule')
no_shows   = sum(1 for e in main if e['deal_type'] == 'No show')
unqualified = sum(1 for e in main if e['deal_type'] == 'Unqualified')

calls_taken = booked - cancelled - rescheduled - no_shows - unqualified
# (this is "qualified taken" — Khalil's definition)

closes_strict   = sum(1 for e in main if e['deal_type'] in ('PIF', '2T', '3T'))
closes_w_dep    = closes_strict + sum(1 for e in main if e['deal_type'] == 'Deposit')

close_rate_incl = closes_w_dep / calls_taken if calls_taken else 0  # default
close_rate_excl = closes_strict / calls_taken if calls_taken else 0

closeish = [e for e in main if e['deal_type'] in ('PIF','2T','3T','Deposit')]
aov = (sum(float(e['revenue']) for e in closeish) / len(closeish)) if closeish else 0

# Cash split — matches the /meetings page top-row cards exactly:
cash_main = sum(float(e['cash']) for e in main)

# Paid term children — `checked_claimed = true` means cash already received.
paid_terms = [e for e in visible
              if (e.get('deal_type') or '').startswith('Term ')
              and e.get('checked_claimed') is True]
cash_terms = sum(float(e['cash']) for e in paid_terms)

# What Khalil reads as "Cash collected" on the dashboard mentally:
cash_total = cash_main + cash_terms

# Revenue: MAIN ROWS ONLY (term children inherit revenue from their parent).
revenue = sum(float(e['revenue']) for e in main)

cash_per_call = cash_main / calls_taken if calls_taken else 0
```

> **Cash gotcha:** `/calendar` Cash KPI = `cash_main` only. `/meetings`
> shows `cash_main` and `cash_terms` as two separate cards — the
> "dashboard total" people read mentally is `cash_total`. KS-9's
> `kpi.py` returns all three (`cash_main`, `cash_terms`, `cash_total`).
> Pick the right one per context. Use `cash_total` for monthly pacing
> against the goal target Khalil set.

### Negatives

```python
negatives = no_shows + cancelled + rescheduled
neg_rate_per_taken  = negatives / calls_taken if calls_taken else 0
neg_rate_per_booked = negatives / booked      if booked      else 0
```

### Day-cell color thresholds (informational)

- Cash ≥ €15.000 → green, else red
- Revenue ≥ €20.000 → green, else red
- Close rate ≥ 70% → green
- AOV ≥ €4.000 → green
- Cash/Call ≥ €2.000 → green

These are for display only; the canonical numbers live in `goals` per-month.

## Common patterns

### "What did today look like?"

```python
today = "2026-04-29"
rows = sb.table("entries").select("*").eq("date", today).eq("hidden", False).execute()
```

### "Current month KPIs"

```python
rows = sb.table("entries").select("*") \
  .gte("date", "2026-04-01").lte("date", "2026-04-30") \
  .eq("hidden", False).execute()
goals = sb.table("goals").select("*").eq("month", "2026-04").maybe_single().execute()
```

### "Find a client"

```python
res = sb.table("entries").select("customer_name, phone, email, date, deal_type, program") \
  .ilike("customer_name", "%Aron%").eq("hidden", False).limit(20).execute()
```

### "Next 5 booked calls"

```python
today = "2026-04-29"
res = sb.table("entries").select("*") \
  .gte("date", today).is_("parent_entry_id", "null") \
  .eq("hidden", False) \
  .not_.in_("deal_type", ["Cancelled","Reschedule","No show"]) \
  .order("date").order("time").limit(5).execute()
```

## When numbers disagree

If your computed KPI doesn't match the app:

1. **`hidden`** — did you filter `hidden = false`?
2. **Strict main filter** — did you exclude `parent_entry_id IS NOT NULL`, **AND** `deal_type LIKE 'Term %'`, **AND** `deal_type = 'Start date'`? Just filtering on `parent_entry_id` is not enough — orphans exist.
3. **Pagination** — PostgREST defaults to **1000 rows**. For wider ranges add `.limit(10000)` or higher.
4. **Calls taken denominator** — did you subtract Unqualified along with cancelled/reschedule/no-show?
5. **Close rate** — did you use `(PIF+2T+3T+Deposit) / calls_taken` for the "incl. deposit" version?
6. **AOV** — closeish (incl. Deposit) for both numerator (sum revenue) and denominator (count)?
7. **Cash** — which one are you comparing?
   - `cash_main` matches `/calendar` Cash and `/meetings` "Cash Collected" card.
   - `cash_terms` matches `/meetings` "Terms collected" card.
   - `cash_total` is what people read off the dashboard mentally (the two cards summed).
8. **Revenue** — main rows only. Never sum term-children revenue (they inherit it from the parent).

The app is the source of truth. `kpi.py` mirrors it line-for-line.
