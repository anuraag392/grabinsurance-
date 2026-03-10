"""
pricing_engine.py
GrabInsurance – Dynamic Premium Pricing Engine

Formula:
    premium = deal_value × product.risk_multiplier × risk_tier_modifier

Risk tier modifiers:
    low    → 0.8  (cautious user, fewer claims historically)
    medium → 1.0  (baseline)
    high   → 1.3  (high-risk profile / high-value purchase)

Catalog constraints enforced:
    premium   ≥ product.min_premium          (floor from catalog)
    premium   ≤ product.max_coverage × 0.05  (hard ceiling: 5% of max payout)
    coverage  =  product.max_coverage        (fixed per product)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RiskTier = Literal["low", "medium", "high"]

RISK_TIER_MODIFIERS: dict[str, float] = {
    "low":    0.8,
    "medium": 1.0,
    "high":   1.3,
}

# Premium hard ceiling expressed as a fraction of max_coverage.
# Prevents absurd premiums on ultra-high-value deals.
PREMIUM_CEILING_RATIO = 0.05   # max premium = 5% of max payout

# Absolute fallback floor if catalog min_premium is missing
ABSOLUTE_FLOOR = 1.99

# ---------------------------------------------------------------------------
# Catalog loader (reads data/insurance_products.json)
# ---------------------------------------------------------------------------

_CATALOG_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "insurance_products.json"
)

_catalog_cache: list[dict] | None = None


def load_catalog() -> list[dict]:
    """Load and cache the insurance product catalog from JSON."""
    global _catalog_cache
    if _catalog_cache is None:
        with open(_CATALOG_PATH, encoding="utf-8") as f:
            _catalog_cache = json.load(f)
        logger.info("Loaded %d products from catalog.", len(_catalog_cache))
    return _catalog_cache


def get_product_by_name(name: str) -> dict | None:
    """Case-insensitive product lookup by name."""
    target = name.strip().lower()
    for p in load_catalog():
        if p.get("name", "").lower() == target:
            return p
    return None


def get_product_by_id(product_id: int) -> dict | None:
    """Product lookup by numeric ID."""
    for p in load_catalog():
        if p.get("id") == product_id:
            return p
    return None


# ---------------------------------------------------------------------------
# Core pricing dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PriceQuote:
    """Immutable pricing result returned from calculate_premium()."""

    product_id:         int
    product_name:       str
    product_category:   str
    deal_value:         float
    user_risk_tier:     str
    risk_multiplier:    float   # from product catalog
    tier_modifier:      float   # from user risk tier
    raw_premium:        float   # before clamping
    premium_price:      float   # final clamped value (what customer pays)
    coverage_amount:    float   # max payout from catalog
    min_premium:        float   # catalog floor applied
    currency:           str = "SGD"

    def to_dict(self) -> dict:
        return {
            "product":          self.product_name,
            "product_id":       self.product_id,
            "category":         self.product_category,
            "premium_price":    self.premium_price,
            "coverage_amount":  self.coverage_amount,
            "currency":         self.currency,
            "breakdown": {
                "deal_value":       self.deal_value,
                "risk_multiplier":  self.risk_multiplier,
                "tier_modifier":    self.tier_modifier,
                "raw_premium":      self.raw_premium,
                "min_premium":      self.min_premium,
                "ceiling_applied":  self.raw_premium > self.premium_price,
                "floor_applied":    self.raw_premium < self.premium_price,
            },
        }


# ---------------------------------------------------------------------------
# Main pricing function
# ---------------------------------------------------------------------------

class PricingError(ValueError):
    """Raised when pricing cannot be computed due to invalid inputs."""


def calculate_premium(
    deal_value: float,
    product: dict,
    user_risk_tier: RiskTier = "medium",
) -> PriceQuote:
    """
    Calculate the insurance premium for a given deal and product.

    Parameters
    ----------
    deal_value :     Purchase price of the deal (SGD). Must be > 0.
    product :        Product dict from catalog (requires: id, name, category,
                     risk_multiplier, min_premium, max_coverage).
    user_risk_tier : "low" | "medium" | "high". Defaults to "medium".

    Returns
    -------
    PriceQuote : Frozen dataclass with full pricing breakdown.

    Raises
    ------
    PricingError : If deal_value ≤ 0 or required product fields are missing.
    """

    # --- Input validation ---
    if deal_value is None or deal_value <= 0:
        raise PricingError(f"deal_value must be positive, got: {deal_value!r}")

    required_fields = ("id", "name", "category", "risk_multiplier", "min_premium", "max_coverage")
    missing = [f for f in required_fields if f not in product or product[f] is None]
    if missing:
        raise PricingError(f"Product is missing required fields: {missing}")

    tier = user_risk_tier.lower() if user_risk_tier else "medium"
    if tier not in RISK_TIER_MODIFIERS:
        logger.warning("Unknown risk tier %r — defaulting to 'medium'.", tier)
        tier = "medium"

    # --- Core formula ---
    risk_mult  = float(product["risk_multiplier"])
    tier_mod   = RISK_TIER_MODIFIERS[tier]
    raw        = round(deal_value * risk_mult * tier_mod, 4)

    # --- Catalog constraints ---
    min_prem   = float(product.get("min_premium", ABSOLUTE_FLOOR))
    max_prem   = round(float(product["max_coverage"]) * PREMIUM_CEILING_RATIO, 2)
    coverage   = float(product["max_coverage"])

    # Floor: never below catalog minimum
    # Ceiling: never more than PREMIUM_CEILING_RATIO of max coverage
    clamped = round(max(min_prem, min(raw, max_prem)), 2)

    logger.debug(
        "Premium calc: deal=%.2f × risk=%.2f × tier=%.2f → raw=%.2f → clamped=%.2f (floor=%.2f, ceil=%.2f)",
        deal_value, risk_mult, tier_mod, raw, clamped, min_prem, max_prem,
    )

    return PriceQuote(
        product_id=       product["id"],
        product_name=     product["name"],
        product_category= product["category"],
        deal_value=       deal_value,
        user_risk_tier=   tier,
        risk_multiplier=  risk_mult,
        tier_modifier=    tier_mod,
        raw_premium=      raw,
        premium_price=    clamped,
        coverage_amount=  coverage,
        min_premium=      min_prem,
    )


# ---------------------------------------------------------------------------
# Batch pricing (for multi-product quotes)
# ---------------------------------------------------------------------------

def calculate_bulk_quotes(
    deal_value: float,
    products: list[dict],
    user_risk_tier: RiskTier = "medium",
) -> list[PriceQuote]:
    """
    Calculate premiums for a list of products and return sorted by premium (ascending).
    Skips products that raise PricingError with a warning.
    """
    quotes: list[PriceQuote] = []
    for p in products:
        try:
            quotes.append(calculate_premium(deal_value, p, user_risk_tier))
        except PricingError as e:
            logger.warning("Skipping product %r: %s", p.get("name"), e)
    return sorted(quotes, key=lambda q: q.premium_price)


# ---------------------------------------------------------------------------
# CLI smoke-test (python pricing_engine.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json as _json

    catalog = load_catalog()
    print(f"Catalog loaded: {len(catalog)} products\n")

    test_cases = [
        ("Trip Cancellation Shield",         680.0,  "medium"),
        ("Screen Damage Cover",              1299.0,  "high"),
        ("Electronics Extended Warranty",    2499.0,  "low"),
        ("Personal Accident – Food Delivery",  22.5,  "high"),
        ("Health OPD Cover",                  45.0,  "medium"),
        ("Luxury Item Theft Guard",          3500.0,  "high"),
    ]

    for name, value, tier in test_cases:
        product = get_product_by_name(name)
        if not product:
            print(f"[SKIP] Product not found: {name}")
            continue
        quote = calculate_premium(value, product, tier)
        print(
            f"  {quote.product_name:<38} | deal=SGD {value:>7,.2f} | tier={tier:<6} "
            f"| premium=SGD {quote.premium_price:>7.2f} | coverage=SGD {quote.coverage_amount:>10,.0f}"
        )
