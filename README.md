# GrabInsurance – Contextual Embedded Insurance Engine

> AI-powered micro-insurance recommendations at checkout, built with FastAPI, React, and Chart.js.

## Project Structure

```
grabinsurance/
├── backend/            FastAPI app + all pipeline modules
│   ├── main.py         API routes (recommend, event, analytics)
│   ├── intent_classifier.py   Keyword rule engine → intent enum
│   ├── insurance_recommender.py  Intent → product DB lookup
│   ├── pricing_engine.py         Dynamic premium calculator
│   ├── claude_copy_generator.py  Mock AI offer copy generator (no API key needed)
│   ├── ab_testing.py             Hash-based A/B assignment + tracking
│   ├── analytics.py              Funnel & revenue aggregations
│   ├── models.py                 SQLAlchemy ORM models
│   ├── database.py               Engine + SessionLocal
│   └── requirements.txt
│
├── mcp_server/         FastMCP server exposing 4 tools
│   └── server.py
│
├── data/
│   ├── insurance_products.json   20 product catalog
│   └── seed_data.py              DB seeder (products + 250 events)
│
├── frontend/           Vite + React + TailwindCSS checkout UI
│   └── src/
│       ├── components/CheckoutPage.jsx
│       ├── components/InsuranceOfferModal.jsx
│       ├── components/DealSummary.jsx
│       └── api/client.js
│
└── dashboard/          Standalone Chart.js analytics dashboard
    └── index.html
```

## Quick Start

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env          # No API key needed
```

### 2. Seed the Database

```bash
cd ../data
python seed_data.py
```

### 3. Run the API

```bash
cd ../backend
uvicorn main:app --reload --port 8000
```

API docs at: http://localhost:8000/docs

### 4. Frontend

```bash
cd ../frontend
npm install
npm run dev
# Open http://localhost:5173
```

### 5. MCP Server

```bash
cd ../mcp_server
pip install -r requirements.txt
python server.py
```

### 6. Analytics Dashboard

Open `dashboard/index.html` directly in your browser (backend must be running).

---

## How the Pipeline Works

```
Deal Object (title, category, price, tags)
    │
    ▼
[1] Intent Classifier       → intent: travel | electronics | health | vehicle | home
    │
    ▼
[2] Insurance Recommender   → ranked product list from SQLite
    │
    ▼
[3] Pricing Engine          → premium = (base + deal×rate) × risk × tier
    │
    ▼
[4] Mock AI Copy Generator  → headline, subheadline, CTA, trust badge
    │
    ▼
[5] A/B Variant Assigner    → hash(user_id) % 2 → A or B
    │
    ▼
[6] Recommendation saved    → Events tracked (impression/click/accept/decline)
```

## Key API Endpoints

| Method | Endpoint                      | Description                        |
|--------|-------------------------------|------------------------------------|
| POST   | `/api/recommend`              | Full pipeline for a deal object    |
| POST   | `/api/event`                  | Track user interaction             |
| GET    | `/api/analytics/summary`      | Funnel metrics                     |
| GET    | `/api/analytics/ab`           | A/B variant CTR/CVR/revenue        |
| GET    | `/api/analytics/revenue`      | Revenue by insurance category      |
| GET    | `/api/analytics/products`     | Top recommended products           |
| GET    | `/api/analytics/events-over-time` | Daily event time series        |

## Environment Variables

| Variable         | Required | Description                        |
|-----------------|----------|------------------------------------|
| DATABASE_URL    | Optional | SQLite path (default: `data/grabinsurance.db`) |

## Tech Stack

| Layer      | Technology                              |
|------------|----------------------------------------|
| Backend    | Python 3.11+, FastAPI, SQLAlchemy      |
| AI         | Built-in Mock AI Generator (no external API)   |
| MCP        | FastMCP (python-sdk)                   |
| Database   | SQLite                                 |
| Frontend   | React 18, Vite, TailwindCSS v3, Framer Motion |
| Dashboard  | Vanilla JS, Chart.js 4 (CDN)           |
