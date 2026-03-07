"""
recommendation_engine.py
MSc Thesis Prototype

Hybrid Recommendation Pipeline:
  Stage 1 — Rule-Based Filtering      (hard constraints)
  Stage 2 — Content-Based Scoring     (weighted features)
  Stage 3 — Collaborative Filtering   (user feedback signal)
  Stage 4 — Hybrid Score Merge        (blend both signals)
  Stage 5 — Return Top-N
"""

import numpy as np


# ─────────────────────────────────────────────
# Weight configuration
# ─────────────────────────────────────────────

# Content-based sub-weights (must sum to 1.0)
W_SKIN_TYPE = 0.35
W_CONCERN   = 0.25
W_RATING    = 0.20
W_PRICE     = 0.10
W_CATEGORY  = 0.10   # NEW: category match bonus

# Hybrid blend (must sum to 1.0)
# When there is enough collaborative data, CF gets more weight.
W_CONTENT   = 0.65
W_COLLAB    = 0.35

# Minimum number of user feedback ratings before CF score is trusted
CF_MIN_FEEDBACK = 2


# ─────────────────────────────────────────────
# Stage 1 — Rule-Based Filtering
# ─────────────────────────────────────────────

def rule_based_filter(products: list[dict], user_profile: dict) -> list[dict]:
    """
    Hard-constraint filtering.

    Rules applied:
      - skin_type must match (case-insensitive)
      - concern must match   (case-insensitive)
      - price ≤ max_budget
      - no avoided ingredient present (case-insensitive substring)
      - category must match if user selected one (optional filter)
    """
    skin_type  = user_profile["skin_type"].lower()
    concern    = user_profile["concern"].lower()
    max_budget = float(user_profile["max_budget"])
    avoided    = [i.lower() for i in user_profile.get("ingredients_to_avoid", [])]
    category   = user_profile.get("category", "all")

    filtered = []
    for p in products:
        if p.get("skin_type", "").lower() != skin_type:
            continue
        if p.get("concern", "").lower() != concern:
            continue
        if float(p.get("price", 0)) > max_budget:
            continue
        ingredients_str = p.get("ingredients", "").lower()
        if any(av in ingredients_str for av in avoided):
            continue
        # Category filter: skip only when user chose a specific category
        if category != "all" and p.get("category", "").lower() != category:
            continue
        filtered.append(p)

    return filtered


# ─────────────────────────────────────────────
# Stage 2 — Content-Based Scoring
# ─────────────────────────────────────────────

def content_based_score(products: list[dict], user_profile: dict) -> list[dict]:
    """
    Assign a content-based relevance score to each product.

    Formula:
        cb_score = 0.35 * skin_type_match   (guaranteed 1.0 after filter)
                 + 0.25 * concern_match      (guaranteed 1.0 after filter)
                 + 0.20 * normalised_rating  (rating / 5)
                 + 0.10 * price_score        (1 - price/budget)
                 + 0.10 * category_match     (1.0 if exact, 0.5 if 'all')
    """
    max_budget = float(user_profile["max_budget"])
    user_cat   = user_profile.get("category", "all").lower()
    scored = []

    for p in products:
        price  = float(p.get("price", 0))
        rating = float(p.get("rating", 0))

        normalised_rating = np.clip(rating / 5.0, 0.0, 1.0)
        price_score       = np.clip(1.0 - price / max_budget, 0.0, 1.0) if max_budget > 0 else 0.0
        category_match    = 1.0 if user_cat == "all" else (
                            1.0 if p.get("category", "").lower() == user_cat else 0.5
                           )

        cb_score = (
            W_SKIN_TYPE * 1.0
            + W_CONCERN  * 1.0
            + W_RATING   * normalised_rating
            + W_PRICE    * price_score
            + W_CATEGORY * category_match
        )

        scored.append({**p, "cb_score": round(float(cb_score), 4)})

    return scored


# ─────────────────────────────────────────────
# Stage 3 — Collaborative Filtering
# ─────────────────────────────────────────────

def collaborative_filter_score(
    products: list[dict],
    collab_data: list[dict],
) -> list[dict]:
    """
    Enrich each product with a collaborative filtering score derived from
    aggregated user feedback ratings stored in Supabase.

    collab_data rows contain:
        { product_id, avg_user_rating, feedback_count }

    CF score:
        - Normalise avg_user_rating to [0, 1] on a 5-point scale.
        - If feedback_count < CF_MIN_FEEDBACK, the CF score falls back to 0.5
          (neutral — we don't penalise products without feedback).
        - This avoids cold-start bias against new products.

    Args:
        products:     Content-scored product list.
        collab_data:  Rows from the product_collab_scores view.

    Returns:
        Products with a 'cf_score' key added.
    """
    # Build a lookup dict: product_id → collab row
    collab_lookup = {row["product_id"]: row for row in collab_data}

    for p in products:
        pid  = p["id"]
        row  = collab_lookup.get(pid)

        if row and int(row.get("feedback_count", 0)) >= CF_MIN_FEEDBACK:
            avg_rating = float(row["avg_user_rating"])
            p["cf_score"]       = round(np.clip(avg_rating / 5.0, 0.0, 1.0), 4)
            p["feedback_count"] = int(row["feedback_count"])
        else:
            # Cold start: neutral score, no penalty
            p["cf_score"]       = 0.5
            p["feedback_count"] = 0

    return products


# ─────────────────────────────────────────────
# Stage 4 — Hybrid Score Merge
# ─────────────────────────────────────────────

def merge_scores(products: list[dict]) -> list[dict]:
    """
    Blend content-based and collaborative scores into a single hybrid score.

        hybrid_score = W_CONTENT * cb_score + W_COLLAB * cf_score

    Products are then sorted descending by hybrid_score.
    """
    for p in products:
        p["score"] = round(
            W_CONTENT * p.get("cb_score", 0.0)
            + W_COLLAB  * p.get("cf_score",  0.5),
            4,
        )

    products.sort(key=lambda p: p["score"], reverse=True)
    return products


# ─────────────────────────────────────────────
# Full Pipeline
# ─────────────────────────────────────────────

def run_recommendation_pipeline(
    products: list[dict],
    user_profile: dict,
    collab_data: list[dict] | None = None,
    top_n: int = 5,
) -> list[dict]:
    """
    Execute the full hybrid recommendation pipeline.

    Args:
        products:     All products fetched from Supabase.
        user_profile: User input dict (skin_type, concern, category, budget, avoided).
        collab_data:  Rows from product_collab_scores view (can be empty/None).
        top_n:        Number of results to return.

    Returns:
        Top-N ranked product dicts with cb_score, cf_score, score, feedback_count.
    """
    # Stage 1: hard constraints
    candidates = rule_based_filter(products, user_profile)
    if not candidates:
        return []

    # Stage 2: content-based scoring
    candidates = content_based_score(candidates, user_profile)

    # Stage 3: collaborative filtering enrichment
    candidates = collaborative_filter_score(candidates, collab_data or [])

    # Stage 4: blend into hybrid score and sort
    ranked = merge_scores(candidates)

    # Stage 5: top-N
    return ranked[:top_n]
