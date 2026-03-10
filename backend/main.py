"""
main.py – GrabInsurance FastAPI application.

Exposes the full 6-step recommendation pipeline:
  classify_intent → recommend_products → calculate_price
  → generate_offer_copy → assign_variant → save Recommendation

Plus event tracking and analytics endpoints for the dashboard.
"""

import os
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv

load_dotenv()

from database import Base, engine, get_db
from models import Event, InsuranceProduct, Recommendation
from intent_classifier import classify_intent
from insurance_recommender import recommend_products
from pricing_engine import (
    calculate_premium,
    get_product_by_name,
    get_product_by_id,
    PricingError,
    load_catalog,
)
from claude_copy_generator import generate_offer_copy
from copy_generator import generate_offer_copy as gen_copy_variants
from ab_testing import assign_variant, get_ab_metrics, track_event
from analytics import (
    get_events_over_time,
    get_funnel_summary,
    get_revenue_by_category,
    get_top_products,
)

# Create tables on startup (idempotent)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="GrabInsurance API",
    version="1.0.0",
    description="Contextual Embedded Insurance Engine — detects purchase intent and recommends micro-insurance at checkout.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

dashboard_path = os.path.join(os.path.dirname(__file__), "..", "dashboard")
app.mount("/dashboard", StaticFiles(directory=dashboard_path, html=True), name="dashboard")


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class DealRequest(BaseModel):
    title: str
    category: str
    price: float
    tags: list[str] = []
    user_id: str = "anonymous"
    seller: Optional[str] = None


class EventRequest(BaseModel):
    user_id: str
    recommendation_id: int
    session_id: Optional[str] = None   # stable browser session identifier
    event_type: str          # impression | click | accept | decline
    variant: str
    category: str = ""
    premium: Optional[float] = None


class QuoteRequest(BaseModel):
    """
    Request body for /get-insurance-quote.

    product_name OR product_id must be supplied.
    user_risk_tier: "low" | "medium" | "high"  (default: "medium")
    """
    deal_value:      float
    product_name:    Optional[str]  = None
    product_id:      Optional[int]  = None
    user_risk_tier:  str            = "medium"


class CopyVariantsRequest(BaseModel):
    deal_name:    str
    merchant:     str
    deal_value:   float
    product_name: str
    premium:      float
    category:     Optional[str] = None
    coverage:     float        = 0.0
    currency:     str          = "SGD"


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "service": "GrabInsurance API", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# Product catalog
# ---------------------------------------------------------------------------


@app.get("/api/products", tags=["Catalog"])
def list_products(db: Session = Depends(get_db)):
    """Return the full insurance product catalog."""
    return db.query(InsuranceProduct).all()


# ---------------------------------------------------------------------------
# Core recommendation pipeline
# ---------------------------------------------------------------------------


@app.post("/api/recommend", tags=["Engine"])
def recommend(request: DealRequest, db: Session = Depends(get_db)):
    """
    Full 6-step pipeline:
    1. Classify intent from deal
    2. Recommend matching insurance products
    3. Calculate dynamic premium
    4. Generate Claude offer copy
    5. Assign A/B variant
    6. Persist recommendation and return structured response
    """
    deal = request.model_dump()

    # Step 1: Intent classification
    intent_result = classify_intent(deal)
    intent = intent_result["intent"]

    # Step 2: Product recommendation
    products = recommend_products(intent, db, top_n=1)
    if not products:
        raise HTTPException(status_code=404, detail="No matching insurance products found.")
    product = products[0]

    # Step 3: Dynamic pricing
    # Step 3: Dynamic pricing (use catalog JSON product if DB product lacks new fields)
    try:
        cat_product = get_product_by_name(product.name) or {}
    except Exception:
        cat_product = {}

    if not cat_product:
        # Build a minimal catalog-compatible dict from the ORM object
        cat_product = {
            "id":               product.id,
            "name":             product.name,
            "category":         product.category,
            "description":      getattr(product, "description", ""),
            "risk_multiplier":  getattr(product, "rate_pct", 0.01),
            "min_premium":      getattr(product, "base_price", 1.99),
            "max_coverage":     getattr(product, "coverage_amount", 10000.0),
            "currency":         "SGD",
        }

    quote_obj = calculate_premium(request.price, cat_product, user_risk_tier="medium")
    quote_compat = type(
        "Q", (),
        {
            "final_premium":   quote_obj.premium_price,
            "coverage_amount": quote_obj.coverage_amount,
            "currency":        quote_obj.currency,
            "base_price":      0.0,
            "risk_multiplier": quote_obj.risk_multiplier,
        },
    )()

    quote = quote_compat

    # Step 4: A/B variant assignment
    variant = assign_variant(request.user_id, deal.get("title", "unknown"))

    # Step 5: Claude copy generation
    copy = generate_offer_copy(deal, product, intent, quote.final_premium)

    # Step 6: Persist recommendation
    rec = Recommendation(
        user_id=request.user_id,
        deal_snapshot=deal,
        intent=intent,
        confidence=intent_result["confidence"],
        product_id=product.id,
        product_name=product.name,
        premium=getattr(quote, "final_premium", getattr(quote, "premium_price", 0.0)),
        variant=variant,
        copy_headline=copy.get("headline", ""),
        copy_cta=copy.get("cta", ""),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    return {
        "recommendation_id": rec.id,
        "intent": intent_result,
        "product": {
            "id": product.id,
            "name": product.name,
            "category": product.category,
            "description": product.description,
            "coverage_amount": product.coverage_amount,
        },
        "quote": {
            "final_premium": quote.final_premium,
            "coverage_amount": quote.coverage_amount,
            "currency": quote.currency,
            "base_price": quote.base_price,
            "risk_multiplier": quote.risk_multiplier,
        },
        "variant": variant,
        "session_id": f"{request.user_id}:{rec.id}",   # stable per-session correlation ID
        "copy": copy,
    }


# ---------------------------------------------------------------------------
# Event tracking
# ---------------------------------------------------------------------------


@app.post("/api/event", tags=["Events"])
def record_event(request: EventRequest, db: Session = Depends(get_db)):
    """Track a user interaction event against a recommendation."""
    track_event(
        db=db,
        user_id=request.user_id,
        recommendation_id=request.recommendation_id,
        event_type=request.event_type,
        variant=request.variant,
        category=request.category,
        premium=request.premium,
    )
    return {"status": "recorded", "event_type": request.event_type}


# ---------------------------------------------------------------------------
# Analytics endpoints (consumed by dashboard)
# ---------------------------------------------------------------------------


@app.get("/api/analytics/summary", tags=["Analytics"])
def analytics_summary(db: Session = Depends(get_db)):
    """Overall funnel metrics: impressions → clicks → accepts."""
    return get_funnel_summary(db)


@app.get("/api/analytics/ab", tags=["Analytics"])
def analytics_ab(db: Session = Depends(get_db)):
    """Per-variant CTR, CVR and revenue for the A/B test."""
    return get_ab_metrics(db)


@app.get("/api/analytics/revenue", tags=["Analytics"])
def analytics_revenue(db: Session = Depends(get_db)):
    """Revenue and policy count grouped by insurance category."""
    return get_revenue_by_category(db)


@app.get("/api/analytics/products", tags=["Analytics"])
def analytics_products(db: Session = Depends(get_db)):
    """Top insurance products by recommendation count."""
    return get_top_products(db)


@app.get("/api/analytics/events-over-time", tags=["Analytics"])
def analytics_events_over_time(db: Session = Depends(get_db)):
    """Daily event counts by event type for time-series charts."""
    return get_events_over_time(db)


# ---------------------------------------------------------------------------
# Insurance quote endpoint
# ---------------------------------------------------------------------------


@app.post("/get-insurance-quote", tags=["Engine"])
def get_insurance_quote(request: QuoteRequest):
    """
    Calculate an insurance premium quote for a given deal and product.

    Lookup priority:
        1. product_name (case-insensitive name match in catalog)
        2. product_id   (numeric ID match in catalog)

    Pricing formula:
        premium = deal_value × product.risk_multiplier × tier_modifier
        where tier_modifier: low=0.8  medium=1.0  high=1.3

    Catalog constraints enforced:
        premium  ≥  product.min_premium
        premium  ≤  product.max_coverage × 5%

    Returns:
        product, premium_price, coverage_amount, currency, and full breakdown.
    """
    # --- Resolve product from catalog ---
    product: dict | None = None

    if request.product_name:
        product = get_product_by_name(request.product_name)
        if product is None:
            raise HTTPException(
                status_code=404,
                detail=f"Product not found in catalog: '{request.product_name}'",
            )

    elif request.product_id is not None:
        product = get_product_by_id(request.product_id)
        if product is None:
            raise HTTPException(
                status_code=404,
                detail=f"Product ID {request.product_id} not found in catalog.",
            )

    else:
        raise HTTPException(
            status_code=422,
            detail="Provide either 'product_name' or 'product_id'.",
        )

    # --- Calculate premium ---
    try:
        quote = calculate_premium(
            deal_value=request.deal_value,
            product=product,
            user_risk_tier=request.user_risk_tier,
        )
    except PricingError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return quote.to_dict()


# ---------------------------------------------------------------------------
# Copy variants endpoint (consumed by React VariantCopyComponent)
# ---------------------------------------------------------------------------


@app.post("/api/copy-variants", tags=["Engine"])
def copy_variants(request: CopyVariantsRequest):
    """
    Generate three offer copy variants (urgency / value / reassurance)
    for a recommended insurance product using the mock copy generator.
    """
    variants = gen_copy_variants(
        deal_name         = request.deal_name,
        merchant          = request.merchant,
        deal_value        = request.deal_value,
        insurance_product = request.product_name,
        premium           = request.premium,
        category          = request.category,
        coverage          = request.coverage,
        currency          = request.currency,
    )
    return {
        "deal_name":    request.deal_name,
        "product_name": request.product_name,
        "premium":      request.premium,
        "currency":     request.currency,
        "variants":     variants,
    }
