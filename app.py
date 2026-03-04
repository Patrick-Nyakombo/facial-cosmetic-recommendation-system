"""
app.py - Streamlit UI for Facial Cosmetics Recommendation System
MSc Thesis Prototype — Entry point

Pages:
  - Login / Sign Up
  - Recommendations (main engine)
  - History (past sessions)
"""

import streamlit as st
from auth import sign_in, sign_up, sign_out, get_current_user
from database import (
    fetch_products,
    insert_feedback,
    save_recommendation_history,
    fetch_recommendation_history,
)
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


# ─────────────────────────────────────────────
# Session state defaults
# ─────────────────────────────────────────────
if "user" not in st.session_state:
    st.session_state["user"] = None
if "page" not in st.session_state:
    st.session_state["page"] = "login"
# Store recommendations in session state so the page doesn't reset on feedback
if "recommendations" not in st.session_state:
    st.session_state["recommendations"] = None
if "last_profile" not in st.session_state:
    st.session_state["last_profile"] = None
# Track which products have already received feedback this session
if "feedback_submitted" not in st.session_state:
    st.session_state["feedback_submitted"] = {}


def set_page(page: str):
    st.session_state["page"] = page


# ═══════════════════════════════════════════════════════════════
# AUTH PAGE  (Login / Sign Up)
# ═══════════════════════════════════════════════════════════════

def render_auth_page():
    st.title("💄 Facial Cosmetics Recommendation System")
    st.caption("This is a Prototype! Product in Development")
    st.divider()

    col_l, col_r = st.columns(2, gap="large")

    # ── Login ──────────────────────────────────────────────────
    with col_l:
        st.subheader("🔐 Log In")
        login_email    = st.text_input("Email",    key="login_email")
        login_password = st.text_input("Password", key="login_password", type="password")

        if st.button("Log In", use_container_width=True):
            if not login_email or not login_password:
                st.warning("Please enter your email and password.")
            else:
                ok, err = sign_in(login_email, login_password)
                if ok:
                    set_page("recommendations")
                    st.rerun()
                else:
                    st.error(f"Login failed: {err}")

    # ── Sign Up ────────────────────────────────────────────────
    with col_r:
        st.subheader("✨ Create Account")
        signup_email    = st.text_input("Email",           key="signup_email")
        signup_password = st.text_input("Password (min 6 chars)", key="signup_password", type="password")
        signup_confirm  = st.text_input("Confirm Password", key="signup_confirm",  type="password")

        if st.button("Create Account", use_container_width=True):
            if not signup_email or not signup_password:
                st.warning("Please fill in all fields.")
            elif signup_password != signup_confirm:
                st.error("Passwords do not match.")
            elif len(signup_password) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                ok, err = sign_up(signup_email, signup_password)
                if ok:
                    st.success("✅ Account created! Please check your email to confirm, then log in.")
                else:
                    st.error(f"Sign-up failed: {err}")


# ═══════════════════════════════════════════════════════════════
# SIDEBAR (shown when logged in)
# ═══════════════════════════════════════════════════════════════

def render_sidebar():
    user = get_current_user()
    with st.sidebar:
        st.markdown(f"👤 **{user['email']}**")
        st.divider()

        if st.button("🔍 Recommendations", use_container_width=True):
            set_page("recommendations")
            st.rerun()

        if st.button("📋 My History", use_container_width=True):
            set_page("history")
            st.rerun()

        st.divider()
        if st.button("🚪 Log Out", use_container_width=True):
            sign_out()
            set_page("login")
            st.rerun()


# ═══════════════════════════════════════════════════════════════
# RECOMMENDATIONS PAGE
# ═══════════════════════════════════════════════════════════════

def render_recommendations_page():
    st.title("💄 Get Recommendations")

    # ── Profile inputs (always visible) ────────────────────────
    with st.sidebar:
        st.header("🧴 Your Skin Profile")

        skin_type = st.selectbox(
            "Skin Type",
            options=["oily", "dry", "combination", "sensitive"],
        )
        concern = st.selectbox(
            "Primary Skin Concern",
            options=["acne", "aging", "hyperpigmentation", "dryness"],
        )
        ingredients_to_avoid = st.text_input(
            "Ingredients to Avoid (comma-separated)",
            placeholder="e.g. alcohol, fragrance",
        )
        max_budget = st.number_input(
            "Maximum Budget ($)",
            min_value=1.0, max_value=500.0, value=50.0, step=1.0,
        )

        run_button = st.button("🔍 Get Recommendations", use_container_width=True)

    # ── Run engine only when button clicked ────────────────────
    if run_button:
        avoided = [i.strip() for i in ingredients_to_avoid.split(",") if i.strip()]
        profile = {
            "skin_type":            skin_type,
            "concern":              concern,
            "ingredients_to_avoid": avoided,
            "max_budget":           max_budget,
        }

        with st.spinner("Fetching products…"):
            products = fetch_products()

        if not products:
            st.error("⚠️ Could not load products. Check your Supabase credentials.")
            return

        with st.spinner("Running recommendation engine…"):
            top5 = run_recommendation_pipeline(products, profile)

        if not top5:
            st.warning("😕 No products matched your criteria. Try adjusting your budget or filters.")
            return

        # ── Persist results in session state ───────────────────
        # This means a feedback button click won't re-run the engine
        st.session_state["recommendations"] = top5
        st.session_state["last_profile"]    = profile
        st.session_state["feedback_submitted"] = {}  # reset on new search

        # Save this session to the user's history
        user = get_current_user()
        if user:
            save_recommendation_history(user["id"], profile, top5)

    # ── Render results from session state ──────────────────────
    top5    = st.session_state.get("recommendations")
    profile = st.session_state.get("last_profile")

    if not top5:
        st.info("👈 Fill in your skin profile and click **Get Recommendations**.")
        st.markdown("""
        ### How it works
        1. **Rule-Based Filtering** — hard constraints on skin type, concern, budget, and avoided ingredients.
        2. **Content-Based Scoring** — weighted formula: skin type (40%) · concern (30%) · rating (20%) · price (10%).
        3. **OpenAI Explanation** — GPT writes a personalised 3-sentence rationale for each result.
        """)
        return

    skin_type = profile["skin_type"]
    concern   = profile["concern"]

    st.success(f"✅ Top {len(top5)} products for **{skin_type}** skin targeting **{concern}**")
    st.divider()

    for rank, product in enumerate(top5, start=1):
        product_id = product["id"]

        with st.container():
            col_info, col_score = st.columns([3, 1])

            with col_info:
                st.subheader(f"#{rank} — {product['name']}")
                st.markdown(f"**Brand:** {product['brand']}")
                st.markdown(
                    f"**Price:** ${float(product['price']):.2f} &nbsp;|&nbsp; "
                    f"**Rating:** ⭐ {product['rating']}/5"
                )
                with st.expander("🧪 Ingredients"):
                    st.write(product.get("ingredients", "N/A"))

            with col_score:
                st.metric("Match Score", f"{round(product['score'] * 100, 1)}%")

            # ── OpenAI Explanation ──────────────────────────────
            explanation_key = f"explanation_{product_id}"
            if explanation_key not in st.session_state:
                with st.spinner(f"Generating AI explanation for {product['name']}…"):
                    st.session_state[explanation_key] = generate_explanation(
                        skin_type=skin_type,
                        concern=concern,
                        ingredients=product.get("ingredients", ""),
                        rating=product["rating"],
                        product_name=product["name"],
                    )

            explanation = st.session_state.get(explanation_key)
            if explanation:
                st.info(f"🤖 **Why this product?**\n\n{explanation}")
            else:
                st.warning("AI explanation unavailable.")

            # ── Feedback ────────────────────────────────────────
            # Check if feedback already submitted for this product this session
            already_submitted = st.session_state["feedback_submitted"].get(product_id, False)

            if already_submitted:
                st.success("✅ Feedback submitted — thank you!")
            else:
                user_rating = st.slider(
                    f"How useful was this recommendation?",
                    min_value=1, max_value=5, value=3,
                    key=f"slider_{product_id}",
                )
                if st.button(
                    f"Submit Feedback",
                    key=f"btn_{product_id}",
                ):
                    ok = insert_feedback(product_id, user_rating)
                    if ok:
                        # Mark as submitted so we show the success message
                        # without re-running the whole engine
                        st.session_state["feedback_submitted"][product_id] = True
                        st.rerun()
                    else:
                        st.error("Failed to save feedback. Please try again.")

            st.divider()


# ═══════════════════════════════════════════════════════════════
# HISTORY PAGE
# ═══════════════════════════════════════════════════════════════

def render_history_page():
    st.title("📋 My Recommendation History")

    user = get_current_user()
    if not user:
        st.error("You must be logged in to view history.")
        return

    with st.spinner("Loading your history…"):
        history = fetch_recommendation_history(user["id"])

    if not history:
        st.info("You have no recommendation history yet. Go to **Recommendations** to get started!")
        return

    st.caption(f"{len(history)} session(s) found")
    st.divider()

    for i, session in enumerate(history, start=1):
        profile  = session.get("profile", {})
        products = session.get("products", [])
        ts       = session.get("created_at", "")[:19].replace("T", " ")  # friendly timestamp

        with st.expander(
            f"Session {i} — {ts} &nbsp;|&nbsp; "
            f"**{profile.get('skin_type', '?')}** skin · **{profile.get('concern', '?')}** · "
            f"Budget ${profile.get('max_budget', '?')}",
            expanded=(i == 1),  # auto-expand the most recent session
        ):
            # Profile summary
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Skin Type",  profile.get("skin_type", "—"))
            col2.metric("Concern",    profile.get("concern", "—"))
            col3.metric("Budget",     f"${profile.get('max_budget', 0):.0f}")
            avoided = profile.get("ingredients_to_avoid", [])
            col4.metric("Avoided Ingredients", len(avoided))

            if avoided:
                st.caption(f"Avoided: {', '.join(avoided)}")

            st.markdown("**Recommended products:**")
            for rank, product in enumerate(products, start=1):
                st.markdown(
                    f"**#{rank} {product.get('name', 'Unknown')}** — "
                    f"{product.get('brand', '')} · "
                    f"${float(product.get('price', 0)):.2f} · "
                    f"⭐ {product.get('rating', '?')}/5"
                )


# ═══════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════

user = get_current_user()
page = st.session_state.get("page", "login")

if user is None:
    render_auth_page()
else:
    render_sidebar()
    if page == "recommendations":
        render_recommendations_page()
    elif page == "history":
        render_history_page()
    else:
        render_recommendations_page()
