"""
intent_classifier.py
Keyword + category-mapping rule engine that infers purchase intent
from a deal object. Returns intent enum + confidence score.
"""

INTENT_KEYWORDS: dict[str, list[str]] = {
    "travel": [
        "flight", "hotel", "trip", "vacation", "airline", "travel",
        "booking", "tour", "cruise", "resort", "passport", "luggage",
        "itinerary", "destination", "airport",
    ],
    "electronics": [
        "phone", "laptop", "iphone", "macbook", "tablet", "gaming",
        "console", "camera", "headphones", "smartwatch", "tv",
        "monitor", "speaker", "earbuds", "keyboard", "mouse", "pc",
        "desktop", "airpods", "charger",
    ],
    "food": [
        "food", "meal", "dinner", "lunch", "breakfast", "restaurant",
        "delivery", "order", "grocery", "groceries", "zomato", "swiggy",
        "grab", "grabfood", "foodpanda", "deliveroo", "coupon", "takeaway",
    ],
    "fashion": [
        "clothing", "clothes", "jacket", "shirt", "dress", "shoes",
        "sneakers", "footwear", "fashion", "apparel", "outfit", "jeans",
        "bag", "handbag", "accessories", "jewellery", "watch", "luxury",
        "designer", "streetwear", "myntra", "zalora", "zara", "h&m",
    ],
    "health": [
        "supplement", "vitamin", "medical", "fitness", "gym", "yoga",
        "health", "medicine", "protein", "wellness", "nutrition",
        "pharmacy", "clinic", "skincare", "checkup", "diagnostics",
    ],
    "vehicle": [
        "car", "bike", "motorcycle", "scooter", "auto", "vehicle",
        "electric vehicle", "ev", "sedan", "suv", "van", "truck",
        "bicycle", "helmet",
    ],
    "home": [
        "furniture", "appliance", "refrigerator", "washing machine",
        "sofa", "bed", "mattress", "home", "kitchen", "dining",
        "wardrobe", "shelf", "lamp", "vacuum", "air conditioner",
    ],
}

# Exact category slug → intent mapping (catches labelled deal categories)
CATEGORY_SLUG_MAP: dict[str, str] = {
    "flights": "travel", "hotels": "travel", "packages": "travel",
    "travel": "travel", "tours": "travel",
    "mobiles": "electronics", "laptops": "electronics",
    "gadgets": "electronics", "computers": "electronics",
    "electronics": "electronics", "smartphones": "electronics",
    "food": "food", "food_delivery": "food", "delivery": "food",
    "restaurant": "food", "groceries": "food",
    "fashion": "fashion", "clothing": "fashion", "footwear": "fashion",
    "accessories": "fashion", "luxury": "fashion",
    "health": "health", "wellness": "health", "fitness": "health",
    "pharmacy": "health", "consultation": "health",
    "automotive": "vehicle", "vehicles": "vehicle", "cars": "vehicle",
    "bike": "vehicle",
    "furniture": "home", "appliances": "home", "home": "home",
    "kitchen": "home",
}


class IntentResult(dict):
    """Typed dict-like result for intent classification."""


def classify_intent(deal: dict) -> IntentResult:
    """
    Classify the purchase intent of a deal.

    Args:
        deal: dict with keys title, category, price, tags (list[str])

    Returns:
        IntentResult with 'intent', 'confidence', 'signals' keys.
    """
    text = " ".join(
        [
            deal.get("title", ""),
            deal.get("category", ""),
            " ".join(deal.get("tags", [])),
        ]
    ).lower()

    scores: dict[str, float] = {k: 0.0 for k in INTENT_KEYWORDS}
    signals: list[str] = []

    # --- Category slug fast-path (strong signal, weight 2.5) ---
    raw_cat = deal.get("category", "").lower().strip()
    if raw_cat in CATEGORY_SLUG_MAP:
        mapped = CATEGORY_SLUG_MAP[raw_cat]
        scores[mapped] += 2.5
        signals.append(f"category_slug:{raw_cat}")

    # --- Keyword scan ---
    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[intent] += 1.0
                signals.append(f"kw:{kw}")

    best_intent = max(scores, key=scores.get)
    best_score = scores[best_intent]

    if best_score == 0.0:
        return IntentResult(intent="general", confidence=0.50, signals=[])

    total = sum(scores.values()) or 1.0
    # Normalised confidence capped at 0.98
    confidence = round(min((best_score / total) + 0.25, 0.98), 2)

    return IntentResult(
        intent=best_intent,
        confidence=confidence,
        signals=signals[:6],
    )
