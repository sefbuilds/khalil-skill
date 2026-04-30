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
