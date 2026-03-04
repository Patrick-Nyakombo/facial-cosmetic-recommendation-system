"""
app.py - Streamlit UI for Facial Cosmetics Recommendation System
MSc Thesis Prototype — Entry point (mobile-responsive)
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
# Page config — centered layout works better on mobile
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Cosmetics Recommender",
    page_icon="💄",
    layout="centered",   # centered > wide for mobile readability
)

# ─────────────────────────────────────────────
# Global responsive CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
/* ── Google Font ── */
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* ── Tighten default padding on small screens ── */
.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    max-width: 860px !important;
}

/* ── Product card ── */
.product-card {
    background: #FAFAFA;
    border: 1px solid #EBEBEB;
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1.2rem;
}

/* ── Rank badge ── */
.rank-badge {
    display: inline-block;
    background: #1A1A2E;
    color: #fff;
    font-size: 0.75rem;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 20px;
    margin-bottom: 6px;
    letter-spacing: 0.04em;
}

/* ── Product title ── */
.product-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: #1A1A2E;
    margin: 4px 0 2px 0;
    line-height: 1.3;
}

/* ── Meta row ── */
.meta-row {
    font-size: 0.85rem;
    color: #555;
    margin-bottom: 6px;
}

/* ── Score pill ── */
.score-pill {
    display: inline-block;
    background: #E8F5E9;
    color: #2E7D32;
    font-weight: 700;
    font-size: 0.9rem;
    padding: 4px 14px;
    border-radius: 20px;
    margin-bottom: 10px;
}

/* ── AI explanation box ── */
.ai-box {
    background: #EEF2FF;
    border-left: 4px solid #4F46E5;
    border-radius: 8px;
    padding: 0.85rem 1rem;
    font-size: 0.88rem;
    color: #1E1B4B;
    margin: 0.6rem 0;
    line-height: 1.55;
}

/* ── Auth card ── */
.auth-card {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 16px;
    padding: 1.8rem;
    margin-bottom: 1rem;
}

/* ── Section header ── */
.section-header {
    font-size: 1rem;
    font-weight: 700;
    color: #1A1A2E;
    margin-bottom: 0.8rem;
    letter-spacing: 0.02em;
}

/* ── History card ── */
.history-meta {
    font-size: 0.82rem;
    color: #777;
    margin-bottom: 0.3rem;
}

/* ── Make Streamlit buttons full width on mobile ── */
@media (max-width: 640px) {
    .stButton > button {
        width: 100% !important;
    }
    /* Stack columns on very small screens */
    [data-testid="column"] {
        min-width: 100% !important;
    }
}

/* ── Button style ── */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #1A1A2E !important;
}
[data-testid="stSidebar"] * {
    color: #E8E8F0 !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.08) !important;
    color: #fff !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    text-align: left !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.16) !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Session state defaults
# ─────────────────────────────────────────────
for key, default in {
    "user": None,
    "page": "login",
    "recommendations": None,
    "last_profile": None,
    "feedback_submitted": {},
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def set_page(page: str):
    st.session_state["page"] = page


# ═══════════════════════════════════════════════════════════════
# AUTH PAGE
# ═══════════════════════════════════════════════════════════════

def render_auth_page():
    st.markdown("""
        <div style='text-align:center; padding: 1.5rem 0 0.5rem 0;'>
            <div style='font-size:2.8rem;'>💄</div>
            <h1 style='font-size:1.6rem; font-weight:800; color:#1A1A2E; margin:0.3rem 0 0.2rem 0;'>
                Cosmetics Recommender
            </h1>
            <p style='color:#888; font-size:0.85rem; margin:0;'>
                MSc Thesis Prototype · Rule-Based + Content-Based + OpenAI
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.write("")

    # Use tabs instead of side-by-side columns → works perfectly on mobile
    tab_login, tab_signup = st.tabs(["🔐  Log In", "✨  Create Account"])

    with tab_login:
        st.write("")
        login_email    = st.text_input("Email address", key="login_email", placeholder="you@example.com")
        login_password = st.text_input("Password", key="login_password", type="password", placeholder="••••••••")
        st.write("")
        if st.button("Log In", use_container_width=True, type="primary"):
            if not login_email or not login_password:
                st.warning("Please enter your email and password.")
            else:
                ok, err = sign_in(login_email, login_password)
                if ok:
                    set_page("recommendations")
                    st.rerun()
                else:
                    st.error(f"Login failed: {err}")

    with tab_signup:
        st.write("")
        signup_email    = st.text_input("Email address", key="signup_email",    placeholder="you@example.com")
        signup_password = st.text_input("Password (min 6 chars)", key="signup_password", type="password", placeholder="••••••••")
        signup_confirm  = st.text_input("Confirm password", key="signup_confirm", type="password", placeholder="••••••••")
        st.write("")
        if st.button("Create Account", use_container_width=True, type="primary"):
            if not signup_email or not signup_password:
                st.warning("Please fill in all fields.")
            elif signup_password != signup_confirm:
                st.error("Passwords do not match.")
            elif len(signup_password) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                ok, err = sign_up(signup_email, signup_password)
                if ok:
                    st.success("✅ Account created! You can now log in.")
                else:
                    st.error(f"Sign-up failed: {err}")


# ═══════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════

def render_sidebar():
    user = get_current_user()
    with st.sidebar:
        st.markdown(f"<div style='font-size:0.8rem;opacity:0.7;margin-bottom:4px;'>Signed in as</div>", unsafe_allow_html=True)
        st.markdown(f"**{user['email']}**")
        st.divider()

        if st.button("💄  Recommendations", use_container_width=True):
            set_page("recommendations")
            st.rerun()

        if st.button("📋  My History", use_container_width=True):
            set_page("history")
            st.rerun()

        st.divider()
        if st.button("🚪  Log Out", use_container_width=True):
            sign_out()
            set_page("login")
            st.rerun()


# ═══════════════════════════════════════════════════════════════
# RECOMMENDATIONS PAGE
# ═══════════════════════════════════════════════════════════════

def render_recommendations_page():
    st.markdown("<h2 style='font-size:1.5rem;font-weight:800;color:#1A1A2E;margin-bottom:0.2rem;'>💄 Get Recommendations</h2>", unsafe_allow_html=True)
    st.caption("Fill in your skin profile in the sidebar and tap Get Recommendations.")

    with st.sidebar:
        st.markdown("### 🧴 Skin Profile")

        skin_type = st.selectbox("Skin Type", ["oily", "dry", "combination", "sensitive"])
        concern   = st.selectbox("Skin Concern", ["acne", "aging", "hyperpigmentation", "dryness"])
        ingredients_to_avoid = st.text_input("Avoid ingredients", placeholder="e.g. alcohol, fragrance")
        max_budget = st.number_input("Max Budget ($)", min_value=1.0, max_value=500.0, value=50.0, step=1.0)

        st.write("")
        run_button = st.button("🔍 Get Recommendations", use_container_width=True, type="primary")

    if run_button:
        avoided = [i.strip() for i in ingredients_to_avoid.split(",") if i.strip()]
        profile = {
            "skin_type": skin_type,
            "concern": concern,
            "ingredients_to_avoid": avoided,
            "max_budget": max_budget,
        }

        with st.spinner("Fetching products…"):
            products = fetch_products()

        if not products:
            st.error("⚠️ Could not load products. Check your Supabase credentials.")
            return

        with st.spinner("Running recommendation engine…"):
            top5 = run_recommendation_pipeline(products, profile)

        if not top5:
            st.warning("😕 No products matched your criteria. Try a higher budget or fewer restrictions.")
            return

        st.session_state["recommendations"]   = top5
        st.session_state["last_profile"]       = profile
        st.session_state["feedback_submitted"] = {}

        user = get_current_user()
        if user:
            save_recommendation_history(user["id"], profile, top5)

    # ── Render from session state ───────────────────────────────
    top5    = st.session_state.get("recommendations")
    profile = st.session_state.get("last_profile")

    if not top5:
        st.markdown("""
        <div style='background:#F8F8FF;border-radius:12px;padding:1.2rem 1.4rem;margin-top:1rem;border:1px solid #E0E0F0;'>
            <div style='font-weight:700;font-size:0.95rem;color:#1A1A2E;margin-bottom:0.6rem;'>How it works</div>
            <ol style='margin:0;padding-left:1.2rem;font-size:0.87rem;color:#444;line-height:1.8;'>
                <li><strong>Rule-Based Filtering</strong> — removes products that don't match your skin type, concern, budget, or contain avoided ingredients.</li>
                <li><strong>Weighted Scoring</strong> — ranks by skin type (40%) · concern (30%) · rating (20%) · price (10%).</li>
                <li><strong>AI Explanation</strong> — GPT writes a personalised 3-sentence rationale for each result.</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
        return

    skin_type = profile["skin_type"]
    concern   = profile["concern"]

    st.success(f"✅ Top {len(top5)} products for **{skin_type}** skin · **{concern}**")
    st.write("")

    for rank, product in enumerate(top5, start=1):
        pid   = product["id"]
        score = round(product["score"] * 100, 1)

        st.markdown(f"""
        <div class="product-card">
            <div class="rank-badge">#{rank}</div>
            <div class="product-title">{product['name']}</div>
            <div class="meta-row">
                {product['brand']} &nbsp;·&nbsp;
                ${float(product['price']):.2f} &nbsp;·&nbsp;
                ⭐ {product['rating']}/5
            </div>
            <div class="score-pill">Match: {score}%</div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("🧪 View Ingredients"):
            st.write(product.get("ingredients", "N/A"))

        # AI explanation (cached in session state)
        exp_key = f"explanation_{pid}"
        if exp_key not in st.session_state:
            with st.spinner("Generating AI explanation…"):
                st.session_state[exp_key] = generate_explanation(
                    skin_type=skin_type,
                    concern=concern,
                    ingredients=product.get("ingredients", ""),
                    rating=product["rating"],
                    product_name=product["name"],
                )

        explanation = st.session_state.get(exp_key)
        if explanation:
            st.markdown(f'<div class="ai-box">🤖 <strong>Why this product?</strong><br><br>{explanation}</div>', unsafe_allow_html=True)
        else:
            st.warning("AI explanation unavailable.")

        # Feedback
        already = st.session_state["feedback_submitted"].get(pid, False)
        if already:
            st.success("✅ Feedback submitted — thank you!")
        else:
            user_rating = st.slider(
                "How useful was this recommendation?",
                min_value=1, max_value=5, value=3,
                key=f"slider_{pid}",
            )
            if st.button("Submit Feedback", key=f"btn_{pid}"):
                ok = insert_feedback(pid, user_rating)
                if ok:
                    st.session_state["feedback_submitted"][pid] = True
                    st.rerun()
                else:
                    st.error("Failed to save feedback. Please try again.")

        st.write("")


# ═══════════════════════════════════════════════════════════════
# HISTORY PAGE
# ═══════════════════════════════════════════════════════════════

def render_history_page():
    st.markdown("<h2 style='font-size:1.5rem;font-weight:800;color:#1A1A2E;'>📋 My History</h2>", unsafe_allow_html=True)

    user = get_current_user()
    if not user:
        st.error("You must be logged in to view history.")
        return

    with st.spinner("Loading your history…"):
        history = fetch_recommendation_history(user["id"])

    if not history:
        st.info("No recommendation history yet. Head to **Recommendations** to get started!")
        return

    st.caption(f"{len(history)} session(s) on record")
    st.write("")

    for i, session in enumerate(history, start=1):
        profile  = session.get("profile", {})
        products = session.get("products", [])
        ts       = session.get("created_at", "")[:19].replace("T", " ")

        label = (
            f"Session {i} · {ts}  |  "
            f"{profile.get('skin_type','?').title()} · "
            f"{profile.get('concern','?').title()} · "
            f"${profile.get('max_budget',0):.0f} budget"
        )

        with st.expander(label, expanded=(i == 1)):
            # Profile chips — single column on mobile, 4 cols on desktop
            cols = st.columns(4)
            cols[0].metric("Skin Type", profile.get("skin_type", "—").title())
            cols[1].metric("Concern",   profile.get("concern",   "—").title())
            cols[2].metric("Budget",    f"${profile.get('max_budget', 0):.0f}")
            avoided = profile.get("ingredients_to_avoid", [])
            cols[3].metric("Avoided",   str(len(avoided)))

            if avoided:
                st.caption("Avoided: " + ", ".join(avoided))

            st.write("")
            for rank, p in enumerate(products, start=1):
                st.markdown(
                    f"**#{rank} {p.get('name','?')}** &nbsp;·&nbsp; "
                    f"{p.get('brand','')} &nbsp;·&nbsp; "
                    f"${float(p.get('price',0)):.2f} &nbsp;·&nbsp; "
                    f"⭐ {p.get('rating','?')}/5"
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
    if page == "history":
        render_history_page()
    else:
        render_recommendations_page()
