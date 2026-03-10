"""
mcp_server/server.py
GrabInsurance – MCP Server (Anthropic Model Context Protocol)

Exposes two tools connectable to Claude Desktop via stdio transport:

  ┌──────────────────────┬────────────────────────────────────────┐
  │ Tool                 │ Description                            │
  ├──────────────────────┼────────────────────────────────────────┤
  │ recommend_insurance  │ Classify a deal and return top-2       │
  │                      │ insurance products with confidence      │
  ├──────────────────────┼────────────────────────────────────────┤
  │ generate_offer_copy  │ Generate 3 offer copy variants         │
  │                      │ (urgency / value / reassurance)        │
  └──────────────────────┴────────────────────────────────────────┘

Claude Desktop config  (claude_desktop_config.json):
────────────────────────────────────────────────────
{
  "mcpServers": {
    "grabinsurance": {
      "command": "python",
      "args": ["D:/grabinsurance/mcp_server/server.py"],
      "env": {}
    }
  }
}

Run standalone:
    python mcp_server/server.py
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

# ── Add backend to import path so we can reuse classifier + copy_generator ──
_BACKEND = Path(__file__).resolve().parent.parent / "backend"
_DATA    = Path(__file__).resolve().parent.parent / "data"
for p in (_BACKEND, _DATA):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from classifier    import classify_deal         # backend/classifier.py
from copy_generator import generate_offer_copy   # backend/copy_generator.py

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, stream=sys.stderr)

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="GrabInsurance",
    instructions=(
        "You are connected to the GrabInsurance contextual embedded insurance engine. "
        "Use `recommend_insurance` to classify a purchase deal and get the two most "
        "relevant micro-insurance products with confidence scores. "
        "Use `generate_offer_copy` to produce three ready-to-display offer messages "
        "for a given product and premium."
    ),
)

# ---------------------------------------------------------------------------
# Shared catalog loader (reads data/insurance_products.json)
# ---------------------------------------------------------------------------

_catalog: list[dict] | None = None

def _load_catalog() -> list[dict]:
    global _catalog
    if _catalog is None:
        catalog_path = _DATA / "insurance_products.json"
        with open(catalog_path, encoding="utf-8") as f:
            _catalog = json.load(f)
    return _catalog


def _find_products_by_names(names: list[str]) -> dict[str, dict]:
    """Return a name→product dict for the given product names (case-insensitive)."""
    catalog = _load_catalog()
    index   = {p["name"].lower(): p for p in catalog}
    return {
        name: index[name.lower()]
        for name in names
        if name.lower() in index
    }

# ---------------------------------------------------------------------------
# Input / Output schemas (Pydantic → full JSON schema in MCP manifest)
# ---------------------------------------------------------------------------

class DealObject(BaseModel):
    """Represents a purchase deal to be classified."""
    merchant:    str        = Field(...,  description="Merchant or seller name. E.g. 'Singapore Airlines'")
    category:    str | list[str] = Field(..., description="Deal category slug(s). E.g. 'flights' or ['fashion','accessories']")
    subcategory: str | None = Field(None, description="Optional subcategory. E.g. 'international', 'smartphone'")
    deal_value:  float      = Field(...,  gt=0, description="Purchase price in local currency. E.g. 1299.0")
    user_history: list[str] = Field(default_factory=list,
                                    description="List of past purchase category slugs for personalisation")


class ProductRecommendation(BaseModel):
    rank:               int
    product_id:         int
    name:               str
    category:           str
    confidence:         float
    description:        str
    min_premium:        float
    max_coverage:       float
    risk_multiplier:    float


class RecommendInsuranceOutput(BaseModel):
    intent_category: str
    is_ambiguous:    bool
    recommendations: list[ProductRecommendation]


class CopyVariant(BaseModel):
    variant: str   # "A" | "B" | "C"
    tone:    str   # "urgency" | "value" | "reassurance"
    message: str
    chars:   int


class GenerateOfferCopyOutput(BaseModel):
    deal_value:   float
    product_name: str
    premium:      float
    variants:     list[CopyVariant]

# ---------------------------------------------------------------------------
# Tool 1 – recommend_insurance
# ---------------------------------------------------------------------------

@mcp.tool()
def recommend_insurance(deal: DealObject) -> dict:
    """
    Classify a purchase deal and return the top two contextual micro-insurance
    product recommendations with confidence scores.

    The classifier uses a three-layer pipeline:
      1. Rule-based category mapping
      2. Weighted multi-signal scoring (merchant, subcategory, deal value, history)
      3. Fallback rules for unknown categories

    Args:
        deal: A deal object describing the purchase (merchant, category,
              subcategory, deal_value, user_history).

    Returns:
        JSON object with intent_category, is_ambiguous flag, and a list of
        up to two recommended products each with name, category, confidence
        score (0–1), and catalog metadata (min_premium, max_coverage).
    """
    classification = classify_deal(deal.model_dump(mode="python"))

    raw_recs: list[dict] = classification.get("recommended_products", [])
    top_two  = raw_recs[:2]

    # Enrich with catalog metadata
    names      = [r["name"] for r in top_two]
    catalog_map = _find_products_by_names(names)

    recommendations: list[dict] = []
    for rank, rec in enumerate(top_two, start=1):
        cat_product = catalog_map.get(rec["name"], {})
        recommendations.append({
            "rank":            rank,
            "product_id":      cat_product.get("id",              0),
            "name":            rec["name"],
            "category":        cat_product.get("category",        ""),
            "confidence":      rec["confidence"],
            "description":     cat_product.get("description",     ""),
            "min_premium":     cat_product.get("min_premium",     0.0),
            "max_coverage":    cat_product.get("max_coverage",    0.0),
            "risk_multiplier": cat_product.get("risk_multiplier", 1.0),
        })

    return {
        "intent_category":  classification.get("intent_category", "unknown"),
        "is_ambiguous":     classification.get("is_ambiguous",    False),
        "is_multi_category":classification.get("is_multi_category", False),
        "missing_fields":   classification.get("missing_fields",  []),
        "recommendations":  recommendations,
    }


# ---------------------------------------------------------------------------
# Tool 2 – generate_offer_copy
# ---------------------------------------------------------------------------

@mcp.tool()
def generate_offer_copy(
    deal_value:   float = Field(..., gt=0,  description="Purchase price in local currency. E.g. 1299.0"),
    product_name: str   = Field(...,        description="Insurance product name. E.g. 'Screen Damage Cover'"),
    premium:      float = Field(..., gt=0,  description="Insurance premium amount. E.g. 6.99"),
    deal_name:    str   = Field("your purchase", description="Optional deal/item name for contextual copy"),
    merchant:     str   = Field("",         description="Optional merchant name for contextual copy"),
    category:     str   = Field("",         description="Optional product category: travel|electronics|food|health|fashion"),
    currency:     str   = Field("SGD",      description="Currency code prefix. Default: SGD"),
) -> dict:
    """
    Generate three contextual insurance offer copy variants for a checkout page.

    Produces one variant per tone without calling any external API:
      - Variant A: Urgency-driven   (FOMO, risk framing, limited-time feel)
      - Variant B: Value-driven     (coverage-to-premium ratio, ROI)
      - Variant C: Reassurance-driven (peace of mind, trust, simplicity)

    The variants are shuffled to simulate LLM response variability.
    Each message is ≤ 160 characters and contextual to the purchase and product.

    Args:
        deal_value:   Purchase price in local currency.
        product_name: Insurance product name from the catalog.
        premium:      Premium amount to display in the copy.
        deal_name:    Optional item name (improves contextualisation).
        merchant:     Optional merchant name.
        category:     Optional category slug for category-specific templates.
        currency:     Currency prefix (default: SGD).

    Returns:
        JSON object with deal context and a list of three copy variants,
        each containing variant label (A/B/C), tone, message text, and char count.
    """
    # Resolve coverage from catalog if product found
    catalog_map = _find_products_by_names([product_name])
    cat_product = catalog_map.get(product_name, {})
    coverage    = float(cat_product.get("max_coverage", 0.0))
    cat_slug    = category or cat_product.get("category", "")

    raw_variants = generate_offer_copy(
        deal_name         = deal_name,
        merchant          = merchant,
        deal_value        = deal_value,
        insurance_product = product_name,
        premium           = premium,
        category          = cat_slug or None,
        coverage          = coverage,
        currency          = currency,
    )

    return {
        "deal_value":   deal_value,
        "product_name": product_name,
        "premium":      premium,
        "currency":     currency,
        "variants":     raw_variants,
    }


# ---------------------------------------------------------------------------
# Entrypoint – stdio transport (required for Claude Desktop)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # transport="stdio" is the standard for Claude Desktop MCP servers.
    # The server speaks JSON-RPC over stdin/stdout; Claude Desktop launches
    # this process and communicates directly.
    mcp.run(transport="stdio")
