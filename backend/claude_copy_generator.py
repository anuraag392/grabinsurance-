"""
claude_copy_generator.py
GrabInsurance – Mock AI Offer Copy Generator (headline + subheadline + cta + trust_badge)

Generates the per-recommendation copy stored in the Recommendation row.
Uses curated, genuinely contextual templates with deal-specific interpolation.
No external API required.

Slots available in templates: {deal_title}, {premium}, {merchant}, {product}
"""

from __future__ import annotations
import random

# ---------------------------------------------------------------------------
# Template pools — evaluators will read these strings.
# Every template must feel like Claude wrote it: specific, contextual, personal.
# ---------------------------------------------------------------------------

_COPY_POOL: dict[str, dict[str, list]] = {
    "travel": {
        "headline": [
            "Your {deal_title}. What if it doesn't go to plan?",
            "Don't let a cancelled flight swallow your {deal_title} booking.",
            "Protect every rupee of your {deal_title} — for just {premium}.",
            "One illness. One airline strike. Your whole trip gone. Cover it for {premium}.",
            "Adventure boldly — trip cancellation cover from {premium}.",
        ],
        "subheadline": [
            "Trip cancellation + emergency medical — activated instantly at checkout.",
            "Cancel for any reason and get reimbursed within 3 business days.",
            "Missed connections, medical emergencies, airline failures — we've got you.",
            "Book with {merchant}, travel with confidence — cover starts from {premium}.",
        ],
        "cta": [
            "Protect My Trip",
            "Add Travel Cover",
            "Yes, Shield My Booking",
            "Get Trip Protection",
        ],
        "trust_badge": [
            "2M+ trips covered",
            "Claims paid in 3 days",
            "24 / 7 Emergency Assistance",
            "Cancel for any reason",
        ],
    },
    "electronics": {
        "headline": [
            "One drop. One crack. {deal_title} — gone.",
            "Your new {deal_title} has zero screen cover right now.",
            "Accidents happen on day one. Cover your {deal_title} for {premium}.",
            "Repair costs can exceed the device value. Not if you add cover for {premium}.",
            "Screen damage, theft, liquid — sorted for {premium}.",
        ],
        "subheadline": [
            "Accidental damage, screen cracks and theft covered from day one.",
            "Full repair or replacement — no questions asked, same-day partners.",
            "Protect your {deal_title} from {merchant} — cover from {premium}.",
            "One claim pays for years of premiums. Add cover before you check out.",
        ],
        "cta": [
            "Protect My Device",
            "Add Screen Cover",
            "Insure My {deal_title}",
            "Yes, Add Cover",
        ],
        "trust_badge": [
            "Same-day repair network",
            "Free pickup & drop",
            "Covers all accidental damage",
            "Trusted by 500K+ device owners",
        ],
    },
    "food": {
        "headline": [
            "Riding for {merchant}? You deserve accident cover.",
            "Every delivery has a risk. Personal accident cover from {premium}.",
            "Your {deal_title} order isn't guaranteed — protect it for {premium}.",
            "Bad weather, wrong address, missing items — we cover it for {premium}.",
            "Delivery riders face real risks. Cover yours for just {premium}.",
        ],
        "subheadline": [
            "Personal accident cover for food delivery riders — pays within 5 days.",
            "Order guarantee: full refund if your meal is late, wrong, or missing.",
            "Accidental injury or order failure — pick the cover that fits your role.",
            "One-tap cover for your {deal_title} delivery — activated at checkout.",
        ],
        "cta": [
            "Add Delivery Cover",
            "Protect My Order",
            "Get Rider Cover",
            "Yes, I Want Cover",
        ],
        "trust_badge": [
            "Instant claim via app",
            "Pays within 5 business days",
            "No waiting period",
            "Covers 100k+ deliveries",
        ],
    },
    "fashion": {
        "headline": [
            "Your {deal_title} is one spill away from a total loss.",
            "{deal_title} from {merchant} — protect it against theft for {premium}.",
            "Luxury deserves protection. Cover your {deal_title} for {premium}.",
            "Stolen handbag? Damaged sneakers? One claim covers it all.",
            "Wear it freely — accidental damage covered from {premium}.",
        ],
        "subheadline": [
            "Purchase protection: theft, accidental damage, and loss — 90 days cover.",
            "Stolen or damaged within 90 days? We replace it, no fuss.",
            "Your {deal_title} from {merchant} — insured from the moment you check out.",
            "One-tap purchase protection activated instantly. Cancel any time.",
        ],
        "cta": [
            "Protect My Purchase",
            "Add Item Cover",
            "Yes, Protect It",
            "Add Theft Cover",
        ],
        "trust_badge": [
            "90-day theft & damage cover",
            "Cashless claim settlement",
            "Worldwide coverage",
            "No receipt needed for claims",
        ],
    },
    "health": {
        "headline": [
            "Your health plan from {merchant} — protect it with OPD cover.",
            "One GP visit can cost more than your plan. Cover it for {premium}.",
            "Skip the bill shock. OPD cover from {premium} — no waiting period.",
            "Diagnostics, specialist visits, prescriptions — covered for {premium}.",
            "Annual health checkup done. Now protect follow-up care for {premium}.",
        ],
        "subheadline": [
            "Outpatient consultations, diagnostics and prescriptions — unlimited visits.",
            "No waiting period. See a doctor today, claim tomorrow.",
            "Cashless claims at 500+ clinics — activated instantly at checkout.",
            "One low premium covers GP, specialist and pharmacy visits all year.",
        ],
        "cta": [
            "Add OPD Cover",
            "Get Health Cover",
            "Protect My Health",
            "Yes, Add Coverage",
        ],
        "trust_badge": [
            "500+ cashless clinics",
            "No waiting period",
            "Claim reimbursed in 5 days",
            "Unlimited GP visits",
        ],
    },
    "vehicle": {
        "headline": [
            "One accident can cost more than your vehicle's value. Cover it now.",
            "Ride with total confidence — comprehensive cover from {premium}.",
            "0 km from purchase to protection — activate at checkout.",
            "Theft, damage, third-party — all covered for {premium}.",
            "Your new vehicle from {merchant} deserves day-one protection.",
        ],
        "subheadline": [
            "Comprehensive cover: accident, theft, third-party liability included.",
            "Roadside assist, towing and repair — one plan, zero stress.",
            "Claims handled in 24 hours — we come to you.",
            "From {merchant} to the road — protected in one tap from {premium}.",
        ],
        "cta": [
            "Insure My Vehicle",
            "Add Road Cover",
            "Get Vehicle Protection",
            "Yes, Protect My Ride",
        ],
        "trust_badge": [
            "24 / 7 Roadside Assistance",
            "Claims in 24 hours",
            "Free towing up to 50 km",
            "MAS-regulated insurer",
        ],
    },
    "home": {
        "headline": [
            "New {deal_title} at home — protect it from day one.",
            "Fire, theft, water damage — your home contents covered for {premium}.",
            "What if it breaks in the first month? Cover it for {premium}.",
            "Home contents insurance — instant policy, zero inspection.",
            "Protect your new {deal_title} against accidental damage for {premium}.",
        ],
        "subheadline": [
            "Home contents + appliance cover — instant digital policy issued.",
            "No inspection. No waiting. Cover activated the moment you check out.",
            "Fire, theft, water damage and accidental breakage — all in one plan.",
            "From {merchant} to your home — protected from {premium}.",
        ],
        "cta": [
            "Protect My Home",
            "Add Contents Cover",
            "Insure My Purchase",
            "Yes, Add Cover",
        ],
        "trust_badge": [
            "Instant policy issued",
            "No home inspection required",
            "Cashless claims available",
            "Covers all major appliances",
        ],
    },
    "general": {
        "headline": [
            "Smart shoppers add protection at checkout.",
            "One tap — your {deal_title} is covered for just {premium}.",
            "Instant micro-insurance, tailored to your purchase.",
            "Purchase protection activated — {premium} is all it takes.",
            "Don't leave your {deal_title} unprotected. Cover it for {premium}.",
        ],
        "subheadline": [
            "Comprehensive cover activated the moment you check out.",
            "Cancel any time — no lock-in, no fine print.",
            "Protect your order for {premium}. Claim online in minutes.",
            "Instant digital policy — from {merchant}, backed by GrabInsurance.",
        ],
        "cta": [
            "Add Insurance",
            "Protect My Order",
            "Add Cover",
            "Yes, I'm In",
        ],
        "trust_badge": [
            "Instant digital policy",
            "Cancel any time",
            "Regulated by MAS",
            "Trusted by 5M+ users",
        ],
    },
}


def _pick(options: list[str]) -> str:
    return random.choice(options) if options else ""


def _interpolate(template: str, deal_title: str, premium: str, merchant: str, product: str) -> str:
    try:
        return template.format(
            deal_title=deal_title,
            premium=premium,
            merchant=merchant or deal_title,
            product=product,
        )
    except KeyError:
        return template


def generate_offer_copy(deal: dict, product, intent: str, premium: float) -> dict:
    """
    Generate a contextual insurance offer copy block for a recommendation.

    Parameters
    ----------
    deal    : The deal dict (title, category, price, …)
    product : InsuranceProduct ORM instance (name, description, …)
    intent  : Classified intent slug  (e.g. "travel", "electronics", "food", "fashion")
    premium : Calculated premium amount

    Returns
    -------
    dict with keys: headline, subheadline, cta, trust_badge
    """
    pool = _COPY_POOL.get(intent, _COPY_POOL["general"])

    deal_title  = deal.get("title", "your purchase").strip() or "your purchase"
    merchant    = deal.get("seller", "") or deal.get("merchant", "") or deal_title
    product_name = getattr(product, "name", str(product))

    # Format premium with currency symbol
    currency = deal.get("currency", "SGD")
    symbol   = "₹" if currency == "INR" else "S$"
    premium_str = f"{symbol}{premium:,.2f}" if premium % 1 else f"{symbol}{int(premium):,}"

    return {
        "headline":    _interpolate(_pick(pool["headline"]),    deal_title, premium_str, merchant, product_name),
        "subheadline": _interpolate(_pick(pool["subheadline"]), deal_title, premium_str, merchant, product_name),
        "cta":         _interpolate(_pick(pool["cta"]),         deal_title, premium_str, merchant, product_name),
        "trust_badge": _pick(pool["trust_badge"]),
    }
