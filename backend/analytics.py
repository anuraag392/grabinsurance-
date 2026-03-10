"""
analytics.py
SQL aggregation helpers for funnel metrics, revenue, product rankings, and time series.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Event, Recommendation


def get_funnel_summary(db: Session) -> dict:
    """Returns overall impression → click → accept funnel with CTR, CVR, revenue."""
    counts: dict[str, int] = {}
    for etype in ["impression", "click", "accept", "decline"]:
        counts[etype] = (
            db.query(func.count(Event.id))
            .filter(Event.event_type == etype)
            .scalar() or 0
        )

    impressions = counts["impression"] or 1
    total_revenue = (
        db.query(func.sum(Event.premium))
        .filter(Event.event_type == "accept")
        .scalar() or 0.0
    )

    return {
        "impressions": counts["impression"],
        "clicks": counts["click"],
        "accepts": counts["accept"],
        "declines": counts["decline"],
        "ctr": round(counts["click"] / impressions * 100, 2),
        "cvr": round(counts["accept"] / impressions * 100, 2),
        "total_revenue": round(float(total_revenue), 2),
    }


def get_revenue_by_category(db: Session) -> list[dict]:
    """Revenue and policy count grouped by insurance category."""
    rows = (
        db.query(
            Event.category,
            func.sum(Event.premium).label("revenue"),
            func.count(Event.id).label("policies"),
        )
        .filter(Event.event_type == "accept")
        .group_by(Event.category)
        .all()
    )
    return [
        {
            "category": r.category or "unknown",
            "revenue": round(float(r.revenue or 0), 2),
            "policies": r.policies,
        }
        for r in rows
    ]


def get_top_products(db: Session, limit: int = 8) -> list[dict]:
    """Most recommended products by recommendation count."""
    rows = (
        db.query(
            Recommendation.product_name,
            func.count(Recommendation.id).label("recommendations"),
        )
        .group_by(Recommendation.product_name)
        .order_by(func.count(Recommendation.id).desc())
        .limit(limit)
        .all()
    )
    return [{"product": r.product_name, "recommendations": r.recommendations} for r in rows]


def get_events_over_time(db: Session) -> list[dict]:
    """Daily event counts grouped by event_type for time-series charts."""
    rows = (
        db.query(
            func.date(Event.created_at).label("date"),
            Event.event_type,
            func.count(Event.id).label("count"),
        )
        .group_by(func.date(Event.created_at), Event.event_type)
        .order_by(func.date(Event.created_at))
        .all()
    )
    return [
        {"date": str(r.date), "event_type": r.event_type, "count": r.count}
        for r in rows
    ]
