"""
Read-only Supabase client for KS-9.

Strict rules:
- Uses the ANON key only. Never the service-role key.
- Exposes a `read()` helper that returns a Supabase client.
- Anything that mutates (insert/update/delete/upsert/rpc with side-effects) is
  out of scope for this skill. If you need to write, build a separate skill
  with explicit confirmation flow.
"""

from __future__ import annotations

import os
from supabase import create_client, Client


_FORBIDDEN_KEY_HINTS = ("service_role", "service-role", "sbsk_")


def _read_env() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_ANON_KEY", "").strip()
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_ANON_KEY must be set. "
            "Use the anon key — never the service-role key."
        )
    # Defensive guard: refuse to run with a service-role key even if someone
    # accidentally puts it in SUPABASE_ANON_KEY.
    lowered = key.lower()
    for hint in _FORBIDDEN_KEY_HINTS:
        if hint in lowered:
            raise RuntimeError(
                "Refusing to run: SUPABASE_ANON_KEY looks like a service-role key. "
                "This skill is read-only by design."
            )
    return url, key


_client: Client | None = None


def read() -> Client:
    """Return a singleton Supabase client. Treat the result as read-only."""
    global _client
    if _client is None:
        url, key = _read_env()
        _client = create_client(url, key)
    return _client
