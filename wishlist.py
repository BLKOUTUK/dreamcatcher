"""
wishlist.py — access to Dreamcatcher's living wishlist + guardrails.

The document lives in Supabase (public.dreamcatcher_wishlist, single row id=1)
so board members can update it through the editor UI without touching the
code or redeploying. The Council fetches it fresh on every evaluation so
edits reshape future verdicts immediately.
"""

import os
from dataclasses import dataclass
from datetime import datetime

import httpx


@dataclass
class Wishlist:
    content: str
    updated_at: str
    updated_by: str | None

    @property
    def updated_at_human(self) -> str:
        try:
            dt = datetime.fromisoformat(self.updated_at.replace("Z", "+00:00"))
            return dt.strftime("%-d %B %Y, %H:%M UTC")
        except Exception:
            return self.updated_at


SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
TABLE = "dreamcatcher_wishlist"


def _headers() -> dict[str, str]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set for Dreamcatcher "
            "to read or write the wishlist."
        )
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def load_wishlist() -> Wishlist:
    """Fetch the current wishlist. Raises on any failure so the caller decides
    how to handle a missing document — we prefer loud over silent."""
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}?id=eq.1&select=content,updated_at,updated_by"
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, headers=_headers())
        resp.raise_for_status()
        rows = resp.json()
    if not rows:
        raise RuntimeError("Dreamcatcher wishlist row is missing from Supabase.")
    row = rows[0]
    return Wishlist(
        content=row["content"],
        updated_at=row["updated_at"],
        updated_by=row.get("updated_by"),
    )


def save_wishlist(content: str, updated_by: str | None = None) -> Wishlist:
    """Upsert the wishlist row. Returns the saved row so the caller can
    display the new updated_at immediately."""
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}?id=eq.1"
    payload = {
        "content": content,
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "updated_by": updated_by or "board",
    }
    with httpx.Client(timeout=10.0) as client:
        resp = client.patch(url, headers=_headers(), json=payload)
        resp.raise_for_status()
        rows = resp.json()
    if not rows:
        raise RuntimeError("Supabase accepted the update but returned no row.")
    row = rows[0]
    return Wishlist(
        content=row["content"],
        updated_at=row["updated_at"],
        updated_by=row.get("updated_by"),
    )
