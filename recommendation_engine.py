"""
recommendation_engine.py - Rule-Based Filtering + Content-Based Weighted Scoring
MSc Thesis Prototype

Pipeline:
  1. Rule-based filtering  → hard constraints (skin type, concern, budget, ingredients)
  2. Weighted scoring      → soft ranking across filtered candidates
  3. Return top-5 results
"""

import numpy as np


# ─────────────────────────────────────────────
# Scoring weights (must sum to 1.0)
# ─────────────────────────────────────────────
W_SKIN_TYPE  = 0.4   # Skin type compatibility is the most important factor
W_CONCERN    = 0.3   # Targeted concern alignment
W_RATING     = 0.2   # Community rating (normalised 0–1)
W_PRICE      = 0.1   # Price attractiveness within budget


# ─────────────────────────────────────────────
# Step 1 — Rule-Based Filtering
# ─────────────────────────────────────────────

def rule_based_filter(products: list[dict], user_profile: dict) -> list[dict]:
    """
    Apply hard-constraint rules to eliminate unsuitable products.

    Rules:
      - Product skin_type must match user's skin_type (case-insensitive)
      - Product concern must match user's concern (case-insensitive)
      - Product price must be ≤ max_budget
      - Product ingredients must NOT contain any avoided ingredient (case-insensitive)

    Args:
        products:     All products fetched from Supabase.
        user_profile: Dict with keys: skin_type, concern, ingredients_to_avoid, max_budget.

    Returns:
        Filtered list of qualifying products.
    """
    skin_type  = user_profile["skin_type"].lower()
    concern    = user_profile["concern"].lower()
    max_budget = float(user_profile["max_budget"])
    avoided    = [ing.lower() for ing in user_profile.get("ingredients_to_avoid", [])]

    filtered = []
    for product in products:
        # Rule 1: skin type match
        if product.get("skin_type", "").lower() != skin_type:
            continue

        # Rule 2: concern match
        if product.get("concern", "").lower() != concern:
            continue

        # Rule 3: budget constraint
        price = float(product.get("price", 0))
        if price > max_budget:
            continue

        # Rule 4: ingredient exclusion (case-insensitive substring check)
        ingredients_str = product.get("ingredients", "").lower()
        if any(avoided_ing in ingredients_str for avoided_ing in avoided):
            continue

        filtered.append(product)

    return filtered


# ─────────────────────────────────────────────
# Step 2 — Content-Based Weighted Scoring
# ─────────────────────────────────────────────

def compute_scores(products: list[dict], user_profile: dict) -> list[dict]:
    """
    Assign a composite relevance score to each filtered product.

    Formula:
        score = 0.4 * skin_type_match
              + 0.3 * concern_match
              + 0.2 * normalised_rating
              + 0.1 * price_score

    Where:
        skin_type_match  = 1.0 (always, since rule filter already enforced it)
        concern_match    = 1.0 (always, since rule filter already enforced it)
        normalised_rating = rating / 5.0
        price_score       = 1 - (price / max_budget)   → rewards cheaper products

    Args:
        products:     Rule-filtered products.
        user_profile: Dict containing max_budget.

    Returns:
        Products list with an added 'score' key, sorted descending by score.
    """
    max_budget = float(user_profile["max_budget"])
    scored = []

    for product in products:
        price  = float(product.get("price", 0))
        rating = float(product.get("rating", 0))

        # Both are 1.0 because rule filter already guarantees these matches
        skin_type_match = 1.0
        concern_match   = 1.0

        # Normalise rating to [0, 1] on a 5-point scale
        normalised_rating = np.clip(rating / 5.0, 0.0, 1.0)

        # Price score: lower price within budget → higher score
        # Avoid division by zero if budget is 0 (shouldn't happen via UI validation)
        price_score = 1.0 - (price / max_budget) if max_budget > 0 else 0.0
        price_score = np.clip(price_score, 0.0, 1.0)

        score = (
            W_SKIN_TYPE * skin_type_match
            + W_CONCERN * concern_match
            + W_RATING  * normalised_rating
            + W_PRICE   * price_score
        )

        scored.append({**product, "score": round(float(score), 4)})

    # Sort by composite score, highest first
    scored.sort(key=lambda p: p["score"], reverse=True)
    return scored


# ─────────────────────────────────────────────
# Step 3 — Full Pipeline
# ─────────────────────────────────────────────

def run_recommendation_pipeline(
    products: list[dict],
    user_profile: dict,
    top_n: int = 5,
) -> list[dict]:
    """
    Execute the end-to-end recommendation pipeline.

    Args:
        products:     All products from the database.
        user_profile: User input dict.
        top_n:        Number of recommendations to return (default 5).

    Returns:
        Top-N scored and ranked product dicts.
    """
    # Stage 1: hard-constraint filtering
    candidates = rule_based_filter(products, user_profile)

    if not candidates:
        return []

    # Stage 2: weighted content-based scoring
    ranked = compute_scores(candidates, user_profile)

    # Stage 3: return top-N
    return ranked[:top_n]
