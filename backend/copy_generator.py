"""
copy_generator.py
GrabInsurance – Mock Insurance Offer Copy Generator

Simulates Claude-generated contextual insurance offer messages without
using any external APIs. Uses curated template pools with category-aware
personalisation and random selection to simulate LLM-style variability.

Function
--------
    generate_offer_copy(deal_name, merchant, deal_value, insurance_product, premium)

Returns 3 shuffled variant dicts:
    Variant A – Urgency-driven   (FOMO, time pressure, risk framing)
    Variant B – Value-driven     (ROI, savings, coverage-to-premium ratio)
    Variant C – Reassurance-driven (peace of mind, trust, simplicity)

Each message:
    • is under 160 characters
    • mentions the deal value and premium
    • is contextual to the product category
"""

from __future__ import annotations

import random
import textwrap
from dataclasses import dataclass
from typing import Literal

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

VariantType = Literal["urgency", "value", "reassurance"]

VARIANT_LABELS = {
    "urgency":     "A",
    "value":       "B",
    "reassurance": "C",
}

# ---------------------------------------------------------------------------
# Helper: currency formatter
# ---------------------------------------------------------------------------

def _fmt(amount: float, currency: str = "SGD") -> str:
    """Format a monetary amount: SGD 1,299 or SGD 8.99"""
    if amount == int(amount):
        return f"{currency} {int(amount):,}"
    return f"{currency} {amount:,.2f}"


# ---------------------------------------------------------------------------
# Template pools
# Three pools per variant type, each pool is a list of format strings.
# Available slots: {deal_name}, {merchant}, {deal_value}, {premium},
#                  {product}, {coverage}
# ---------------------------------------------------------------------------

# ── Urgency (Variant A) ────────────────────────────────────────────────────
_URGENCY_GENERIC = [
    "Don't risk your {deal_value} purchase. Add protection for just {premium}. One tap, instant cover.",
    "Your {deal_value} order is unprotected. Secure it now for {premium}—takes seconds.",
    "Accidents happen. Cover your {deal_value} {deal_name} for only {premium} before you check out.",
    "One claim pays for years of cover. Protect your {deal_value} deal for just {premium} today.",
    "You're {deal_value} in. Don't lose it all—add {product} for {premium} now.",
    "Once you check out, this offer expires. Protect {deal_name} for {premium}.",
    "Your {deal_value} investment is at risk. {product} is available for {premium}—act now.",
]

_URGENCY_BY_CATEGORY: dict[str, list[str]] = {
    "travel": [
        "Flights cancel. Hotels happen. Don't lose your {deal_value} trip—add cover for {premium}.",
        "Your {deal_value} trip to {merchant} isn't guaranteed. Cover cancellations for {premium}.",
        "Travel plans change. Protect your {deal_value} booking today for just {premium}.",
        "One illness could cancel your {deal_value} trip. Shield it for only {premium}.",
    ],
    "electronics": [
        "One drop could cost you {deal_value}. Screen cover for your {deal_name} starts at {premium}.",
        "Accidents and theft happen on day one. Protect your {deal_value} device for {premium}.",
        "Your {deal_value} {deal_name} has no screen cover—add it now for {premium}.",
        "Repair costs > {deal_value}? Protect your device today for just {premium}.",
    ],
    "food": [
        "Delivering in traffic is risky. Protect against accidents for just {premium}.",
        "One bad delivery could cost more than {deal_value}. Get cover now for {premium}.",
        "Your {deal_value} order isn't guaranteed. Add delivery protection for {premium}.",
    ],
    "health": [
        "Clinic fees add up fast. OPD cover for your {deal_value} plan starts at {premium}.",
        "Don't gamble on your health. Add outpatient cover for {premium} right now.",
        "A single consultation can exceed {deal_value}. Protect yourself for {premium}.",
    ],
    "fashion": [
        "Your {deal_value} {deal_name} is one spill away from a loss. Cover it for {premium}.",
        "Theft happens. Protect your {deal_value} purchase for only {premium} today.",
        "Once damaged, {deal_name} loses value fast. Insure it now for just {premium}.",
    ],
}

# ── Value (Variant B) ──────────────────────────────────────────────────────
_VALUE_GENERIC = [
    "For just {premium}, protect your {deal_value} {deal_name}—that's less than a cup of coffee.",
    "{premium} covers up to {coverage}. On a {deal_value} purchase, the maths makes sense.",
    "Spend {premium} today, protect {deal_value}. {product} gives you {coverage} coverage.",
    "{deal_value} item, {premium} premium, {coverage} covered. That's {ratio}× your money working for you.",
    "Compare: {premium} insurance vs. {deal_value} full replacement. The choice is clear.",
    "Only {premium} to unlock {coverage} in coverage on your {deal_value} order.",
]

_VALUE_BY_CATEGORY: dict[str, list[str]] = {
    "travel": [
        "{deal_value} trip + {premium} cover = worry-free travel. {coverage} if things go wrong.",
        "Your {deal_value} trip deserves a {premium} safety net. Get {coverage} in cover.",
        "Just {premium} protects your {deal_value} {deal_name}. {coverage} in coverage included.",
    ],
    "electronics": [
        "Screen repair = {deal_value}+. Protection = {premium}. Easy choice for your {deal_name}.",
        "{deal_name} worth {deal_value}? Screen cover pays for itself in one claim for {premium}.",
        "Add {product} for {premium}. Repair or replacement covered up to {coverage}.",
    ],
    "food": [
        "{premium} guarantees your {deal_value} order. Get a refund if things go wrong.",
        "For {premium}, your {deal_value} food order is guaranteed—or your money back.",
    ],
    "health": [
        "{premium} unlocks {coverage} in OPD cover. One consultation pays for it.",
        "At {premium}, health OPD cover for your {deal_value} plan covers multiple visits.",
    ],
    "fashion": [
        "{deal_name} worth {deal_value}? {premium} cover is the smartest add-on in your cart.",
        "Protect your {deal_value} {deal_name} for {premium}. Covered up to {coverage}.",
    ],
}

# ── Reassurance (Variant C) ────────────────────────────────────────────────
_REASSURANCE_GENERIC = [
    "Enjoy your {deal_value} {deal_name} worry-free. {product} has you covered for {premium}.",
    "Shop with confidence. Your {deal_value} purchase is protected for just {premium}.",
    "Relax—your {deal_value} order is in safe hands for only {premium} with {product}.",
    "We've got your back. Cover your {deal_value} {deal_name} for {premium}, zero hassle.",
    "Peace of mind included for {premium}. Your {deal_value} {deal_name} is fully protected.",
    "Thousands trust {product}. Protect your {deal_value} order for {premium} today.",
]

_REASSURANCE_BY_CATEGORY: dict[str, list[str]] = {
    "travel": [
        "Bon voyage! Your {deal_value} trip to {merchant} is covered for just {premium}.",
        "Travel with total peace of mind. {deal_value} protected, {premium} is all it costs.",
        "Your {deal_value} trip is in safe hands. {product} covers the unexpected for {premium}.",
    ],
    "electronics": [
        "Use your {deal_value} {deal_name} freely—accidental damage is covered for {premium}.",
        "No more bubble wrap anxiety. Your {deal_value} device is protected for {premium}.",
        "Covered from day one. Enjoy your {deal_name} without worry for just {premium}.",
    ],
    "food": [
        "Every delivery guaranteed. Your {deal_value} order is protected for {premium}.",
        "Order with confidence—your {deal_value} meal is covered if anything goes wrong for {premium}.",
    ],
    "health": [
        "Your health matters. OPD cover keeps you protected for just {premium}.",
        "See a doctor anytime. Your outpatient visits are covered for only {premium}.",
    ],
    "fashion": [
        "Wear it confidently. Your {deal_value} {deal_name} is protected for {premium}.",
        "Style, met with safety. {deal_name} covered against theft or damage for {premium}.",
    ],
}

# ---------------------------------------------------------------------------
# Template selector
# ---------------------------------------------------------------------------

def _pick_template(
    variant_type: VariantType,
    category: str | None,
) -> str:
    """
    Select a template string from the appropriate pool.
    Prefers category-specific templates; falls back to generic pool.
    ~60% chance of category-specific template when one exists.
    """
    cat = (category or "").lower()

    pools_by_category: dict[VariantType, dict[str, list[str]]] = {
        "urgency":     _URGENCY_BY_CATEGORY,
        "value":       _VALUE_BY_CATEGORY,
        "reassurance": _REASSURANCE_BY_CATEGORY,
    }
    generic_pools: dict[VariantType, list[str]] = {
        "urgency":     _URGENCY_GENERIC,
        "value":       _VALUE_GENERIC,
        "reassurance": _REASSURANCE_GENERIC,
    }

    cat_pool  = pools_by_category[variant_type].get(cat, [])
    gen_pool  = generic_pools[variant_type]

    if cat_pool and random.random() < 0.65:
        return random.choice(cat_pool)
    return random.choice(gen_pool)


# ---------------------------------------------------------------------------
# Message renderer
# ---------------------------------------------------------------------------

def _render(
    template: str,
    deal_name:         str,
    merchant:          str,
    deal_value:        float,
    insurance_product: str,
    premium:           float,
    coverage:          float,
    currency:          str,
) -> str:
    """Fill a template with context values and trim to ≤ 160 characters."""
    ratio = int(coverage / premium) if premium > 0 else 0
    msg = template.format(
        deal_name=deal_name,
        merchant=merchant  or deal_name,
        deal_value=_fmt(deal_value, currency),
        product=insurance_product,
        premium=_fmt(premium, currency),
        coverage=_fmt(coverage, currency),
        ratio=f"{ratio}×",
    )
    # Hard-trim with ellipsis if somehow over 160 chars
    return msg if len(msg) <= 160 else msg[:157].rstrip() + "…"


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class CopyVariant:
    variant:  str          # "A", "B", or "C"
    tone:     VariantType  # urgency | value | reassurance
    message:  str
    chars:    int

    def to_dict(self) -> dict:
        return {
            "variant": self.variant,
            "tone":    self.tone,
            "message": self.message,
            "chars":   self.chars,
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_offer_copy(
    deal_name:         str,
    merchant:          str,
    deal_value:        float,
    insurance_product: str,
    premium:           float,
    *,
    category:          str | None = None,
    coverage:          float      = 0.0,
    currency:          str        = "SGD",
    seed:              int | None = None,
) -> list[dict]:
    """
    Generate 3 contextual insurance offer copy variants for a deal.

    Parameters
    ----------
    deal_name         : Name of the item or deal (e.g. "iPhone 16 Pro")
    merchant          : Merchant name (e.g. "Apple Store")
    deal_value        : Purchase price in local currency
    insurance_product : Insurance product name (e.g. "Screen Damage Cover")
    premium           : Insurance premium amount
    category          : Optional product category slug for contextual templates
                        ("travel" | "electronics" | "food" | "health" | "fashion")
    coverage          : Max payout amount (used in Value variant; defaults to 50× premium)
    currency          : Currency prefix (default: "SGD")
    seed              : Optional random seed for deterministic output (testing)

    Returns
    -------
    list[dict]  – 3 shuffled variants, each:
        {
            "variant": "A" | "B" | "C",
            "tone":    "urgency" | "value" | "reassurance",
            "message": str,   # ≤ 160 characters
            "chars":   int,
        }
    """
    if seed is not None:
        random.seed(seed)

    # Default coverage to a sensible fallback if not supplied
    if coverage <= 0:
        coverage = premium * 50

    context = dict(
        deal_name         = deal_name.strip() or "your item",
        merchant          = merchant.strip()  or deal_name,
        deal_value        = deal_value,
        insurance_product = insurance_product.strip(),
        premium           = premium,
        coverage          = coverage,
        currency          = currency,
    )

    variants: list[CopyVariant] = []
    tones: list[VariantType] = ["urgency", "value", "reassurance"]

    for tone in tones:
        # Sample a new template for each variant (with retries for length)
        for attempt in range(5):
            tmpl = _pick_template(tone, category)
            msg  = _render(tmpl, **context)
            if len(msg) <= 160:
                break
        else:
            # Last-resort minimal message
            msg = f"Protect your {_fmt(deal_value, currency)} purchase for {_fmt(premium, currency)}."

        variants.append(CopyVariant(
            variant=VARIANT_LABELS[tone],
            tone=tone,
            message=msg,
            chars=len(msg),
        ))

    # Shuffle to simulate LLM non-determinism (variant labels stay attached to tone)
    random.shuffle(variants)

    return [v.to_dict() for v in variants]


# ---------------------------------------------------------------------------
# CLI demo  (python copy_generator.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_cases = [
        dict(
            deal_name="Goa Trip Package",
            merchant="MakeMyTrip",
            deal_value=12400,
            insurance_product="Trip Cancellation Shield",
            premium=89,
            category="travel",
            coverage=5000,
            currency="INR",
        ),
        dict(
            deal_name="iPhone 16 Pro 256GB",
            merchant="Apple Store",
            deal_value=1299,
            insurance_product="Screen Damage Cover",
            premium=6.99,
            category="electronics",
            coverage=800,
            currency="SGD",
        ),
        dict(
            deal_name="GrabFood Order",
            merchant="GrabFood",
            deal_value=22.50,
            insurance_product="Personal Accident – Food Delivery",
            premium=3.99,
            category="food",
            coverage=50000,
            currency="SGD",
        ),
        dict(
            deal_name="Gucci Crossbody Bag",
            merchant="Zalora",
            deal_value=1850,
            insurance_product="Luxury Item Theft Guard",
            premium=19.99,
            category="fashion",
            coverage=10000,
            currency="SGD",
        ),
    ]

    for tc in test_cases:
        print(f"\n{'─'*70}")
        print(f"  Deal: {tc['deal_name']} ({tc['currency']} {tc['deal_value']:,})")
        print(f"  Product: {tc['insurance_product']}  |  Premium: {tc['currency']} {tc['premium']}")
        print(f"{'─'*70}")
        variants = generate_offer_copy(**tc)
        for v in variants:
            print(f"  [{v['variant']} – {v['tone'].upper():<12}] ({v['chars']} chars)")
            print(f"  {v['message']}")
            print()
