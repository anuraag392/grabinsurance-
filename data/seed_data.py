"""
seed_data.py
Creates the SQLite database, seeds 20 insurance products,
2 A/B variants, and ~250 realistic synthetic events spread
over the last 30 days.

Run from project root:
    python data/seed_data.py
"""

import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Allow imports from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from database import Base, engine, SessionLocal
from models import ABVariant, Event, InsuranceProduct, Recommendation

PRODUCTS_JSON = Path(__file__).parent / "insurance_products.json"

SAMPLE_DEALS = [
    {"title": "iPhone 16 Pro 256GB", "category": "mobiles", "price": 1299.0, "tags": ["apple", "smartphone"]},
    {"title": "Singapore Airlines Flight SQ001", "category": "flights", "price": 680.0, "tags": ["flight", "airline"]},
    {"title": "Dell XPS 15 Laptop", "category": "laptops", "price": 2499.0, "tags": ["laptop", "dell"]},
    {"title": "Bali Resort Package 5D4N", "category": "packages", "price": 1850.0, "tags": ["vacation", "resort", "trip"]},
    {"title": "Samsung QLED 65\" TV", "category": "electronics", "price": 1799.0, "tags": ["tv", "samsung"]},
    {"title": "Honda PCX 160 Scooter", "category": "vehicles", "price": 4200.0, "tags": ["scooter", "honda"]},
    {"title": "IKEA MALM Queen Bed Frame", "category": "furniture", "price": 399.0, "tags": ["bed", "furniture"]},
    {"title": "Dyson V15 Vacuum Cleaner", "category": "appliances", "price": 899.0, "tags": ["vacuum", "appliance"]},
    {"title": "AirPods Pro 2nd Gen", "category": "gadgets", "price": 349.0, "tags": ["earbuds", "apple", "audio"]},
    {"title": "3-Night Sentosa Hotel Stay", "category": "hotels", "price": 540.0, "tags": ["hotel", "travel"]},
]

INTENTS_FOR_DEALS = [
    "electronics", "travel", "electronics", "travel", "electronics",
    "vehicle", "home", "home", "electronics", "travel",
]

CATEGORY_FOR_DEALS = [
    "device_protection", "travel_cancellation", "device_protection",
    "travel_cancellation", "device_protection", "vehicle_damage",
    "home_contents", "appliance_protection", "device_protection",
    "travel_medical",
]

VARIANTS = ["A", "B"]

# Realistic funnel drop-off rates
CLICK_RATE = 0.55       # 55% of impressions click
ACCEPT_RATE = 0.28      # 28% of impressions accept (of those, ~50% who clicked)
DECLINE_RATE = 0.27     # 27% of impressions decline


def random_past_datetime(days_back: int = 30) -> datetime:
    offset = random.randint(0, days_back * 24 * 60 * 60)
    return datetime.utcnow() - timedelta(seconds=offset)


def seed():
    print("Creating database tables…")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # ------------------------------------------------------------------ #
    # 1. Insurance products
    # ------------------------------------------------------------------ #
    if db.query(InsuranceProduct).count() == 0:
        print("Seeding insurance products…")
        with open(PRODUCTS_JSON) as f:
            products_data = json.load(f)
        for p in products_data:
            db.add(InsuranceProduct(**p))
        db.commit()
        print(f"  → {len(products_data)} products inserted.")
    else:
        print("  Insurance products already seeded, skipping.")

    # ------------------------------------------------------------------ #
    # 2. A/B variants
    # ------------------------------------------------------------------ #
    if db.query(ABVariant).count() == 0:
        print("Seeding A/B variants…")
        db.add(ABVariant(name="A", description="Control – standard offer card layout"))
        db.add(ABVariant(name="B", description="Experiment – urgency badge + social proof"))
        db.commit()
        print("  → 2 variants inserted.")

    # ------------------------------------------------------------------ #
    # 3. Synthetic recommendations + events
    # ------------------------------------------------------------------ #
    existing_events = db.query(Event).count()
    if existing_events < 50:
        print("Seeding synthetic recommendations and events…")
        products = db.query(InsuranceProduct).all()

        rec_count = 0
        event_count = 0

        for i in range(250):
            deal_idx = i % len(SAMPLE_DEALS)
            deal = SAMPLE_DEALS[deal_idx]
            intent = INTENTS_FOR_DEALS[deal_idx]
            category = CATEGORY_FOR_DEALS[deal_idx]
            user_id = f"synthetic_user_{i:04d}"
            variant = VARIANTS[i % 2]

            # Pick a product matching the intent category
            matching = [p for p in products if p.category == category]
            product = random.choice(matching) if matching else random.choice(products)

            # Calculate a realistic premium
            premium = round(product.base_price + deal["price"] * product.rate_pct, 2)

            ts = random_past_datetime(30)

            rec = Recommendation(
                user_id=user_id,
                deal_snapshot=deal,
                intent=intent,
                confidence=round(random.uniform(0.62, 0.97), 2),
                product_id=product.id,
                product_name=product.name,
                premium=premium,
                variant=variant,
                copy_headline="Add protection at checkout",
                copy_cta="Add Insurance",
                created_at=ts,
            )
            db.add(rec)
            db.flush()  # get rec.id
            rec_count += 1

            # Impression always tracked
            db.add(Event(
                user_id=user_id,
                recommendation_id=rec.id,
                event_type="impression",
                variant=variant,
                category=category,
                created_at=ts,
            ))
            event_count += 1

            rand = random.random()
            if rand < ACCEPT_RATE:
                db.add(Event(
                    user_id=user_id,
                    recommendation_id=rec.id,
                    event_type="click",
                    variant=variant,
                    category=category,
                    created_at=ts + timedelta(seconds=random.randint(2, 15)),
                ))
                db.add(Event(
                    user_id=user_id,
                    recommendation_id=rec.id,
                    event_type="accept",
                    variant=variant,
                    category=category,
                    premium=premium,
                    created_at=ts + timedelta(seconds=random.randint(16, 60)),
                ))
                event_count += 2

            elif rand < ACCEPT_RATE + DECLINE_RATE:
                db.add(Event(
                    user_id=user_id,
                    recommendation_id=rec.id,
                    event_type="click",
                    variant=variant,
                    category=category,
                    created_at=ts + timedelta(seconds=random.randint(2, 15)),
                ))
                db.add(Event(
                    user_id=user_id,
                    recommendation_id=rec.id,
                    event_type="decline",
                    variant=variant,
                    category=category,
                    created_at=ts + timedelta(seconds=random.randint(16, 60)),
                ))
                event_count += 2

            elif rand < ACCEPT_RATE + DECLINE_RATE + CLICK_RATE - ACCEPT_RATE - DECLINE_RATE:
                # click only (no action)
                db.add(Event(
                    user_id=user_id,
                    recommendation_id=rec.id,
                    event_type="click",
                    variant=variant,
                    category=category,
                    created_at=ts + timedelta(seconds=random.randint(2, 15)),
                ))
                event_count += 1

        db.commit()
        print(f"  → {rec_count} recommendations and {event_count} events inserted.")
    else:
        print(f"  Events already present ({existing_events}), skipping synthetic seed.")

    db.close()
    print("\nSeed complete. Database is ready.")


if __name__ == "__main__":
    seed()
