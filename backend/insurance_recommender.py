"""
insurance_recommender.py
Maps classified purchase intent to relevant insurance products from the DB.
"""

from sqlalchemy.orm import Session
from models import InsuranceProduct

# Intent → preferred product category slugs (ordered by relevance)
INTENT_CATEGORY_MAP: dict[str, list[str]] = {
    "travel":      ["travel_cancellation", "travel_medical", "travel_baggage"],
    "electronics": ["device_protection", "extended_warranty", "theft_protection"],
    "food":        ["personal_accident", "food_guarantee", "device_protection"],
    "fashion":     ["purchase_protection", "theft_protection", "device_protection"],
    "health":      ["personal_accident", "critical_illness", "hospital_cash"],
    "vehicle":     ["vehicle_damage", "roadside_assistance", "theft_protection"],
    "home":        ["home_contents", "appliance_protection", "fire_damage"],
    "general":     ["personal_accident", "device_protection", "home_contents"],
}


def recommend_products(
    intent: str, db: Session, top_n: int = 3
) -> list[InsuranceProduct]:
    """
    Return up to top_n InsuranceProduct rows that best match the given intent.
    Prefers category ordering defined in INTENT_CATEGORY_MAP.
    Falls back to any products in DB if nothing matches.
    """
    preferred = INTENT_CATEGORY_MAP.get(intent, INTENT_CATEGORY_MAP["general"])
    results: list[InsuranceProduct] = []

    for cat in preferred:
        products = (
            db.query(InsuranceProduct)
            .filter(InsuranceProduct.category == cat)
            .limit(1)
            .all()
        )
        results.extend(products)
        if len(results) >= top_n:
            break

    # Fallback: any products
    if not results:
        results = db.query(InsuranceProduct).limit(top_n).all()

    return results[:top_n]
