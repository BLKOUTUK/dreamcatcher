"""
verdicts.py — persistence for Dreamcatcher Council evaluations.

Every /evaluate call stores one row in public.dreamcatcher_verdicts so the
history is attributable and the wishlist snapshot at the time of judgement
is preserved (the document can change later without invalidating the record).
"""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx


@dataclass
class Verdict:
    id: int
    url: str
    submitted_by: str | None
    skeptic_response: str
    ethicist_response: str
    builder_response: str
    skeptic_recommendation: str
    ethicist_recommendation: str
    builder_recommendation: str
    verdict: str
    wishlist_snapshot: str
    wishlist_updated_at: str | None
    council_model: str | None
    created_at: str

    @property
    def created_at_human(self) -> str:
        try:
            dt = datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
            return dt.strftime("%-d %b %Y · %H:%M UTC")
        except Exception:
            return self.created_at


SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
TABLE = "dreamcatcher_verdicts"


def _headers() -> dict[str, str]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set for Dreamcatcher "
            "to read or write verdict history."
        )
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _row_to_verdict(row: dict[str, Any]) -> Verdict:
    return Verdict(
        id=row["id"],
        url=row["url"],
        submitted_by=row.get("submitted_by"),
        skeptic_response=row["skeptic_response"],
        ethicist_response=row["ethicist_response"],
        builder_response=row["builder_response"],
        skeptic_recommendation=row["skeptic_recommendation"],
        ethicist_recommendation=row["ethicist_recommendation"],
        builder_recommendation=row["builder_recommendation"],
        verdict=row["verdict"],
        wishlist_snapshot=row.get("wishlist_snapshot", ""),
        wishlist_updated_at=row.get("wishlist_updated_at"),
        council_model=row.get("council_model"),
        created_at=row["created_at"],
    )


def save_verdict(
    *,
    url: str,
    submitted_by: str | None,
    skeptic_response: str,
    ethicist_response: str,
    builder_response: str,
    skeptic_recommendation: str,
    ethicist_recommendation: str,
    builder_recommendation: str,
    verdict: str,
    wishlist_snapshot: str,
    wishlist_updated_at: str | None,
    council_model: str | None,
) -> Verdict:
    payload = {
        "url": url,
        "submitted_by": submitted_by or None,
        "skeptic_response": skeptic_response,
        "ethicist_response": ethicist_response,
        "builder_response": builder_response,
        "skeptic_recommendation": skeptic_recommendation,
        "ethicist_recommendation": ethicist_recommendation,
        "builder_recommendation": builder_recommendation,
        "verdict": verdict,
        "wishlist_snapshot": wishlist_snapshot,
        "wishlist_updated_at": wishlist_updated_at,
        "council_model": council_model,
    }
    with httpx.Client(timeout=10.0) as client:
        resp = client.post(
            f"{SUPABASE_URL}/rest/v1/{TABLE}",
            headers=_headers(),
            json=payload,
        )
        resp.raise_for_status()
        rows = resp.json()
    if not rows:
        raise RuntimeError("Supabase accepted the verdict but returned no row.")
    return _row_to_verdict(rows[0])


def list_verdicts(
    *,
    limit: int = 50,
    verdict_filter: str | None = None,
) -> list[Verdict]:
    """List most recent verdicts. Excludes the large snapshot column to keep the payload small."""
    fields = (
        "id,url,submitted_by,verdict,"
        "skeptic_recommendation,ethicist_recommendation,builder_recommendation,"
        "wishlist_updated_at,council_model,created_at"
    )
    params = [
        f"select={fields}",
        f"order=created_at.desc",
        f"limit={limit}",
    ]
    if verdict_filter in ("GO", "HOLD", "PASS"):
        params.append(f"verdict=eq.{verdict_filter}")
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}?" + "&".join(params)
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, headers=_headers())
        resp.raise_for_status()
        rows = resp.json()
    return [
        Verdict(
            id=r["id"],
            url=r["url"],
            submitted_by=r.get("submitted_by"),
            skeptic_response="",
            ethicist_response="",
            builder_response="",
            skeptic_recommendation=r["skeptic_recommendation"],
            ethicist_recommendation=r["ethicist_recommendation"],
            builder_recommendation=r["builder_recommendation"],
            verdict=r["verdict"],
            wishlist_snapshot="",
            wishlist_updated_at=r.get("wishlist_updated_at"),
            council_model=r.get("council_model"),
            created_at=r["created_at"],
        )
        for r in rows
    ]


def get_verdict(verdict_id: int) -> Verdict | None:
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}?id=eq.{verdict_id}&select=*"
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, headers=_headers())
        resp.raise_for_status()
        rows = resp.json()
    if not rows:
        return None
    return _row_to_verdict(rows[0])


def verdict_counts() -> dict[str, int]:
    """Small summary used on the list page header."""
    counts = {"GO": 0, "HOLD": 0, "PASS": 0, "TOTAL": 0}
    with httpx.Client(timeout=10.0) as client:
        for v in ("GO", "HOLD", "PASS"):
            resp = client.get(
                f"{SUPABASE_URL}/rest/v1/{TABLE}?verdict=eq.{v}&select=id",
                headers={**_headers(), "Prefer": "count=exact"},
            )
            resp.raise_for_status()
            counts[v] = int(resp.headers.get("content-range", "0-0/0").split("/")[-1] or 0)
    counts["TOTAL"] = counts["GO"] + counts["HOLD"] + counts["PASS"]
    return counts
