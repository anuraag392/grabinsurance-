"""
classifier.py
GrabInsurance – Deal Intent Classifier

Classifies a deal object into one or more contextual micro-insurance product
recommendations using a three-layer pipeline:

  Layer 1 → Rule-based category mapping   (deterministic, high-precision)
  Layer 2 → Weighted multi-signal scoring  (merchant, subcategory, value, history)
  Layer 3 → Fallback rules                 (guarantees a non-empty result)

Usage
-----
    from classifier import classify_deal

    result = classify_deal({
        "merchant": "Singapore Airlines",
        "category": "flights",
        "subcategory": "international",
        "deal_value": 680.0,
        "user_history": ["travel", "electronics"],
    })
    # → { "recommended_products": [{"name": "...", "confidence": 0.91}, ...] }
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# All known product names (must match data/insurance_products.json)
class P:  # noqa: N801 – short alias for Product names used throughout
    TRIP_CANCEL   = "Trip Cancellation Shield"
    TRAVEL_MED    = "Travel Medical Emergency Cover"
    RETURN_JOURNEY = "Return Journey Protection"
    EXT_WARRANTY  = "Electronics Extended Warranty"
    SCREEN_DAMAGE = "Screen Damage Cover"
    PA_FOOD       = "Personal Accident – Food Delivery"
    FOOD_GUARANTEE = "Food Delivery Order Guarantee"
    HEALTH_OPD    = "Health OPD Cover"
    PURCHASE_PROT = "Purchase Protection"
    LUXURY_THEFT  = "Luxury Item Theft Guard"


# ---------------------------------------------------------------------------
# Layer 1 – Rule-based category → product map
# Each entry maps a normalised category slug to a list of (product, base_score).
# ---------------------------------------------------------------------------

CATEGORY_RULES: dict[str, list[tuple[str, float]]] = {
    # Travel
    "travel":      [(P.TRIP_CANCEL, 0.90), (P.TRAVEL_MED, 0.80), (P.RETURN_JOURNEY, 0.65)],
    "flights":     [(P.TRIP_CANCEL, 0.95), (P.TRAVEL_MED, 0.85), (P.RETURN_JOURNEY, 0.70)],
    "hotels":      [(P.TRIP_CANCEL, 0.75), (P.RETURN_JOURNEY, 0.70)],
    "packages":    [(P.TRIP_CANCEL, 0.90), (P.TRAVEL_MED, 0.80), (P.RETURN_JOURNEY, 0.60)],
    "tours":       [(P.TRIP_CANCEL, 0.85), (P.TRAVEL_MED, 0.70)],
    # Electronics
    "electronics": [(P.EXT_WARRANTY, 0.85), (P.SCREEN_DAMAGE, 0.75)],
    "mobiles":     [(P.SCREEN_DAMAGE, 0.92), (P.EXT_WARRANTY, 0.80)],
    "smartphones": [(P.SCREEN_DAMAGE, 0.92), (P.EXT_WARRANTY, 0.80)],
    "laptops":     [(P.EXT_WARRANTY, 0.90), (P.SCREEN_DAMAGE, 0.60)],
    "gadgets":     [(P.EXT_WARRANTY, 0.80), (P.SCREEN_DAMAGE, 0.70)],
    "computers":   [(P.EXT_WARRANTY, 0.85), (P.SCREEN_DAMAGE, 0.55)],
    # Food / Food Delivery
    "food":         [(P.PA_FOOD, 0.80), (P.FOOD_GUARANTEE, 0.75)],
    "food_delivery":[(P.PA_FOOD, 0.95), (P.FOOD_GUARANTEE, 0.85)],
    "delivery":     [(P.PA_FOOD, 0.88), (P.FOOD_GUARANTEE, 0.80)],
    "restaurant":   [(P.FOOD_GUARANTEE, 0.70)],
    # Health / Wellness
    "health":      [(P.HEALTH_OPD, 0.92)],
    "wellness":    [(P.HEALTH_OPD, 0.80)],
    "pharmacy":    [(P.HEALTH_OPD, 0.88)],
    "fitness":     [(P.HEALTH_OPD, 0.65)],
    # Fashion
    "fashion":     [(P.PURCHASE_PROT, 0.85), (P.LUXURY_THEFT, 0.60)],
    "luxury":      [(P.LUXURY_THEFT, 0.92), (P.PURCHASE_PROT, 0.70)],
    "clothing":    [(P.PURCHASE_PROT, 0.80)],
    "accessories": [(P.PURCHASE_PROT, 0.75), (P.LUXURY_THEFT, 0.55)],
    "footwear":    [(P.PURCHASE_PROT, 0.72)],
}

# ---------------------------------------------------------------------------
# Layer 2 – Weighted scoring signals
# ---------------------------------------------------------------------------

# Subcategory → per-product additive boosts (stacked on top of category score)
SUBCATEGORY_BOOSTS: dict[str, dict[str, float]] = {
    "international":  {P.TRAVEL_MED: 0.20, P.TRIP_CANCEL: 0.15},
    "domestic":       {P.TRIP_CANCEL: 0.10, P.RETURN_JOURNEY: 0.15},
    "last_minute":    {P.TRIP_CANCEL: 0.20},
    "budget":         {P.TRIP_CANCEL: 0.10},
    "business_class": {P.TRAVEL_MED: 0.15, P.TRIP_CANCEL: 0.10},
    "smartphone":     {P.SCREEN_DAMAGE: 0.25, P.EXT_WARRANTY: 0.10},
    "tablet":         {P.SCREEN_DAMAGE: 0.20, P.EXT_WARRANTY: 0.15},
    "laptop":         {P.EXT_WARRANTY: 0.25, P.SCREEN_DAMAGE: 0.10},
    "wearable":       {P.SCREEN_DAMAGE: 0.15, P.EXT_WARRANTY: 0.15},
    "on_demand":      {P.PA_FOOD: 0.25, P.FOOD_GUARANTEE: 0.20},
    "scheduled":      {P.FOOD_GUARANTEE: 0.20},
    "prescription":   {P.HEALTH_OPD: 0.30},
    "consultation":   {P.HEALTH_OPD: 0.25},
    "supplement":     {P.HEALTH_OPD: 0.15},
    "designer":       {P.LUXURY_THEFT: 0.30, P.PURCHASE_PROT: 0.15},
    "streetwear":     {P.PURCHASE_PROT: 0.20},
    "vintage":        {P.LUXURY_THEFT: 0.20, P.PURCHASE_PROT: 0.20},
}

# Merchant keyword → per-product additive boosts
MERCHANT_SIGNALS: dict[str, dict[str, float]] = {
    # Travel merchants
    "airlines":       {P.TRIP_CANCEL: 0.20, P.TRAVEL_MED: 0.15},
    "airline":        {P.TRIP_CANCEL: 0.20, P.TRAVEL_MED: 0.15},
    "airways":        {P.TRIP_CANCEL: 0.20, P.TRAVEL_MED: 0.15},
    "hotel":          {P.TRIP_CANCEL: 0.15, P.RETURN_JOURNEY: 0.10},
    "resort":         {P.TRIP_CANCEL: 0.15, P.TRAVEL_MED: 0.10},
    "airbnb":         {P.TRIP_CANCEL: 0.15},
    "agoda":          {P.TRIP_CANCEL: 0.15, P.RETURN_JOURNEY: 0.10},
    "booking.com":    {P.TRIP_CANCEL: 0.15, P.RETURN_JOURNEY: 0.10},
    "klook":          {P.TRIP_CANCEL: 0.10, P.TRAVEL_MED: 0.10},
    "expedia":        {P.TRIP_CANCEL: 0.20, P.TRAVEL_MED: 0.15},
    # Electronics merchants
    "apple":          {P.SCREEN_DAMAGE: 0.25, P.EXT_WARRANTY: 0.20},
    "samsung":        {P.SCREEN_DAMAGE: 0.20, P.EXT_WARRANTY: 0.15},
    "dell":           {P.EXT_WARRANTY: 0.25, P.SCREEN_DAMAGE: 0.10},
    "lenovo":         {P.EXT_WARRANTY: 0.25, P.SCREEN_DAMAGE: 0.10},
    "sony":           {P.EXT_WARRANTY: 0.20, P.SCREEN_DAMAGE: 0.15},
    "dyson":          {P.EXT_WARRANTY: 0.20},
    # Food delivery
    "grab":           {P.PA_FOOD: 0.30, P.FOOD_GUARANTEE: 0.25},
    "grabfood":       {P.PA_FOOD: 0.35, P.FOOD_GUARANTEE: 0.30},
    "foodpanda":      {P.PA_FOOD: 0.30, P.FOOD_GUARANTEE: 0.30},
    "deliveroo":      {P.PA_FOOD: 0.25, P.FOOD_GUARANTEE: 0.25},
    "mcdonalds":      {P.FOOD_GUARANTEE: 0.20},
    # Health
    "guardian":       {P.HEALTH_OPD: 0.30},
    "watsons":        {P.HEALTH_OPD: 0.25},
    "parkway":        {P.HEALTH_OPD: 0.35},
    "raffles":        {P.HEALTH_OPD: 0.35},
    "ntuc":           {P.HEALTH_OPD: 0.15},
    # Fashion / Luxury
    "louis vuitton":  {P.LUXURY_THEFT: 0.40, P.PURCHASE_PROT: 0.20},
    "gucci":          {P.LUXURY_THEFT: 0.40, P.PURCHASE_PROT: 0.20},
    "prada":          {P.LUXURY_THEFT: 0.40},
    "hermes":         {P.LUXURY_THEFT: 0.45},
    "zara":           {P.PURCHASE_PROT: 0.25},
    "h&m":            {P.PURCHASE_PROT: 0.20},
    "uniqlo":         {P.PURCHASE_PROT: 0.20},
    "zalora":         {P.PURCHASE_PROT: 0.25, P.LUXURY_THEFT: 0.10},
    "shopee":         {P.PURCHASE_PROT: 0.15},
    "lazada":         {P.PURCHASE_PROT: 0.15, P.EXT_WARRANTY: 0.10},
}

# Deal value brackets → per-product boosts
DEAL_VALUE_RULES: list[tuple[float, float, dict[str, float]]] = [
    # (min_value, max_value, {product: boost})
    (0,     50,     {P.FOOD_GUARANTEE: 0.20, P.PURCHASE_PROT: 0.10}),
    (50,    200,    {P.SCREEN_DAMAGE: 0.15, P.PURCHASE_PROT: 0.15}),
    (200,   800,    {P.SCREEN_DAMAGE: 0.20, P.EXT_WARRANTY: 0.15, P.PURCHASE_PROT: 0.15}),
    (800,   2000,   {P.EXT_WARRANTY: 0.25, P.SCREEN_DAMAGE: 0.20, P.TRIP_CANCEL: 0.15}),
    (2000,  5000,   {P.EXT_WARRANTY: 0.30, P.TRIP_CANCEL: 0.20, P.LUXURY_THEFT: 0.15}),
    (5000,  math.inf, {P.LUXURY_THEFT: 0.30, P.TRIP_CANCEL: 0.25, P.TRAVEL_MED: 0.20}),
]

# User history category → products to boost based on past behaviour
HISTORY_AFFINITY: dict[str, dict[str, float]] = {
    "travel":      {P.TRIP_CANCEL: 0.15, P.TRAVEL_MED: 0.10},
    "flights":     {P.TRIP_CANCEL: 0.15, P.TRAVEL_MED: 0.12},
    "electronics": {P.EXT_WARRANTY: 0.12, P.SCREEN_DAMAGE: 0.10},
    "food":        {P.PA_FOOD: 0.12, P.FOOD_GUARANTEE: 0.10},
    "health":      {P.HEALTH_OPD: 0.15},
    "fashion":     {P.PURCHASE_PROT: 0.12, P.LUXURY_THEFT: 0.08},
    "luxury":      {P.LUXURY_THEFT: 0.15},
}

# Layer 3 – Fallback products when no category matches (ordered by popularity)
FALLBACK_PRODUCTS: list[tuple[str, float]] = [
    (P.PURCHASE_PROT, 0.45),
    (P.PA_FOOD,       0.35),
    (P.EXT_WARRANTY,  0.30),
]

# Minimum confidence threshold — recommendations below this are suppressed
MIN_CONFIDENCE = 0.30

# Maximum recommendations returned
MAX_RECOMMENDATIONS = 5


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ProductScore:
    name:  str
    score: float = 0.0
    signals: list[str] = field(default_factory=list)

    def add(self, value: float, label: str) -> None:
        if value != 0.0:
            self.score += value
            self.signals.append(f"{label}={value:+.2f}")


@dataclass
class ClassificationResult:
    recommended_products: list[dict]
    intent_category:      str
    is_ambiguous:         bool
    is_multi_category:    bool
    missing_fields:       list[str]
    debug_signals:        dict[str, list[str]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Input normalisation helpers
# ---------------------------------------------------------------------------

def _normalise_str(value: Any, default: str = "") -> str:
    """Coerce to lowercase stripped string or return default."""
    if value is None:
        return default
    return str(value).lower().strip()


def _normalise_categories(raw: Any) -> list[str]:
    """Accept str, list[str], or None. Returns list of normalised slugs."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return [_normalise_str(c) for c in raw if c]
    return [_normalise_str(raw)]


def _validate_deal(deal: dict) -> tuple[dict, list[str]]:
    """
    Validate and sanitise the incoming deal object.

    Returns:
        (sanitised_deal, list_of_missing_field_names)
    """
    missing: list[str] = []
    sanitised: dict = {}

    sanitised["merchant"]    = _normalise_str(deal.get("merchant"))
    sanitised["categories"]  = _normalise_categories(deal.get("category"))
    sanitised["subcategory"] = _normalise_str(deal.get("subcategory"))
    sanitised["deal_value"]  = float(deal.get("deal_value") or 0.0)
    sanitised["user_history"] = [
        _normalise_str(h) for h in (deal.get("user_history") or []) if h
    ]

    if not sanitised["merchant"]:
        missing.append("merchant")
    if not sanitised["categories"]:
        missing.append("category")
    if sanitised["deal_value"] <= 0:
        missing.append("deal_value")

    return sanitised, missing


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _build_score_map() -> dict[str, ProductScore]:
    """Create a fresh zeroed score entry for every known product."""
    all_products = [
        P.TRIP_CANCEL, P.TRAVEL_MED, P.RETURN_JOURNEY,
        P.EXT_WARRANTY, P.SCREEN_DAMAGE,
        P.PA_FOOD, P.FOOD_GUARANTEE,
        P.HEALTH_OPD,
        P.PURCHASE_PROT, P.LUXURY_THEFT,
    ]
    return {name: ProductScore(name=name) for name in all_products}


def _apply_category_rules(scores: dict[str, ProductScore], categories: list[str]) -> str:
    """
    Layer 1: Apply deterministic rule-based scores.

    Returns the primary detected intent category (most common among matched rules).
    """
    intent_hits: dict[str, int] = {}
    INTENT_PARENT = {
        "travel": "travel", "flights": "travel", "hotels": "travel",
        "packages": "travel", "tours": "travel",
        "electronics": "electronics", "mobiles": "electronics",
        "smartphones": "electronics", "laptops": "electronics",
        "gadgets": "electronics", "computers": "electronics",
        "food": "food", "food_delivery": "food", "delivery": "food",
        "restaurant": "food",
        "health": "health", "wellness": "health", "pharmacy": "health",
        "fitness": "health",
        "fashion": "fashion", "luxury": "fashion", "clothing": "fashion",
        "accessories": "fashion", "footwear": "fashion",
    }

    for cat in categories:
        rules = CATEGORY_RULES.get(cat)
        if rules:
            parent = INTENT_PARENT.get(cat, cat)
            intent_hits[parent] = intent_hits.get(parent, 0) + 1
            for product_name, base_score in rules:
                if product_name in scores:
                    scores[product_name].add(base_score, f"cat:{cat}")

    # Return dominant intent or "unknown"
    if not intent_hits:
        return "unknown"
    return max(intent_hits, key=intent_hits.get)


def _apply_subcategory_boosts(scores: dict[str, ProductScore], subcategory: str) -> None:
    """Layer 2a: Subcategory-specific additive boosts."""
    boosts = SUBCATEGORY_BOOSTS.get(subcategory, {})
    for product_name, boost in boosts.items():
        if product_name in scores:
            scores[product_name].add(boost, f"sub:{subcategory}")


def _apply_merchant_signals(scores: dict[str, ProductScore], merchant: str) -> None:
    """Layer 2b: Merchant keyword matching (checks for any partial token match)."""
    merchant_tokens = merchant.split()
    for token in merchant_tokens:
        # Exact or partial match against known merchant keys
        for key, boosts in MERCHANT_SIGNALS.items():
            if token in key or key in merchant:
                for product_name, boost in boosts.items():
                    if product_name in scores:
                        scores[product_name].add(boost, f"merchant:{key}")
                break  # one match per token is enough


def _apply_deal_value_rules(scores: dict[str, ProductScore], deal_value: float) -> None:
    """Layer 2c: Deal price bracket boosts."""
    for min_v, max_v, boosts in DEAL_VALUE_RULES:
        if min_v <= deal_value < max_v:
            for product_name, boost in boosts.items():
                if product_name in scores:
                    scores[product_name].add(boost, f"value:[{min_v},{max_v})")
            break


def _apply_user_history(scores: dict[str, ProductScore], user_history: list[str]) -> None:
    """Layer 2d: Personalisation from past purchase category history."""
    seen: set[str] = set()  # deduplicate per history entry
    for past_cat in user_history:
        if past_cat in seen:
            continue
        seen.add(past_cat)
        boosts = HISTORY_AFFINITY.get(past_cat, {})
        for product_name, boost in boosts.items():
            if product_name in scores:
                scores[product_name].add(boost, f"history:{past_cat}")


def _apply_fallback(scores: dict[str, ProductScore]) -> None:
    """
    Layer 3: If no product has a meaningful score, inject fallback recommendations
    to guarantee a non-empty result.
    """
    if all(ps.score == 0.0 for ps in scores.values()):
        logger.warning("No category rules matched — applying fallback recommendations.")
        for product_name, base_score in FALLBACK_PRODUCTS:
            if product_name in scores:
                scores[product_name].add(base_score, "fallback")


# ---------------------------------------------------------------------------
# Confidence normalisation
# ---------------------------------------------------------------------------

def _normalise_confidence(scores: dict[str, ProductScore]) -> list[dict]:
    """
    Convert raw additive scores to confidence values in [0, 1].

    Strategy:
      - Sort by score descending
      - Cap the top score at 1.0
      - Scale all others proportionally
      - Filter below MIN_CONFIDENCE threshold
      - Return top MAX_RECOMMENDATIONS entries
    """
    ranked = sorted(scores.values(), key=lambda ps: ps.score, reverse=True)
    top_score = ranked[0].score if ranked else 0.0

    if top_score == 0.0:
        return []

    results = []
    for ps in ranked:
        confidence = round(min(ps.score / top_score, 1.0), 3)
        if confidence < MIN_CONFIDENCE:
            break  # already sorted, no need to continue
        results.append({
            "name":       ps.name,
            "confidence": confidence,
        })
        if len(results) >= MAX_RECOMMENDATIONS:
            break

    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_deal(deal: dict) -> dict:
    """
    Classify a deal object and return ranked micro-insurance recommendations.

    Parameters
    ----------
    deal : dict
        {
            "merchant":     str | None,
            "category":     str | list[str] | None,   # supports multi-category cart
            "subcategory":  str | None,
            "deal_value":   float | int | None,
            "user_history": list[str] | None,
        }

    Returns
    -------
    dict
        {
            "recommended_products": [{"name": str, "confidence": float}, ...],
            "intent_category":      str,
            "is_ambiguous":         bool,
            "is_multi_category":    bool,
            "missing_fields":       list[str],
        }

    Edge Cases Handled
    ------------------
    - Missing or None fields:        validated and defaulted; flagged in missing_fields
    - Ambiguous category:            multiple partial scores → multi-product output
    - Multi-category cart (list):    all categories scored together
    - Unknown merchant/category:     falls through to Layer 3 fallback
    - Extremely low deal values:     value-bracket rules handle gracefully
    """
    # --- Input validation ---
    if not isinstance(deal, dict):
        logger.error("classify_deal received non-dict input: %s", type(deal))
        return {
            "recommended_products": [],
            "intent_category": "unknown",
            "is_ambiguous": False,
            "is_multi_category": False,
            "missing_fields": ["deal"],
        }

    sanitised, missing_fields = _validate_deal(deal)

    if missing_fields:
        logger.warning("classify_deal: missing fields %s", missing_fields)

    categories    = sanitised["categories"]
    subcategory   = sanitised["subcategory"]
    merchant      = sanitised["merchant"]
    deal_value    = sanitised["deal_value"]
    user_history  = sanitised["user_history"]

    is_multi_category = len(categories) > 1

    # --- Build score map ---
    scores = _build_score_map()

    # --- Layer 1: Rule-based mapping ---
    intent_category = _apply_category_rules(scores, categories)

    # --- Layer 2: Weighted signals ---
    if subcategory:
        _apply_subcategory_boosts(scores, subcategory)

    if merchant:
        _apply_merchant_signals(scores, merchant)

    if deal_value > 0:
        _apply_deal_value_rules(scores, deal_value)

    if user_history:
        _apply_user_history(scores, user_history)

    # --- Layer 3: Fallback ---
    _apply_fallback(scores)

    # --- Normalise to [0, 1] confidence ---
    recommended = _normalise_confidence(scores)

    # Ambiguous if top two products have confidence within 15pp of each other
    is_ambiguous = (
        len(recommended) >= 2
        and (recommended[0]["confidence"] - recommended[1]["confidence"]) < 0.15
    )

    result: dict = {
        "recommended_products": recommended,
        "intent_category":      intent_category,
        "is_ambiguous":         is_ambiguous,
        "is_multi_category":    is_multi_category,
        "missing_fields":       missing_fields,
    }

    logger.debug(
        "classify_deal → intent=%s ambiguous=%s products=%d",
        intent_category, is_ambiguous, len(recommended),
    )

    return result


# ---------------------------------------------------------------------------
# CLI smoke-test (python classifier.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json

    test_cases = [
        {
            "label": "Travel deal (clear)",
            "deal": {
                "merchant": "Singapore Airlines",
                "category": "flights",
                "subcategory": "international",
                "deal_value": 680.0,
                "user_history": ["travel", "hotels"],
            },
        },
        {
            "label": "Electronics deal (high value)",
            "deal": {
                "merchant": "Apple Store",
                "category": "mobiles",
                "subcategory": "smartphone",
                "deal_value": 1299.0,
                "user_history": ["electronics"],
            },
        },
        {
            "label": "Food delivery (GrabFood)",
            "deal": {
                "merchant": "GrabFood",
                "category": "food_delivery",
                "subcategory": "on_demand",
                "deal_value": 22.50,
                "user_history": [],
            },
        },
        {
            "label": "Health pharmacy purchase",
            "deal": {
                "merchant": "Guardian",
                "category": "pharmacy",
                "subcategory": "prescription",
                "deal_value": 45.0,
                "user_history": ["health"],
            },
        },
        {
            "label": "Luxury fashion – ambiguous",
            "deal": {
                "merchant": "Zalora",
                "category": ["fashion", "accessories"],
                "subcategory": "designer",
                "deal_value": 850.0,
                "user_history": ["fashion", "luxury"],
            },
        },
        {
            "label": "Edge case – missing fields",
            "deal": {
                "merchant": None,
                "category": None,
                "deal_value": 0,
                "user_history": None,
            },
        },
        {
            "label": "Edge case – unknown category",
            "deal": {
                "merchant": "Random Shop",
                "category": "stationery",
                "subcategory": "pens",
                "deal_value": 12.0,
                "user_history": [],
            },
        },
    ]

    for tc in test_cases:
        result = classify_deal(tc["deal"])
        print(f"\n{'='*60}")
        print(f"  {tc['label']}")
        print(f"{'='*60}")
        print(json.dumps(result, indent=2))
