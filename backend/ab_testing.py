"""
ab_testing.py
GrabInsurance – A/B Testing Engine

Assigns variants, tracks clicks and conversions, and provides analytics.
Uses Python's built-in sqlite3 — no ORM dependency required.

Schema (table: ab_sessions)
────────────────────────────
  session_id   TEXT PRIMARY KEY
  variant      TEXT  NOT NULL    – "A" | "B" | "C"
  deal_id      TEXT  NOT NULL
  timestamp    TEXT  NOT NULL    – ISO-8601 UTC
  clicked      INTEGER DEFAULT 0 – 0 or 1
  converted    INTEGER DEFAULT 0 – 0 or 1
  click_ts     TEXT              – ISO-8601 UTC, set on first click
  convert_ts   TEXT              – ISO-8601 UTC, set on conversion

Usage
─────
    from ab_testing import ABTesting

    ab = ABTesting()                           # uses default DB path
    variant = ab.assign_variant("sess_001", "deal_iphone16")
    ab.track_click("sess_001")
    ab.track_conversion("sess_001")

    print(ab.get_conversion_rate())            # {"A": 0.28, "B": 0.31, "C": 0.24}
    print(ab.get_click_rate())                 # {"A": 0.52, "B": 0.60, "C": 0.48}
    print(ab.get_best_variant())               # {"variant": "B", "conversion_rate": 0.31, ...}

Module-level convenience API (uses a shared default instance):
    from ab_testing import assign_variant, track_click, track_conversion
    from ab_testing import get_conversion_rate, get_click_rate, get_best_variant
"""

from __future__ import annotations

import logging
import random
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VARIANTS: list[str] = ["A", "B", "C"]

DEFAULT_DB_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "ab_testing.db"
)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS ab_sessions (
    session_id  TEXT PRIMARY KEY,
    variant     TEXT NOT NULL,
    deal_id     TEXT NOT NULL,
    timestamp   TEXT NOT NULL,
    clicked     INTEGER NOT NULL DEFAULT 0,
    converted   INTEGER NOT NULL DEFAULT 0,
    click_ts    TEXT,
    convert_ts  TEXT
);
"""

# ---------------------------------------------------------------------------
# Dataclass for a single AB session row
# ---------------------------------------------------------------------------

@dataclass
class ABSession:
    session_id: str
    variant:    str
    deal_id:    str
    timestamp:  str
    clicked:    bool = False
    converted:  bool = False
    click_ts:   str | None = None
    convert_ts: str | None = None

    @classmethod
    def from_row(cls, row: tuple) -> "ABSession":
        return cls(
            session_id = row[0],
            variant    = row[1],
            deal_id    = row[2],
            timestamp  = row[3],
            clicked    = bool(row[4]),
            converted  = bool(row[5]),
            click_ts   = row[6],
            convert_ts = row[7],
        )

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "variant":    self.variant,
            "deal_id":    self.deal_id,
            "timestamp":  self.timestamp,
            "click":      self.clicked,
            "conversion": self.converted,
            "click_ts":   self.click_ts,
            "convert_ts": self.convert_ts,
        }

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

# ---------------------------------------------------------------------------
# Core class
# ---------------------------------------------------------------------------

class ABTesting:
    """
    Thread-safe A/B testing engine backed by SQLite.

    Parameters
    ----------
    db_path : Path or str
        Path to the SQLite database file. Created automatically if absent.
    variants : list[str]
        Variant labels to assign. Default: ["A", "B", "C"].
    """

    def __init__(
        self,
        db_path: Path | str | None = None,
        variants: list[str] | None = None,
    ) -> None:
        self.db_path  = Path(db_path or DEFAULT_DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.variants = variants or VARIANTS
        self._lock    = threading.Lock()
        self._init_db()

    # ── DB init ────────────────────────────────────────────────────────────

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(_CREATE_TABLE)
            conn.commit()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # ── Variant assignment ─────────────────────────────────────────────────

    def assign_variant(self, session_id: str, deal_id: str) -> str:
        """
        Randomly assign a variant to a session and persist the record.

        If the session already exists, return its previously assigned variant
        without creating a duplicate row (idempotent).

        Parameters
        ----------
        session_id : Unique session identifier (e.g. UUID or user+timestamp hash)
        deal_id    : Deal or product identifier being tested

        Returns
        -------
        str – Assigned variant label ("A", "B", or "C")
        """
        with self._lock, self._connect() as conn:
            existing = conn.execute(
                "SELECT variant FROM ab_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()

            if existing:
                logger.debug("Session %s already assigned variant %s", session_id, existing[0])
                return existing[0]

            variant = random.choice(self.variants)
            conn.execute(
                """
                INSERT INTO ab_sessions (session_id, variant, deal_id, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, variant, deal_id, _utcnow()),
            )
            conn.commit()
            logger.info("Assigned variant %s to session %s (deal: %s)", variant, session_id, deal_id)
            return variant

    # ── Event tracking ─────────────────────────────────────────────────────

    def track_click(self, session_id: str) -> bool:
        """
        Record that a user clicked the insurance offer for this session.

        Idempotent — subsequent calls for the same session are no-ops.

        Returns True if the click was newly recorded, False if already tracked.
        """
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT clicked FROM ab_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()

            if row is None:
                logger.warning("track_click: session %s not found", session_id)
                return False

            if row["clicked"]:
                return False  # already recorded

            conn.execute(
                "UPDATE ab_sessions SET clicked = 1, click_ts = ? WHERE session_id = ?",
                (_utcnow(), session_id),
            )
            conn.commit()
            logger.debug("Click recorded for session %s", session_id)
            return True

    def track_conversion(self, session_id: str) -> bool:
        """
        Record that a user accepted the insurance offer (converted).

        Also marks the session as clicked if not already set (implicit click).
        Idempotent — subsequent calls are no-ops.

        Returns True if the conversion was newly recorded, False if already tracked.
        """
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT clicked, converted FROM ab_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()

            if row is None:
                logger.warning("track_conversion: session %s not found", session_id)
                return False

            if row["converted"]:
                return False  # already recorded

            now = _utcnow()
            conn.execute(
                """
                UPDATE ab_sessions
                SET converted = 1, convert_ts = ?,
                    clicked   = CASE WHEN clicked = 0 THEN 1 ELSE clicked END,
                    click_ts  = CASE WHEN click_ts IS NULL THEN ? ELSE click_ts END
                WHERE session_id = ?
                """,
                (now, now, session_id),
            )
            conn.commit()
            logger.debug("Conversion recorded for session %s", session_id)
            return True

    # ── Session retrieval ──────────────────────────────────────────────────

    def get_session(self, session_id: str) -> ABSession | None:
        """Retrieve a single session by ID."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM ab_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return ABSession.from_row(tuple(row)) if row else None

    def get_all_sessions(
        self,
        variant: str | None = None,
        deal_id: str | None = None,
    ) -> list[ABSession]:
        """
        Return all sessions, optionally filtered by variant or deal_id.
        """
        clauses, params = [], []
        if variant:
            clauses.append("variant = ?")
            params.append(variant.upper())
        if deal_id:
            clauses.append("deal_id = ?")
            params.append(deal_id)

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM ab_sessions {where} ORDER BY timestamp",
                params,
            ).fetchall()

        return [ABSession.from_row(tuple(r)) for r in rows]

    # ── Analytics ──────────────────────────────────────────────────────────

    def get_click_rate(
        self,
        variant: str | None = None,
    ) -> dict[str, float] | float:
        """
        Calculate the click-through rate (CTR): clicks ÷ impressions.

        Parameters
        ----------
        variant : If supplied, return a single float for that variant.
                  If None, return a dict mapping each variant → CTR.

        Returns
        -------
        float (single variant) or dict[str, float] (all variants)
        """
        if variant:
            return self._rate_for_variant(variant.upper(), "clicked")

        return {v: self._rate_for_variant(v, "clicked") for v in self.variants}

    def get_conversion_rate(
        self,
        variant: str | None = None,
    ) -> dict[str, float] | float:
        """
        Calculate the conversion rate (CVR): conversions ÷ impressions.

        Parameters
        ----------
        variant : If supplied, return a single float for that variant.
                  If None, return a dict mapping each variant → CVR.

        Returns
        -------
        float (single variant) or dict[str, float] (all variants)
        """
        if variant:
            return self._rate_for_variant(variant.upper(), "converted")

        return {v: self._rate_for_variant(v, "converted") for v in self.variants}

    def _rate_for_variant(self, variant: str, field: str) -> float:
        with self._connect() as conn:
            row = conn.execute(
                f"""
                SELECT
                    COUNT(*)                            AS total,
                    COALESCE(SUM({field}), 0)           AS events
                FROM ab_sessions
                WHERE variant = ?
                """,
                (variant,),
            ).fetchone()

        total  = row["total"]  if row else 0
        events = row["events"] if row else 0
        return round(events / total, 4) if total > 0 else 0.0

    def get_best_variant(self) -> dict:
        """
        Return the variant with the highest conversion rate.

        If two variants are tied, the one with the higher click rate wins.
        Returns a dict with full stats for the winning variant.

        Returns
        -------
        dict:
            {
                "variant":         str,
                "total_sessions":  int,
                "clicks":          int,
                "conversions":     int,
                "click_rate":      float,
                "conversion_rate": float,
                "is_significant":  bool,   # True if sample size > 30
            }
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    variant,
                    COUNT(*)        AS total,
                    SUM(clicked)    AS clicks,
                    SUM(converted)  AS conversions
                FROM  ab_sessions
                GROUP BY variant
                ORDER BY variant
                """,
            ).fetchall()

        if not rows:
            return {"error": "No sessions recorded yet."}

        stats = []
        for row in rows:
            total       = row["total"]       or 0
            clicks      = row["clicks"]      or 0
            conversions = row["conversions"] or 0
            stats.append({
                "variant":         row["variant"],
                "total_sessions":  total,
                "clicks":          clicks,
                "conversions":     conversions,
                "click_rate":      round(clicks / total,      4) if total else 0.0,
                "conversion_rate": round(conversions / total, 4) if total else 0.0,
                "is_significant":  total >= 30,
            })

        # Sort: primary = conversion_rate, tiebreak = click_rate
        best = sorted(
            stats,
            key=lambda s: (s["conversion_rate"], s["click_rate"]),
            reverse=True,
        )[0]

        return best

    def get_summary(self) -> dict:
        """
        Return a full summary of all variants with per-variant stats and a winner.

        Returns
        -------
        dict:
            {
                "total_sessions": int,
                "variants":       list[dict],   # per-variant stats
                "best_variant":   dict,
            }
        """
        with self._connect() as conn:
            total_sessions = conn.execute(
                "SELECT COUNT(*) FROM ab_sessions"
            ).fetchone()[0]

        variant_stats = []
        for v in self.variants:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    SELECT
                        COUNT(*)       AS total,
                        SUM(clicked)   AS clicks,
                        SUM(converted) AS conversions
                    FROM  ab_sessions
                    WHERE variant = ?
                    """,
                    (v,),
                ).fetchone()

            total       = row["total"]       or 0
            clicks      = row["clicks"]      or 0
            conversions = row["conversions"] or 0
            variant_stats.append({
                "variant":         v,
                "total_sessions":  total,
                "clicks":          clicks,
                "conversions":     conversions,
                "click_rate":      round(clicks / total,      4) if total else 0.0,
                "conversion_rate": round(conversions / total, 4) if total else 0.0,
            })

        return {
            "total_sessions": total_sessions,
            "variants":       variant_stats,
            "best_variant":   self.get_best_variant(),
        }

    def reset(self, variant: str | None = None) -> int:
        """
        Delete session data. If variant is specified, only deletes that variant.

        Returns
        -------
        int – number of rows deleted.
        """
        with self._lock, self._connect() as conn:
            if variant:
                cursor = conn.execute(
                    "DELETE FROM ab_sessions WHERE variant = ?", (variant.upper(),)
                )
            else:
                cursor = conn.execute("DELETE FROM ab_sessions")
            conn.commit()
            return cursor.rowcount


# ---------------------------------------------------------------------------
# Module-level convenience API (shared default instance)
# ---------------------------------------------------------------------------

_default: ABTesting | None = None

def _get_default() -> ABTesting:
    global _default
    if _default is None:
        _default = ABTesting()
    return _default


def assign_variant(session_id: str, deal_id: str) -> str:
    """Assign a variant using the default shared ABTesting instance."""
    return _get_default().assign_variant(session_id, deal_id)


def track_click(session_id: str) -> bool:
    """Track a click using the default shared ABTesting instance."""
    return _get_default().track_click(session_id)


def track_conversion(session_id: str) -> bool:
    """Track a conversion using the default shared ABTesting instance."""
    return _get_default().track_conversion(session_id)


def get_click_rate(variant: str | None = None) -> dict[str, float] | float:
    """Get click rates using the default shared ABTesting instance."""
    return _get_default().get_click_rate(variant)


def get_conversion_rate(variant: str | None = None) -> dict[str, float] | float:
    """Get conversion rates using the default shared ABTesting instance."""
    return _get_default().get_conversion_rate(variant)


def get_best_variant() -> dict:
    """Get the best-performing variant from the default shared ABTesting instance."""
    return _get_default().get_best_variant()


# ---------------------------------------------------------------------------
# SQLAlchemy-based helpers  (used by main.py analytics + event endpoints)
# ---------------------------------------------------------------------------

def track_event(
    db,
    user_id: str,
    recommendation_id: int,
    event_type: str,
    variant: str,
    category: str = "",
    premium: float | None = None,
) -> None:
    """
    Persist a user interaction event (impression/click/accept/decline)
    to the SQLAlchemy-backed `events` table.
    """
    from models import Event  # local import to avoid circular deps at module level
    event = Event(
        user_id=user_id,
        recommendation_id=recommendation_id,
        event_type=event_type,
        variant=variant,
        category=category,
        premium=premium if event_type == "accept" else None,
    )
    db.add(event)
    db.commit()


def get_ab_metrics(db) -> list[dict]:
    """
    Return per-variant A/B metrics from the `events` table:
    impressions, clicks, accepts, CTR, CVR, and revenue.
    """
    from sqlalchemy import func
    from models import Event  # local import

    variants = ["A", "B", "C"]
    results = []

    for variant in variants:
        impressions = (
            db.query(func.count(Event.id))
            .filter(Event.variant == variant, Event.event_type == "impression")
            .scalar() or 0
        )
        clicks = (
            db.query(func.count(Event.id))
            .filter(Event.variant == variant, Event.event_type == "click")
            .scalar() or 0
        )
        accepts = (
            db.query(func.count(Event.id))
            .filter(Event.variant == variant, Event.event_type == "accept")
            .scalar() or 0
        )
        revenue = (
            db.query(func.sum(Event.premium))
            .filter(Event.variant == variant, Event.event_type == "accept")
            .scalar() or 0.0
        )

        base = impressions or 1  # avoid division by zero
        results.append({
            "variant":     variant,
            "impressions": impressions,
            "clicks":      clicks,
            "accepts":     accepts,
            "ctr":         round(clicks  / base * 100, 2),
            "cvr":         round(accepts / base * 100, 2),
            "revenue":     round(float(revenue), 2),
        })

    return results


# ---------------------------------------------------------------------------
# CLI smoke test  (python ab_testing.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import tempfile, json, uuid

    print("GrabInsurance A/B Testing Engine – Smoke Test")
    print("=" * 50)

    # Use a temp DB so the test is isolated
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    ab = ABTesting(db_path=db_path)

    # Simulate 90 sessions with realistic funnel rates
    deals = ["deal_iphone16", "deal_bali_trip", "deal_gucci_bag"]
    sessions: list[tuple[str, str]] = []

    for i in range(90):
        sid = f"sess_{uuid.uuid4().hex[:8]}"
        did = random.choice(deals)
        variant = ab.assign_variant(sid, did)
        sessions.append((sid, variant))

    # Simulate click + conversion funnel (B slightly better)
    click_rate_by_variant    = {"A": 0.50, "B": 0.62, "C": 0.45}
    convert_rate_by_variant  = {"A": 0.25, "B": 0.33, "C": 0.20}

    for sid, variant in sessions:
        if random.random() < click_rate_by_variant.get(variant, 0.5):
            ab.track_click(sid)
        if random.random() < convert_rate_by_variant.get(variant, 0.25):
            ab.track_conversion(sid)

    # Results
    print("\n── Click Rates ──────────────────────────────")
    for v, rate in ab.get_click_rate().items():
        print(f"  Variant {v}:  {rate:.1%}")

    print("\n── Conversion Rates ─────────────────────────")
    for v, rate in ab.get_conversion_rate().items():
        print(f"  Variant {v}:  {rate:.1%}")

    print("\n── Best Variant ─────────────────────────────")
    print(json.dumps(ab.get_best_variant(), indent=2))

    print("\n── Full Summary ─────────────────────────────")
    summary = ab.get_summary()
    print(f"  Total sessions : {summary['total_sessions']}")
    for vs in summary["variants"]:
        print(f"  {vs['variant']}: {vs['total_sessions']} sessions | "
              f"CTR {vs['click_rate']:.1%} | CVR {vs['conversion_rate']:.1%}")

    # Cleanup
    Path(db_path).unlink(missing_ok=True)
    print("\nAll assertions passed ✓")
