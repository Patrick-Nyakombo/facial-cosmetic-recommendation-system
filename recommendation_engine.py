"""
recommendation_engine.py
MSc Thesis Prototype

Hybrid Recommendation Pipeline aligned with dissertation:
  Stage 1 — Rule-Based Filtering  (skin type, concern, category, price, ingredients)
  Stage 2 — Content-Based Scoring (skin type match + concern match + rating +
                                    popularity + price fit + tag match)
  Stage 3 — Collaborative Filtering (helpfulness-weighted user feedback)
  Stage 4 — Hybrid Score Merge    (65% content / 35% collaborative)
  Stage 5 — Top-N

Skin type → tag mapping:
  oily        → "best for oily skin"
  dry         → "best for dry skin"
  combination → "best for combination skin"
  sensitive   → "best for sensitive skin"

Concern → tag mapping:
  acne             → "good for: acne/blemishes"
  aging            → "good for: aging"
  hyperpigmentation → "good for: dark spots"
  dryness          → "hydrating"
"""

import json
import ast
import numpy as np

# ── Content-based sub-weights (sum = 1.0) ──────────────────────
W_SKIN_TYPE  = 0.20   # skin type match via tag mapping
W_CONCERN    = 0.20   # concern match via tag mapping
W_RATING     = 0.20   # product rating
W_LOVES      = 0.10   # popularity
W_REVIEWS    = 0.05   # review count depth
W_PRICE      = 0.10   # price fit within budget
W_TAG_MATCH  = 0.10   # user-selected extra tags
W_CATEGORY   = 0.05   # category match bonus

# ── Hybrid blend (sum = 1.0) ────────────────────────────────────
W_CONTENT = 0.65
W_COLLAB  = 0.35

CF_MIN_FEEDBACK = 2

# ── Skin type → product highlight tag mapping ───────────────────
SKIN_TYPE_TAG_MAP = {
    "oily":        ["best for oily skin", "oil control", "mattifying"],
    "dry":         ["best for dry skin", "moisturizing", "hydrating"],
    "combination": ["best for combination skin", "balancing"],
    "sensitive":   ["best for sensitive skin", "gentle", "fragrance free"],
}

# ── Skin concern → product highlight tag mapping ────────────────
CONCERN_TAG_MAP = {
    "acne":              ["good for: acne/blemishes", "acne", "blemish", "oil control"],
    "aging":             ["good for: aging", "anti-aging", "anti-wrinkle", "firming"],
    "hyperpigmentation": ["good for: dark spots", "brightening", "dark spots", "even skin tone"],
    "dryness":           ["hydrating", "moisturizing", "good for: dry skin"],
}


def _parse_highlights(raw) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(t).lower().strip() for t in raw]
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(t).lower().strip() for t in parsed]
    except (json.JSONDecodeError, TypeError):
        pass
    try:
        parsed = ast.literal_eval(raw)
        if isinstance(parsed, list):
            return [str(t).lower().strip() for t in parsed]
    except Exception:
        pass
    return []


def _tag_overlap(product_tags: list[str], target_tags: list[str]) -> float:
    """Return fraction of target_tags found (substring match) in product_tags. 0–1."""
    if not target_tags:
        return 0.5   # neutral when no target defined
    hits = sum(
        1 for tt in target_tags
        if any(tt in pt or pt in tt for pt in product_tags)
    )
    return hits / len(target_tags)


# ─────────────────────────────────────────────
# Stage 1 — Rule-Based Filtering
# ─────────────────────────────────────────────

def rule_based_filter(products: list[dict], user_profile: dict) -> list[dict]:
    """
    Hard constraints:
      - primary/secondary category match
      - price ≤ max_budget
      - no avoided ingredient present
      - out_of_stock excluded unless opted in
    Skin type and concern are soft signals (scored, not filtered).
    """
    primary_cat   = user_profile.get("primary_category", "all").lower()
    secondary_cat = user_profile.get("secondary_category", "all").lower()
    max_budget    = float(user_profile.get("max_budget", 999_999))
    avoided       = [i.lower() for i in user_profile.get("ingredients_to_avoid", [])]
    include_oos   = user_profile.get("include_out_of_stock", False)

    filtered = []
    for p in products:
        if not include_oos and int(p.get("out_of_stock") or 0) == 1:
            continue
        price = p.get("price_usd")
        if price is not None and float(price) > max_budget:
            continue
        if primary_cat != "all":
            if (p.get("primary_category") or "").lower() != primary_cat:
                continue
        if secondary_cat != "all":
            if (p.get("secondary_category") or "").lower() != secondary_cat:
                continue
        ingredients_str = (p.get("ingredients") or "").lower()
        if any(av in ingredients_str for av in avoided):
            continue
        filtered.append(p)

    return filtered


# ─────────────────────────────────────────────
# Stage 2 — Content-Based Scoring
# ─────────────────────────────────────────────

def content_based_score(
    products: list[dict],
    user_profile: dict,
    all_loves: list[int],
    all_reviews: list[int],
) -> list[dict]:
    """
    Score = W_SKIN_TYPE  * skin_type_match    (via tag mapping)
          + W_CONCERN    * concern_match       (via tag mapping)
          + W_RATING     * normalised_rating
          + W_LOVES      * normalised_loves
          + W_REVIEWS    * normalised_reviews
          + W_PRICE      * price_score
          + W_TAG_MATCH  * extra_tag_match
          + W_CATEGORY   * category_match
    """
    primary_cat   = user_profile.get("primary_category", "all").lower()
    max_budget    = float(user_profile.get("max_budget", 1))
    skin_type     = user_profile.get("skin_type", "").lower()
    skin_concerns = [c.lower() for c in user_profile.get("skin_concerns", [])]
    extra_tags    = [t.lower() for t in user_profile.get("tags_to_match", [])]

    # Build target tag lists from skin type and concerns
    skin_type_targets = SKIN_TYPE_TAG_MAP.get(skin_type, [])
    concern_targets   = []
    for c in skin_concerns:
        concern_targets.extend(CONCERN_TAG_MAP.get(c, []))

    max_loves_in_set   = max(all_loves, default=1) or 1
    max_reviews_in_set = max(all_reviews, default=1) or 1

    scored = []
    for p in products:
        price      = float(p.get("price_usd") or 0)
        rating     = float(p.get("rating") or 0)
        loves      = int(p.get("loves_count") or 0)
        reviews    = int(p.get("reviews") or 0)
        prod_tags  = _parse_highlights(p.get("highlights"))
        prod_cat   = (p.get("primary_category") or "").lower()

        norm_rating  = np.clip(rating / 5.0, 0.0, 1.0)
        norm_loves   = np.clip(loves / max_loves_in_set, 0.0, 1.0)
        norm_reviews = np.clip(reviews / max_reviews_in_set, 0.0, 1.0)
        price_score  = np.clip(1.0 - price / max_budget, 0.0, 1.0) if max_budget > 0 else 0.0

        skin_type_match = _tag_overlap(prod_tags, skin_type_targets)
        concern_match   = _tag_overlap(prod_tags, concern_targets)
        extra_tag_match = _tag_overlap(prod_tags, extra_tags)
        category_match  = 1.0 if (primary_cat == "all" or prod_cat == primary_cat) else 0.5

        cb_score = (
            W_SKIN_TYPE * skin_type_match
            + W_CONCERN   * concern_match
            + W_RATING    * norm_rating
            + W_LOVES     * norm_loves
            + W_REVIEWS   * norm_reviews
            + W_PRICE     * price_score
            + W_TAG_MATCH * extra_tag_match
            + W_CATEGORY  * category_match
        )

        scored.append({
            **p,
            "cb_score":          round(float(cb_score), 4),
            "_norm_rating":      round(float(norm_rating), 4),
            "_skin_type_match":  round(float(skin_type_match), 4),
            "_concern_match":    round(float(concern_match), 4),
            "_tag_match":        round(float(extra_tag_match), 4),
            "_price_score":      round(float(price_score), 4),
        })

    return scored


# ─────────────────────────────────────────────
# Stage 3 — Collaborative Filtering
# ─────────────────────────────────────────────

def collaborative_filter_score(products: list[dict], collab_data: list[dict]) -> list[dict]:
    """
    Enrich each product with a helpfulness-weighted CF score.
    collab_data comes from the product_collab_scores view.
    """
    collab_lookup = {row["product_id"]: row for row in collab_data}

    for p in products:
        row = collab_lookup.get(p["product_id"])

        if row and int(row.get("feedback_count", 0)) >= CF_MIN_FEEDBACK:
            avg_rating = float(row["avg_user_rating"])
            p["cf_score"]        = round(np.clip(avg_rating / 5.0, 0.0, 1.0), 4)
            p["feedback_count"]  = int(row["feedback_count"])
            p["recommend_rate"]  = round(float(row.get("recommend_rate") or 0), 4)
        else:
            p["cf_score"]       = 0.5
            p["feedback_count"] = 0
            p["recommend_rate"] = 0.0

    return products


# ─────────────────────────────────────────────
# Stage 4 — Hybrid Score Merge
# ─────────────────────────────────────────────

def merge_scores(products: list[dict]) -> list[dict]:
    for p in products:
        p["score"] = round(
            W_CONTENT * p.get("cb_score", 0.0)
            + W_COLLAB * p.get("cf_score", 0.5),
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
    candidates = rule_based_filter(products, user_profile)
    if not candidates:
        return []

    all_loves   = [int(p.get("loves_count") or 0) for p in candidates]
    all_reviews = [int(p.get("reviews") or 0) for p in candidates]

    candidates = content_based_score(candidates, user_profile, all_loves, all_reviews)
    candidates = collaborative_filter_score(candidates, collab_data or [])
    ranked     = merge_scores(candidates)

    return ranked[:top_n]
