"""
app.py - Streamlit UI for Facial Cosmetics Recommendation System
MSc Thesis Prototype — Entry point
"""

import streamlit as st
from database import fetch_products, insert_feedback
from recommendation_engine import run_recommendation_pipeline
from openai_service import generate_explanation

# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Cosmetics Recommender",
    page_icon="💄",
    layout="wide",
)

st.title("💄 Facial Cosmetics Recommendation System")
st.caption("MSc Thesis Prototype · Rule-Based + Content-Based + OpenAI")

# ─────────────────────────────────────────────
# Sidebar — User Profile Input
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("👤 Your Skin Profile")

    skin_type = st.selectbox(
        "Skin Type",
        options=["oily", "dry", "combination", "sensitive"],
        index=0,
    )

    concern = st.selectbox(
        "Primary Skin Concern",
        options=["acne", "aging", "hyperpigmentation", "dryness"],
        index=0,
    )

    ingredients_to_avoid = st.text_input(
        "Ingredients to Avoid (comma-separated)",
        placeholder="e.g. alcohol, fragrance, parabens",
    )

    max_budget = st.number_input(
        "Maximum Budget ($)",
        min_value=1.0,
        max_value=500.0,
        value=50.0,
        step=1.0,
    )

    run_button = st.button("🔍 Get Recommendations", use_container_width=True)

# ─────────────────────────────────────────────
# Main content
# ─────────────────────────────────────────────
if run_button:
    # Parse avoided ingredients into a list
    avoided = [i.strip() for i in ingredients_to_avoid.split(",") if i.strip()]

    user_profile = {
        "skin_type": skin_type,
        "concern": concern,
        "ingredients_to_avoid": avoided,
        "max_budget": max_budget,
    }

    with st.spinner("Fetching products from database…"):
        products = fetch_products()

    if not products:
        st.error("⚠️ Could not load products from the database. Check your Supabase credentials.")
        st.stop()

    with st.spinner("Running recommendation engine…"):
        top5 = run_recommendation_pipeline(products, user_profile)

    if not top5:
        st.warning(
            "😕 No products matched your criteria. "
            "Try adjusting your budget or removing some ingredients to avoid."
        )
        st.stop()

    st.success(f"✅ Found {len(top5)} product(s) matching your profile!")
    st.divider()

    # ── Display each recommendation ──────────────────────────────────────
    for rank, product in enumerate(top5, start=1):
        with st.container():
            col_info, col_score = st.columns([3, 1])

            with col_info:
                st.subheader(f"#{rank} — {product['name']}")
                st.markdown(f"**Brand:** {product['brand']}")
                st.markdown(f"**Price:** ${product['price']:.2f}  &nbsp;|&nbsp;  **Rating:** ⭐ {product['rating']}/5")
                st.markdown(f"**Suitable for:** `{product['skin_type']}`  &nbsp;|&nbsp;  **Targets:** `{product['concern']}`")

                with st.expander("🧪 Ingredients"):
                    st.write(product.get("ingredients", "N/A"))

            with col_score:
                score_pct = round(product["score"] * 100, 1)
                st.metric("Match Score", f"{score_pct}%")

            # ── OpenAI Explanation ───────────────────────────────────────
            with st.spinner(f"Generating AI explanation for {product['name']}…"):
                explanation = generate_explanation(
                    skin_type=skin_type,
                    concern=concern,
                    ingredients=product.get("ingredients", ""),
                    rating=product["rating"],
                    product_name=product["name"],
                )

            if explanation:
                st.info(f"🤖 **Why this product?**\n\n{explanation}")
            else:
                st.warning("AI explanation unavailable for this product.")

            # ── Feedback ─────────────────────────────────────────────────
            feedback_key = f"feedback_{product['id']}"
            user_rating = st.slider(
                f"Rate this recommendation (product #{rank})",
                min_value=1,
                max_value=5,
                value=3,
                key=feedback_key,
            )
            if st.button(f"Submit Feedback for #{rank}", key=f"btn_{product['id']}"):
                success = insert_feedback(product["id"], user_rating)
                if success:
                    st.success("Thank you for your feedback! 🙏")
                else:
                    st.error("Failed to save feedback. Please try again.")

            st.divider()

else:
    # Landing state
    st.info(
        "👈 Fill in your skin profile in the sidebar, then click **Get Recommendations** "
        "to receive personalised cosmetic suggestions."
    )
    st.markdown(
        """
        ### How it works
        1. **Rule-Based Filtering** — removes products that don't match your skin type, concern, budget, or contain avoided ingredients.
        2. **Content-Based Scoring** — ranks remaining products using a weighted formula (skin type match · concern match · rating · price).
        3. **OpenAI Explanation** — GPT generates a personalised 3-sentence rationale for each top-5 product.
        """
    )
