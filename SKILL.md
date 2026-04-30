---
name: custom-app-skill
description: "Read-only access to Khalil's sales tracker via Supabase. Use when user asks about pipeline, KPIs, today's calls, this month's performance, recent closes, a specific client, or how he's pacing vs goals. Also for daily briefings, weekly recaps, or pre-call context. Mirrors the data shown in https://khalilsarvari.vercel.app."
---

# custom-app-skill

This is your eyes into Khalil's sales tracker — the same data the app at https://khalilsarvari.vercel.app shows. **Read-only.** You never write through this skill.

## When to use

- "Hoe sta ik vandaag?" / "What's my day looking like?"
- "Hoeveel cash deze maand?" / "How am I pacing vs my targets?"
- "Wie heb ik morgen om 14:00?"
- "Wanneer was de laatste close?"
- "Heb ik een note bij Loek's call?"
- Pre-call lookup: pull the prospect's history before he dials in
- Heartbeat: check if today's pacing is off vs the monthly goal

## Configuration

Two env vars, both already public-safe (RLS allows read with the anon key):

```bash
export SUPABASE_URL="https://.supabase.co"
export SUPABASE_ANON_KEY=""
```

Khalil's project ref: see `TOOLS.md` in the workspace root.

Install deps once:

```bash
pip install -r requirements.txt
```

## Scripts

All scripts print human-readable text to stdout (or JSON with `--json`). Pipe them, parse them, or just read them.

| Script | What it does |
|---|---|
| `today.py` | Snapshot of today: calls booked/taken, closes, KPIs, day note, upcoming slots |
| `month.py [yyyy-MM]` | Full month KPIs vs goals (defaults to current month) |
| `upcoming.py [N]` | Next N scheduled calls with name/time/program (default 5) |
| `search.py <query>` | Search clients by name/phone/email |
| `recap.py [iso-week]` | Weekly recap: KPIs, closes, slumps (defaults to this week) |
| `day.py <yyyy-MM-dd>` | Detail of one specific day |

## How to read what comes back

The schema and KPI definitions are non-trivial. **Read [SCHEMA.md](SCHEMA.md) before interpreting raw rows.** Key gotchas:

- `entries.hidden = true` rows are soft-deleted; never count them.
- `entries.parent_entry_id` is non-null for **term children** (Term 2/3, Term 3/3, Start date follow-ups). They share cash but not revenue with the parent.
- "Calls taken" excludes Cancelled, Reschedule, No show, **and** Unqualified.
- Close rate counts Deposit as a close (matches app behavior).
- Cash on day cells = main-row cash only (no term roll-overs from other months).

## Examples

```bash
# What's today like?
python scripts/today.py

# How am I pacing this month vs goals?
python scripts/month.py

# Last week's recap
python scripts/recap.py

# Specific day
python scripts/day.py 2026-04-15

# Find a client
python scripts/search.py "Aron"

# Next 10 booked calls
python scripts/upcoming.py 10
```

## Permissions

- read-only Supabase via the anon key
- never write, never use the service role key

## Hard rules

- **Never** write. `client.py` only exposes a read-only client. Don't import the Supabase library directly to bypass it.
- **Never** print or log the anon key. Reference it via env only.
- Hidden rows (`hidden=true`) are excluded everywhere — do not undo this filter.
- If a number you compute disagrees with the app's `/calendar` for the same period, **the app wins.** Re-read [SCHEMA.md](SCHEMA.md) and `lib/kpi.py` to figure out where you went off. 
