"""
app.py - Streamlit UI for Facial Cosmetics Recommendation System
MSc Thesis Prototype

Pages:
  - Login / Register (with skin profile capture at signup — FR-1)
  - Recommendations  (skin type + concern pre-filled from profile — FR-3)
  - Product Detail   (dedicated full product view — FR-3 / Figure 4.8)
  - My History       (past recommendation sessions)
  - My Profile       (edit skin type & concerns — FR-1)
  - Admin Panel      (product stats + feedback table — FR-2 / Figure 4.9)
"""

import json
import ast
import streamlit as st
from PIL import Image
from auth import sign_in, sign_up, sign_out, get_current_user, is_admin
from database import (
    fetch_products, fetch_collab_scores, insert_feedback,
    save_recommendation_history, fetch_recommendation_history,
    save_user_profile, fetch_user_profile,
    fetch_all_feedback, fetch_product_stats,
)
from recommendation_engine import run_recommendation_pipeline
from openai_service import generate_explanation
from skin_analyzer import classify_skin_type, get_skin_analysis_tips

st.set_page_config(page_title="Cosmetics Recommender", page_icon="💄", layout="centered")

# ═══════════════════════════════════════════════════════════════
# GLOBAL CSS
# ═══════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.block-container {
    padding-top: 1.5rem !important; padding-bottom: 2rem !important;
    padding-left: 1rem !important;  padding-right: 1rem !important;
    max-width: 880px !important;
}
.product-card {
    background: #FAFAFA; border: 1px solid #EBEBEB;
    border-radius: 14px; padding: 1.2rem 1.4rem; margin-bottom: 0.6rem;
}
.detail-card {
    background: #fff; border: 1.5px solid #E0E0F0;
    border-radius: 16px; padding: 1.6rem 1.8rem; margin-bottom: 1rem;
}
.rank-badge {
    display: inline-block; background: #1A1A2E; color: #fff;
    font-size: 0.72rem; font-weight: 700; padding: 3px 10px;
    border-radius: 20px; margin-bottom: 6px; letter-spacing: 0.04em;
}
.cat-badge {
    display: inline-block; background: #F3E8FF; color: #6B21A8;
    font-size: 0.72rem; font-weight: 600; padding: 3px 10px;
    border-radius: 20px; margin-left: 6px;
}
.tag-badge {
    display: inline-block; background: #FEF9C3; color: #854D0E;
    font-size: 0.70rem; font-weight: 600; padding: 2px 8px;
    border-radius: 20px; margin: 2px 3px 2px 0;
}
.skin-badge {
    display: inline-block; background: #ECFDF5; color: #065F46;
    font-size: 0.70rem; font-weight: 600; padding: 2px 8px;
    border-radius: 20px; margin: 2px 3px 2px 0;
}
.product-title { font-size: 1.1rem; font-weight: 700; color: #1A1A2E; margin: 4px 0 2px 0; }
.meta-row { font-size: 0.84rem; color: #555; margin-bottom: 6px; }
.score-pill {
    display: inline-block; background: #E8F5E9; color: #2E7D32;
    font-weight: 700; font-size: 0.85rem; padding: 3px 12px; border-radius: 20px;
}
.cf-pill {
    display: inline-block; background: #EFF6FF; color: #1D4ED8;
    font-weight: 600; font-size: 0.78rem; padding: 3px 10px;
    border-radius: 20px; margin-left: 6px;
}
.ai-box {
    background: #EEF2FF; border-left: 4px solid #4F46E5; border-radius: 8px;
    padding: 0.85rem 1rem; font-size: 0.87rem; color: #1E1B4B;
    margin: 0.6rem 0; line-height: 1.6;
}
.score-breakdown {
    background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 8px;
    padding: 0.7rem 1rem; font-size: 0.8rem; color: #374151; margin: 0.4rem 0;
}
.admin-stat {
    background: #F8FAFF; border: 1px solid #DBEAFE; border-radius: 10px;
    padding: 0.9rem 1.1rem; text-align: center;
}
.cnn-result-box {
    background: linear-gradient(135deg, #F0FDF4 0%, #ECFDF5 100%);
    border: 1.5px solid #6EE7B7; border-radius: 14px;
    padding: 1.2rem 1.4rem; margin: 0.8rem 0;
}
.cnn-suggestion-box {
    background: #FFFBEB; border: 1.5px solid #FCD34D;
    border-radius: 14px; padding: 1.2rem 1.4rem; margin: 0.8rem 0;
}
@media (max-width: 640px) { .stButton > button { width: 100% !important; } }
.stButton > button { border-radius: 10px !important; font-weight: 600 !important; }
[data-testid="stSidebar"] { background: #1A1A2E !important; }
[data-testid="stSidebar"] * { color: #E8E8F0 !important; }
[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.08) !important; color: #fff !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
}
[data-testid="stSidebar"] .stButton > button:hover { background: rgba(255,255,255,0.16) !important; }
</style>
""", unsafe_allow_html=True)

# ── Session defaults ─────────────────────────────────────────────
for key, default in {
    "user": None, "page": "login",
    "recommendations": None, "last_profile": None,
    "feedback_submitted": {}, "feedback_reviews": {},
    "_products_cache": None,
    "detail_product": None,
    "user_profile": {"display_name": "", "skin_type": "", "skin_concerns": []},
    "is_admin": False,
    "_trigger_run": False,
    "_run_profile": {},
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


SKIN_TYPES   = ["", "oily", "dry", "combination", "sensitive"]
SKIN_CONCERNS = ["acne", "aging", "hyperpigmentation", "dryness"]
ADMIN_EMAIL  = "admin@cosmeticsrecommender.com"   # override via admin_users table


def set_page(p):
    st.session_state["page"] = p


def _parse_highlights(raw) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(t).strip() for t in raw]
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(t).strip() for t in parsed]
    except Exception:
        pass
    try:
        parsed = ast.literal_eval(raw)
        if isinstance(parsed, list):
            return [str(t).strip() for t in parsed]
    except Exception:
        pass
    return []


def _get_filter_options(products: list[dict]) -> dict:
    primary_cats   = sorted({p.get("primary_category") or "" for p in products if p.get("primary_category")})
    secondary_cats = sorted({p.get("secondary_category") or "" for p in products if p.get("secondary_category")})
    all_tags: set[str] = set()
    for p in products:
        for t in _parse_highlights(p.get("highlights")):
            if t:
                all_tags.add(t)
    return {
        "primary_cats":   ["all"] + primary_cats,
        "secondary_cats": ["all"] + secondary_cats,
        "all_tags":       sorted(all_tags),
    }


# ═══════════════════════════════════════════════════════════════
# AUTH PAGE  — Login + Registration with skin profile
# ═══════════════════════════════════════════════════════════════

def render_auth_page():
    st.markdown("""
        <div style='text-align:center;padding:1.5rem 0 0.5rem 0;'>
            <div style='font-size:2.8rem;'>💄</div>
            <h1 style='font-size:1.6rem;font-weight:800;color:#1A1A2E;margin:0.3rem 0 0.2rem 0;'>
                Cosmetics Recommender</h1>
            <p style='color:#888;font-size:0.85rem;margin:0;'>
                MSc Thesis Prototype · Rule-Based + Content-Based + Collaborative + OpenAI</p>
        </div>""", unsafe_allow_html=True)
    st.write("")

    tab_login, tab_signup = st.tabs(["🔐  Log In", "✨  Create Account"])

    with tab_login:
        st.write("")
        email = st.text_input("Email address", key="login_email", placeholder="you@example.com")
        pwd   = st.text_input("Password", key="login_password", type="password", placeholder="••••••••")
        st.write("")
        if st.button("Log In", use_container_width='stretch', type="primary"):
            if not email or not pwd:
                st.warning("Please enter your email and password.")
            else:
                ok, err = sign_in(email, pwd)
                if ok:
                    set_page("recommendations")
                    st.rerun()
                else:
                    st.error(f"Login failed: {err}")

    with tab_signup:
        st.write("")
        st.markdown("**Account details**")
        s_name  = st.text_input("Display name",       key="signup_name",     placeholder="Jane")
        s_email = st.text_input("Email address",      key="signup_email",    placeholder="you@example.com")
        s_pwd   = st.text_input("Password (min 6)",   key="signup_password", type="password", placeholder="••••••••")
        s_conf  = st.text_input("Confirm password",   key="signup_confirm",  type="password", placeholder="••••••••")

        st.write("")
        st.markdown("**Skin profile** *(helps personalise recommendations)*")
        s_skin_type = st.selectbox(
            "Skin type", SKIN_TYPES, key="signup_skin_type",
            format_func=lambda x: "Select skin type…" if x == "" else x.title(),
        )
        s_concerns = st.multiselect(
            "Skin concerns", SKIN_CONCERNS, key="signup_concerns",
            format_func=str.title,
        )

        st.write("")
        if st.button("Create Account", use_container_width='stretch', type="primary"):
            if not s_email or not s_pwd:
                st.warning("Please fill in all required fields.")
            elif s_pwd != s_conf:
                st.error("Passwords do not match.")
            elif len(s_pwd) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                ok, err = sign_up(
                    email=s_email, password=s_pwd,
                    display_name=s_name,
                    skin_type=s_skin_type,
                    skin_concerns=s_concerns,
                )
                if ok:
                    st.success("✅ Account created! Please log in.")
                else:
                    st.error(f"Sign-up failed: {err}")


# ═══════════════════════════════════════════════════════════════
# SIDEBAR FILTER HELPER  — only rendered on recommendations page
# ═══════════════════════════════════════════════════════════════

def _render_recommendation_sidebar_filters(stored_profile: dict) -> None:
    """Render recommendation filter widgets inside the sidebar."""
    if st.session_state["_products_cache"] is None:
        st.session_state["_products_cache"] = fetch_products()

    all_products = st.session_state["_products_cache"] or []
    opts = _get_filter_options(all_products) if all_products else {
        "primary_cats": ["all"], "secondary_cats": ["all"], "all_tags": []
    }

    default_skin     = stored_profile.get("skin_type", "")
    default_concerns = stored_profile.get("skin_concerns", [])

    st.markdown("### 🧴 Skin Profile")
    skin_type = st.selectbox(
        "Skin type", SKIN_TYPES,
        index=SKIN_TYPES.index(default_skin) if default_skin in SKIN_TYPES else 0,
        format_func=lambda x: "Not specified" if x == "" else x.title(),
        help="Pre-filled from your profile.",
        key="sb_skin_type",
    )
    skin_concerns = st.multiselect(
        "Skin concerns", SKIN_CONCERNS,
        default=[c for c in default_concerns if c in SKIN_CONCERNS],
        format_func=str.title,
        key="sb_skin_concerns",
    )

    st.markdown("### 🗂️ Category")
    primary_cat = st.selectbox(
        "Primary category", opts["primary_cats"],
        format_func=lambda c: "🛍️ All Categories" if c == "all" else c,
        key="sb_primary_cat",
    )
    if primary_cat != "all":
        sec_opts = ["all"] + sorted({
            p.get("secondary_category") or ""
            for p in all_products
            if (p.get("primary_category") or "").lower() == primary_cat.lower()
            and p.get("secondary_category")
        })
    else:
        sec_opts = opts["secondary_cats"]
    secondary_cat = st.selectbox(
        "Sub-category (optional)", sec_opts,
        format_func=lambda c: "All" if c == "all" else c,
        key="sb_secondary_cat",
    )

    st.markdown("### 🏷️ Extra Tags")
    relevant_tags = sorted({
        tag
        for p in all_products
        if primary_cat == "all" or (p.get("primary_category") or "").lower() == primary_cat.lower()
        for tag in _parse_highlights(p.get("highlights"))
    }) if all_products else opts["all_tags"]
    selected_tags = st.multiselect(
        "Optional highlights to match", relevant_tags,
        placeholder="e.g. Vegan, Layerable…",
        key="sb_selected_tags",
    )

    st.markdown("### ⚙️ Filters")
    ingredients_to_avoid = st.text_input(
        "Avoid ingredients", placeholder="e.g. alcohol, fragrance",
        key="sb_ingredients",
    )
    max_budget = st.number_input(
        "Max Budget ($)", min_value=1.0, max_value=1000.0,
        value=100.0, step=5.0, key="sb_max_budget",
    )
    include_oos = st.checkbox(
        "Include out-of-stock products", value=False, key="sb_include_oos",
    )

    st.write("")
    if st.button("🔍 Get Recommendations", use_container_width='stretch',
                 type="primary", key="sb_run_button"):
        avoided = [i.strip() for i in ingredients_to_avoid.split(",") if i.strip()]
        st.session_state["_run_profile"] = {
            "skin_type":            skin_type,
            "skin_concerns":        skin_concerns,
            "primary_category":     primary_cat,
            "secondary_category":   secondary_cat,
            "tags_to_match":        selected_tags,
            "ingredients_to_avoid": avoided,
            "max_budget":           max_budget,
            "include_out_of_stock": include_oos,
        }
        st.session_state["_trigger_run"] = True


# ═══════════════════════════════════════════════════════════════
# SIDEBAR NAV
# ═══════════════════════════════════════════════════════════════

def render_sidebar():
    user    = get_current_user()
    profile = st.session_state.get("user_profile", {})
    name    = profile.get("display_name") or user["email"].split("@")[0]
    page    = st.session_state.get("page", "recommendations")

    with st.sidebar:
        st.markdown("<div style='font-size:0.75rem;opacity:0.6;'>Signed in as</div>", unsafe_allow_html=True)
        st.markdown(f"**{name}**")
        skin = profile.get("skin_type", "")
        if skin:
            st.markdown(f"<span class='skin-badge'>🧴 {skin.title()} skin</span>", unsafe_allow_html=True)
        st.divider()

        if st.button("💄  Recommendations", use_container_width='stretch'):
            set_page("recommendations"); st.rerun()
        if st.button("📋  My History",      use_container_width='stretch'):
            set_page("history"); st.rerun()
        if st.button("👤  My Profile",      use_container_width='stretch'):
            set_page("profile"); st.rerun()

        if is_admin():
            st.divider()
            if st.button("🛠️  Admin Panel", use_container_width='stretch'):
                set_page("admin"); st.rerun()

        st.divider()
        if st.button("🚪  Log Out", use_container_width='stretch'):
            sign_out(); set_page("login"); st.rerun()

        # ── Recommendation filters — only shown on recommendations page ──
        if page == "recommendations":
            _render_recommendation_sidebar_filters(profile)


# ═══════════════════════════════════════════════════════════════
# PROFILE PAGE  — edit skin type & concerns (FR-1)
# ═══════════════════════════════════════════════════════════════

def _render_cnn_result(result: dict) -> None:
    """Render the skin analysis result card."""
    if result.get("error"):
        st.warning(f"⚠️ {result['error']}")
        return

    skin_type_detected = result.get("skin_type")
    if not skin_type_detected:
        return

    confidence = result["confidence"]
    reasoning  = result.get("reasoning", "")
    signs      = result.get("raw_scores", {})

    st.markdown(
        f'<div class="cnn-result-box">'
        f'<div style="font-size:0.8rem;color:#065F46;font-weight:600;margin-bottom:4px;">🤖 AI Analysis Complete</div>'
        f'<div style="font-size:1.3rem;font-weight:800;color:#1A1A2E;">{skin_type_detected.title()} Skin</div>'
        f'<div style="font-size:0.82rem;color:#374151;margin-top:4px;">Confidence: <strong>{confidence:.0%}</strong></div>'
        + (f'<div style="font-size:0.82rem;color:#555;margin-top:6px;font-style:italic;">{reasoning}</div>' if reasoning else "")
        + f'</div>',
        unsafe_allow_html=True,
    )

    if signs:
        st.markdown(
            "<div style='font-size:0.8rem;color:#374151;margin-top:4px;'>"
            "<strong>Signs observed:</strong> " + " · ".join(signs.keys()) + "</div>",
            unsafe_allow_html=True,
        )


def _run_analysis(image: Image.Image, cache_key: str) -> dict:
    """Run CNN analysis and cache the result by cache_key."""
    if st.session_state.get("_last_skin_file") != cache_key:
        with st.spinner("🧠 Analysing skin type with CNN model…"):
            result = classify_skin_type(image)
        st.session_state["cnn_skin_result"]    = result
        st.session_state["_last_skin_file"]    = cache_key
        st.session_state["cnn_skin_suggestion"] = result.get("skin_type")
    return st.session_state.get("cnn_skin_result", {})


def render_profile_page():
    user    = get_current_user()
    profile = st.session_state.get("user_profile", {})

    st.markdown("<h2 style='font-size:1.45rem;font-weight:800;color:#1A1A2E;'>👤 My Profile</h2>",
                unsafe_allow_html=True)
    st.caption("Your skin profile personalises your recommendations.")
    st.write("")

    # ── Display name ─────────────────────────────────────────────
    display_name = st.text_input("Display name", value=profile.get("display_name", ""),
                                 key="prof_display_name")
    st.write("")
    st.divider()

    # ── AI Skin Analysis ─────────────────────────────────────────
    st.markdown("### 🔬 AI Skin Type Analysis")
    st.markdown(
        "<div style='font-size:0.82rem;color:#555;background:#F8F8FF;border-radius:8px;"
        "padding:0.6rem 0.9rem;margin-bottom:1rem;border:1px solid #E0E0F0;'>"
        "📸 <strong>Tips:</strong> Natural daylight · No heavy makeup · Face camera directly · No filters"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Option 1: Upload ─────────────────────────────────────────
    st.markdown("**Upload a photo**")
    uploaded_file = st.file_uploader(
        "Choose a face photo (JPG, PNG or WebP)",
        type=["jpg", "jpeg", "png", "webp"],
        key="skin_photo_upload",
    )
    if uploaded_file is not None:
        image     = Image.open(uploaded_file)
        cache_key = f"upload_{uploaded_file.name}_{uploaded_file.size}"
        col_img, col_res = st.columns([1, 2])
        with col_img:
            st.image(image, caption="Your photo", width="stretch")
        with col_res:
            result = _run_analysis(image, cache_key)
            _render_cnn_result(result)
        st.write("")

    # ── Option 2: Webcam ─────────────────────────────────────────
    st.markdown("**Or use your webcam**")
    webcam_photo = st.camera_input("Take a photo", key="webcam_capture")
    if webcam_photo is not None:
        image     = Image.open(webcam_photo)
        cache_key = f"webcam_{webcam_photo.size}"
        col_i, col_r = st.columns([1, 2])
        with col_i:
            st.image(image, caption="Captured", width="stretch")
        with col_r:
            result = _run_analysis(image, cache_key)
            _render_cnn_result(result)

    # ── CNN confirmation ─────────────────────────────────────────
    cnn_suggestion = st.session_state.get("cnn_skin_suggestion")
    cnn_result     = st.session_state.get("cnn_skin_result", {})
    if cnn_suggestion and not cnn_result.get("error"):
        st.write("")
        st.markdown(
            f'<div class="cnn-suggestion-box">'
            f'<div style="font-size:0.9rem;font-weight:700;color:#92400E;margin-bottom:4px;">'
            f'🤖 Detected: <strong>{cnn_suggestion.title()} Skin</strong>'
            f' ({cnn_result.get("confidence", 0):.0%} confidence)</div>'
            f'<div style="font-size:0.82rem;color:#78350F;">Apply this to pre-fill the skin type below, or dismiss.</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        col_a, col_d = st.columns([1, 1])
        with col_a:
            if st.button(f"✅ Apply — {cnn_suggestion.title()} skin",
                         use_container_width='stretch', type="primary", key="cnn_accept"):
                st.session_state["cnn_confirmed"] = cnn_suggestion
                st.rerun()
        with col_d:
            if st.button("❌ Dismiss", use_container_width='stretch', key="cnn_reject"):
                for k in ["cnn_skin_suggestion", "cnn_skin_result", "_last_skin_file", "cnn_confirmed"]:
                    st.session_state.pop(k, None)
                st.rerun()

    if st.session_state.get("cnn_confirmed"):
        st.success(f"✅ CNN result applied: **{st.session_state['cnn_confirmed'].title()} skin** — pre-filled below.")

    st.divider()

    # ── Skin type & concerns ─────────────────────────────────────
    st.markdown("### 🧴 Skin Type & Concerns")
    confirmed_skin = st.session_state.get("cnn_confirmed") or profile.get("skin_type", "")
    skin_idx       = SKIN_TYPES.index(confirmed_skin) if confirmed_skin in SKIN_TYPES else 0

    skin_type = st.selectbox(
        "Skin type", SKIN_TYPES, index=skin_idx,
        format_func=lambda x: "Not specified" if x == "" else x.title(),
        key="prof_skin_type",
    )
    skin_concerns = st.multiselect(
        "Skin concerns", SKIN_CONCERNS,
        default=[c for c in profile.get("skin_concerns", []) if c in SKIN_CONCERNS],
        format_func=str.title,
        key="prof_skin_concerns",
    )

    st.write("")
    if st.button("💾 Save Profile", use_container_width='stretch', type="primary", key="save_profile_btn"):
        ok = save_user_profile(user["id"], display_name, skin_type, skin_concerns)
        if ok:
            st.session_state["user_profile"] = {
                "display_name":  display_name,
                "skin_type":     skin_type,
                "skin_concerns": skin_concerns,
            }
            for k in ["cnn_skin_suggestion", "cnn_skin_result", "_last_skin_file", "cnn_confirmed"]:
                st.session_state.pop(k, None)
            st.success("✅ Profile saved!")
        else:
            st.error("Failed to save profile.")


# ═══════════════════════════════════════════════════════════════
# PRODUCT DETAIL PAGE  (FR-3, Figure 4.8)
# ═══════════════════════════════════════════════════════════════

def render_product_detail_page():
    product = st.session_state.get("detail_product")
    if not product:
        st.warning("No product selected.")
        if st.button("← Back to Recommendations"):
            set_page("recommendations"); st.rerun()
        return

    if st.button("← Back to Recommendations"):
        set_page("recommendations"); st.rerun()

    st.write("")

    pid       = product.get("product_id", "")
    p_name    = product.get("product_name", "Unknown Product")
    brand     = product.get("brand_name", "")
    price     = float(product.get("price_usd") or 0)
    rating    = float(product.get("rating") or 0)
    loves     = int(product.get("loves_count") or 0)
    reviews   = int(product.get("reviews") or 0)
    size      = product.get("size") or ""
    p_cat     = product.get("primary_category") or ""
    s_cat     = product.get("secondary_category") or ""
    t_cat     = product.get("tertiary_category") or ""
    prod_tags = _parse_highlights(product.get("highlights"))
    ingredients = product.get("ingredients") or "Not available"
    score     = round(product.get("score", 0) * 100, 1)
    cf_score  = round(product.get("cf_score", 0) * 100, 1)
    fb_count  = product.get("feedback_count", 0)
    rec_rate  = round((product.get("recommend_rate") or 0) * 100)

    # Category breadcrumb
    cat_crumb = " › ".join(c for c in [p_cat, s_cat, t_cat] if c)

    tags_html = "".join(f'<span class="tag-badge">{t}</span>' for t in prod_tags)

    badges = ""
    if int(product.get("sephora_exclusive") or 0):
        badges += ' <span style="background:#FFE4E6;color:#9F1239;font-size:0.72rem;font-weight:700;padding:3px 9px;border-radius:20px;">Sephora Exclusive</span>'
    if int(product.get("new") or 0):
        badges += ' <span style="background:#DCFCE7;color:#14532D;font-size:0.72rem;font-weight:700;padding:3px 9px;border-radius:20px;">New</span>'
    if int(product.get("limited_edition") or 0):
        badges += ' <span style="background:#FEF3C7;color:#92400E;font-size:0.72rem;font-weight:700;padding:3px 9px;border-radius:20px;">Limited Edition</span>'
    if int(product.get("online_only") or 0):
        badges += ' <span style="background:#EFF6FF;color:#1E40AF;font-size:0.72rem;font-weight:700;padding:3px 9px;border-radius:20px;">Online Only</span>'

    size_cell   = (f'<div><div style="font-size:0.75rem;color:#888;">Size</div>'
                   f'<div style="font-size:1rem;font-weight:600;color:#1A1A2E;">{size}</div></div>') if size else ""
    cf_label    = f"({fb_count} ratings)" if fb_count else "(new)"
    rec_pill    = (f'<span style="display:inline-block;background:#FDF4FF;color:#7E22CE;'
                   f'font-size:0.78rem;font-weight:600;padding:3px 10px;border-radius:20px;margin-left:6px;">'
                   f'👍 {rec_rate}% recommend</span>') if fb_count else ""

    detail_html = (
        '<div class="detail-card">'
        f'<div style="margin-bottom:8px;"><span class="cat-badge">{cat_crumb}</span>{badges}</div>'
        f'<div style="font-size:1.5rem;font-weight:800;color:#1A1A2E;margin:8px 0 4px 0;">{p_name}</div>'
        f'<div style="font-size:1rem;color:#555;margin-bottom:12px;">{brand}</div>'
        '<div style="display:flex;gap:2rem;flex-wrap:wrap;margin-bottom:14px;">'
        f'<div><div style="font-size:0.75rem;color:#888;">Price</div><div style="font-size:1.2rem;font-weight:700;color:#1A1A2E;">${price:.2f}</div></div>'
        f'<div><div style="font-size:0.75rem;color:#888;">Rating</div><div style="font-size:1.2rem;font-weight:700;color:#1A1A2E;">⭐ {rating:.2f}/5</div></div>'
        f'<div><div style="font-size:0.75rem;color:#888;">Loves</div><div style="font-size:1.2rem;font-weight:700;color:#1A1A2E;">❤️ {loves:,}</div></div>'
        f'<div><div style="font-size:0.75rem;color:#888;">Reviews</div><div style="font-size:1.2rem;font-weight:700;color:#1A1A2E;">💬 {reviews:,}</div></div>'
        f"{size_cell}"
        "</div>"
        f'<div style="margin-bottom:10px;">{tags_html}</div>'
        '<div style="margin-top:10px;">'
        f'<span class="score-pill">Match {score}%</span>'
        f'<span class="cf-pill">👥 CF {cf_score}% {cf_label}</span>'
        f"{rec_pill}"
        "</div>"
        "</div>"
    )
    st.markdown(detail_html, unsafe_allow_html=True)

    # Variation info
    v_type = product.get("variation_type") or ""
    v_val  = product.get("variation_value") or ""
    if v_type or v_val:
        st.markdown(f"**Variation:** {v_type} — {v_val}" if v_type and v_val else f"**Variation:** {v_type or v_val}")

    # Score breakdown
    with st.expander("📊 Score breakdown", expanded=True):
        skin_m  = round(product.get("_skin_type_match", 0) * 100, 1)
        conc_m  = round(product.get("_concern_match", 0) * 100, 1)
        tag_m   = round(product.get("_tag_match", 0) * 100, 1)
        price_f = round(product.get("_price_score", 0) * 100, 1)
        rat_n   = round(product.get("_norm_rating", 0) * 100, 1)
        cb_s    = round(product.get("cb_score", 0) * 100, 1)
        st.markdown(f"""
        <div class="score-breakdown">
            <strong>Hybrid score {score}%</strong> = 65% content-based + 35% collaborative<br><br>
            <strong>Content-based ({cb_s}%)</strong><br>
            &nbsp;&nbsp;• Skin type match: {skin_m}%<br>
            &nbsp;&nbsp;• Concern match: {conc_m}%<br>
            &nbsp;&nbsp;• Rating signal: {rat_n}%<br>
            &nbsp;&nbsp;• Tag match: {tag_m}%<br>
            &nbsp;&nbsp;• Price fit: {price_f}%<br><br>
            <strong>Collaborative ({cf_score}%)</strong> —
            {f'{fb_count} user rating(s) · {rec_rate}% recommend' if fb_count else 'No ratings yet — neutral score applied'}
        </div>""", unsafe_allow_html=True)

    # Ingredients
    with st.expander("🧪 Full Ingredients List"):
        st.write(ingredients)

    # AI explanation
    exp_key = f"explanation_{pid}"
    profile = st.session_state.get("user_profile", {})
    skin_str    = profile.get("skin_type", "") or "general"
    concern_str = ", ".join(profile.get("skin_concerns", [])) or "general"
    if exp_key not in st.session_state:
        with st.spinner("Generating AI explanation…"):
            st.session_state[exp_key] = generate_explanation(
                skin_type=skin_str, concern=concern_str,
                ingredients=ingredients, rating=rating,
                product_name=p_name,
            )
    explanation = st.session_state.get(exp_key)
    if explanation:
        st.markdown(f'<div class="ai-box">🤖 <strong>Why this product?</strong><br><br>{explanation}</div>',
                    unsafe_allow_html=True)

    # Rich feedback form (FR-4)
    st.write("")
    st.markdown("### 💬 Leave a Review")
    already = st.session_state["feedback_submitted"].get(pid, False)
    if already:
        st.success("✅ Your review has been submitted — thank you!")
    else:
        with st.form(f"feedback_form_{pid}"):
            f_rating      = st.slider("Overall rating", 1, 5, 4)
            f_recommended = st.radio("Would you recommend this product?",
                                     ["Yes", "No"], horizontal=True)
            f_review      = st.text_area("Write a review (optional)",
                                         placeholder="Share what you liked or didn't like…",
                                         max_chars=500)
            submitted = st.form_submit_button("Submit Review", use_container_width='stretch', type="primary")

        if submitted:
            ok = insert_feedback(
                product_id     = pid,
                rating         = f_rating,
                is_recommended = (f_recommended == "Yes"),
                review_text    = f_review,
            )
            if ok:
                st.session_state["feedback_submitted"][pid] = True
                st.rerun()
            else:
                st.error("Failed to save review.")


# ═══════════════════════════════════════════════════════════════
# RECOMMENDATIONS PAGE  (FR-3)
# ═══════════════════════════════════════════════════════════════

def render_recommendations_page():
    st.markdown("<h2 style='font-size:1.45rem;font-weight:800;color:#1A1A2E;'>💄 Get Recommendations</h2>",
                unsafe_allow_html=True)

    # Ensure products are loaded (sidebar helper may have already done this)
    if st.session_state["_products_cache"] is None:
        with st.spinner("Loading catalogue…"):
            st.session_state["_products_cache"] = fetch_products()

    # ── Handle run trigger set by sidebar button ─────────────────
    if st.session_state.get("_trigger_run"):
        st.session_state["_trigger_run"] = False
        profile = st.session_state.get("_run_profile", {})

        with st.spinner("Running hybrid recommendation engine…"):
            products    = fetch_products()
            collab_data = fetch_collab_scores()

        if not products:
            st.error("⚠️ Could not load products. Check your Supabase credentials.")
            return

        top5 = run_recommendation_pipeline(products, profile, collab_data=collab_data)

        if not top5:
            st.warning("😕 No products matched your criteria. Try a higher budget, broader category, or fewer restrictions.")
            return

        st.session_state["recommendations"]   = top5
        st.session_state["last_profile"]       = profile
        st.session_state["feedback_submitted"] = {}
        for key in list(st.session_state.keys()):
            if key.startswith("explanation_"):
                del st.session_state[key]

        user = get_current_user()
        if user:
            save_recommendation_history(user["id"], profile, top5)

    top5    = st.session_state.get("recommendations")
    profile = st.session_state.get("last_profile")

    if not top5:
        st.markdown("""
        <div style='background:#F8F8FF;border-radius:12px;padding:1.2rem 1.4rem;
                    margin-top:1rem;border:1px solid #E0E0F0;'>
            <div style='font-weight:700;font-size:0.95rem;color:#1A1A2E;margin-bottom:0.6rem;'>
                How the hybrid engine works</div>
            <ol style='margin:0;padding-left:1.2rem;font-size:0.86rem;color:#444;line-height:2;'>
                <li><strong>Rule-Based Filter</strong> — category, budget, avoided ingredients, stock status.</li>
                <li><strong>Content-Based Score</strong> — skin type 20% · concern 20% · rating 20% · popularity 10% · price fit 10% · tags 10% · category 5% · reviews 5%.</li>
                <li><strong>Collaborative Filtering</strong> — helpfulness-weighted user reviews (35% blend).</li>
                <li><strong>AI Explanation</strong> — GPT writes a personalised rationale per product.</li>
            </ol>
        </div>""", unsafe_allow_html=True)
        return

    skin_type     = profile.get("skin_type", "")
    skin_concerns = profile.get("skin_concerns", [])
    primary_cat   = profile.get("primary_category", "all")
    secondary_cat = profile.get("secondary_category", "all")
    tags          = profile.get("tags_to_match", [])
    cat_label     = primary_cat if primary_cat != "all" else "All Categories"
    if secondary_cat != "all":
        cat_label += f" › {secondary_cat}"

    summary_parts = [f"✅ Top {len(top5)} results · {cat_label}"]
    if skin_type:
        summary_parts.append(f"{skin_type.title()} skin")
    if skin_concerns:
        summary_parts.append(", ".join(c.title() for c in skin_concerns))
    st.success(" · ".join(summary_parts))
    st.write("")

    for rank, product in enumerate(top5, start=1):
        pid      = product["product_id"]
        score    = round(product.get("score", 0) * 100, 1)
        cf_score = round(product.get("cf_score", 0) * 100, 1)
        fb_count = product.get("feedback_count", 0)
        rec_rate = round((product.get("recommend_rate") or 0) * 100)
        p_cat    = product.get("primary_category") or ""
        p_subcat = product.get("secondary_category") or ""
        prod_tags = _parse_highlights(product.get("highlights"))
        tags_html = "".join(f'<span class="tag-badge">{t}</span>' for t in prod_tags[:4])
        cat_display = p_cat + (f" › {p_subcat}" if p_subcat else "")
        price   = float(product.get("price_usd") or 0)
        rating  = product.get("rating") or "N/A"
        loves   = int(product.get("loves_count") or 0)
        size    = product.get("size") or ""

        badges = ""
        if int(product.get("sephora_exclusive") or 0):
            badges += ' <span style="background:#FFE4E6;color:#9F1239;font-size:0.68rem;font-weight:700;padding:2px 7px;border-radius:20px;">Sephora Exclusive</span>'
        if int(product.get("new") or 0):
            badges += ' <span style="background:#DCFCE7;color:#14532D;font-size:0.68rem;font-weight:700;padding:2px 7px;border-radius:20px;">New</span>'

        size_str   = f" &nbsp;·&nbsp; {size}" if size else ""
        cf_str     = f" &nbsp;·&nbsp; {rec_rate}% recommend" if fb_count else " (new)"
        p_name_str = product.get("product_name") or "Unknown Product"
        brand_str  = product.get("brand_name") or ""

        card_html = (
            '<div class="product-card">'
            "<div>"
            f'<span class="rank-badge">#{rank}</span>'
            f'<span class="cat-badge">{cat_display}</span>'
            f"{badges}"
            "</div>"
            f'<div class="product-title">{p_name_str}</div>'
            f'<div class="meta-row">{brand_str} &nbsp;·&nbsp; ${price:.2f}{size_str} &nbsp;·&nbsp; ⭐ {rating}/5 &nbsp;·&nbsp; ❤️ {loves:,}</div>'
            f'<div style="margin-bottom:8px;">{tags_html}</div>'
            "<div>"
            f'<span class="score-pill">Match {score}%</span>'
            f'<span class="cf-pill">👥 CF {cf_score}%{cf_str}</span>'
            "</div>"
            "</div>"
        )
        st.markdown(card_html, unsafe_allow_html=True)

        col_detail, col_gap = st.columns([1, 3])
        with col_detail:
            if st.button("📄 View Details", key=f"detail_{pid}"):
                st.session_state["detail_product"] = product
                set_page("product_detail")
                st.rerun()

        # Quick AI explanation
        exp_key = f"explanation_{pid}"
        if exp_key not in st.session_state:
            skin_str    = skin_type or "general"
            concern_str = ", ".join(skin_concerns) if skin_concerns else "general"
            with st.spinner("Generating AI explanation…"):
                st.session_state[exp_key] = generate_explanation(
                    skin_type=skin_str, concern=concern_str,
                    ingredients=product.get("ingredients", ""),
                    rating=rating, product_name=product.get("product_name", ""),
                )
        explanation = st.session_state.get(exp_key)
        if explanation:
            st.markdown(f'<div class="ai-box">🤖 <strong>Why this product?</strong><br><br>{explanation}</div>',
                        unsafe_allow_html=True)

        # Quick feedback (inline, detail page has full form)
        already = st.session_state["feedback_submitted"].get(pid, False)
        if already:
            st.success("✅ Feedback submitted")
        else:
            q_rating = st.slider("Quick rating", 1, 5, 4, key=f"slider_{pid}",
                                 help="Rate this recommendation — full review available on product detail page")
            if st.button("Submit Rating", key=f"btn_{pid}"):
                ok = insert_feedback(pid, q_rating)
                if ok:
                    st.session_state["feedback_submitted"][pid] = True
                    st.rerun()
        st.write("")


# ═══════════════════════════════════════════════════════════════
# HISTORY PAGE
# ═══════════════════════════════════════════════════════════════

def render_history_page():
    st.markdown("<h2 style='font-size:1.45rem;font-weight:800;color:#1A1A2E;'>📋 My History</h2>",
                unsafe_allow_html=True)
    user = get_current_user()
    if not user:
        st.error("You must be logged in to view history.")
        return

    with st.spinner("Loading your history…"):
        history = fetch_recommendation_history(user["id"])

    if not history:
        st.info("No history yet. Head to **Recommendations** to get started!")
        return

    st.caption(f"{len(history)} session(s) on record")
    st.write("")

    for i, session in enumerate(history, start=1):
        profile  = session.get("profile", {})
        products = session.get("products", [])
        ts       = session.get("created_at", "")[:19].replace("T", " ")
        skin     = profile.get("skin_type", "")
        concerns = profile.get("skin_concerns", [])
        primary_cat   = profile.get("primary_category", "all")
        secondary_cat = profile.get("secondary_category", "all")
        cat_label     = primary_cat if primary_cat != "all" else "All"
        if secondary_cat != "all":
            cat_label += f" › {secondary_cat}"
        budget = profile.get("max_budget", 0)

        parts = [f"Session {i} · {ts}", cat_label, f"${budget:.0f}"]
        if skin:
            parts.append(f"{skin.title()} skin")
        if concerns:
            parts.append(", ".join(c.title() for c in concerns[:2]))

        with st.expander("  |  ".join(parts), expanded=(i == 1)):
            cols = st.columns(4)
            cols[0].metric("Category", cat_label)
            cols[1].metric("Skin Type", skin.title() if skin else "—")
            cols[2].metric("Budget",   f"${budget:.0f}")
            cols[3].metric("Results",  str(len(products)))

            if concerns:
                st.caption("Concerns: " + ", ".join(c.title() for c in concerns))
            avoided = profile.get("ingredients_to_avoid", [])
            if avoided:
                st.caption("Avoided: " + ", ".join(avoided))
            st.write("")

            for rank, p in enumerate(products, start=1):
                p_name   = p.get("product_name", "?")
                p_brand  = p.get("brand_name", "")
                p_price  = float(p.get("price_usd") or 0)
                p_rating = p.get("rating", "?")
                p_cat    = p.get("primary_category", "")
                st.markdown(
                    f"**#{rank}** **{p_name}** &nbsp;·&nbsp; {p_brand} &nbsp;·&nbsp; "
                    f"${p_price:.2f} &nbsp;·&nbsp; ⭐ {p_rating}/5"
                    + (f" &nbsp;·&nbsp; {p_cat}" if p_cat else "")
                )


# ═══════════════════════════════════════════════════════════════
# ADMIN PANEL  (FR-2, Figure 4.9)
# ═══════════════════════════════════════════════════════════════

def render_admin_page():
    if not is_admin():
        st.error("🚫 Access denied. Admin privileges required.")
        return

    st.markdown("<h2 style='font-size:1.45rem;font-weight:800;color:#1A1A2E;'>🛠️ Administrator Panel</h2>",
                unsafe_allow_html=True)
    st.caption("Manage the product catalogue and monitor user feedback.")
    st.write("")

    tab_stats, tab_products, tab_feedback = st.tabs(
        ["📊 Overview", "🗄️ Product Database", "💬 Feedback Log"]
    )

    with tab_stats:
        products = fetch_products()
        stats    = fetch_product_stats()
        feedback = fetch_all_feedback()

        total_products  = len(products)
        total_feedback  = len(feedback)
        rated_products  = len(stats)
        avg_rating      = (sum(float(s.get("avg_user_rating") or 0) for s in stats) / rated_products
                           if rated_products else 0)

        c1, c2, c3, c4 = st.columns(4)
        for col, label, value in zip(
            [c1, c2, c3, c4],
            ["Total Products", "Total Reviews", "Rated Products", "Avg User Rating"],
            [total_products, total_feedback, rated_products, f"{avg_rating:.2f}/5"],
        ):
            with col:
                st.markdown(f"""
                <div class="admin-stat">
                    <div style="font-size:0.75rem;color:#888;">{label}</div>
                    <div style="font-size:1.6rem;font-weight:800;color:#1A1A2E;">{value}</div>
                </div>""", unsafe_allow_html=True)

        if stats:
            st.write("")
            st.markdown("**Top rated products (by user reviews)**")
            sorted_stats = sorted(stats, key=lambda x: float(x.get("avg_user_rating") or 0), reverse=True)
            for s in sorted_stats[:10]:
                pid      = s.get("product_id", "")
                avg_r    = float(s.get("avg_user_rating") or 0)
                fb_count = int(s.get("feedback_count") or 0)
                rec_rate = round(float(s.get("recommend_rate") or 0) * 100)
                # Look up product name
                match = next((p for p in products if p.get("product_id") == pid), None)
                name  = match.get("product_name", pid) if match else pid
                brand = match.get("brand_name", "") if match else ""
                st.markdown(
                    f"**{name}** &nbsp;·&nbsp; {brand} &nbsp;·&nbsp; "
                    f"⭐ {avg_r:.2f}/5 &nbsp;·&nbsp; {fb_count} reviews &nbsp;·&nbsp; "
                    f"👍 {rec_rate}% recommend"
                )

    with tab_products:
        products = fetch_products()
        st.caption(f"{len(products)} products in database")
        st.write("")

        search = st.text_input("🔍 Search products", placeholder="Product name or brand…")
        cat_filter = st.selectbox(
            "Filter by category",
            ["All"] + sorted({p.get("primary_category") or "" for p in products if p.get("primary_category")}),
        )

        filtered = products
        if search:
            s = search.lower()
            filtered = [p for p in filtered if s in (p.get("product_name") or "").lower()
                        or s in (p.get("brand_name") or "").lower()]
        if cat_filter != "All":
            filtered = [p for p in filtered if (p.get("primary_category") or "") == cat_filter]

        st.caption(f"Showing {len(filtered)} product(s)")
        for p in filtered[:100]:
            st.markdown(
                f"**{p.get('product_name','')}** &nbsp;·&nbsp; {p.get('brand_name','')} &nbsp;·&nbsp; "
                f"${float(p.get('price_usd') or 0):.2f} &nbsp;·&nbsp; "
                f"⭐ {p.get('rating','?')}/5 &nbsp;·&nbsp; "
                f"{p.get('primary_category','')} › {p.get('secondary_category','')}"
            )

    with tab_feedback:
        feedback = fetch_all_feedback()
        st.caption(f"{len(feedback)} feedback record(s)")
        st.write("")

        if not feedback:
            st.info("No feedback submitted yet.")
        else:
            for row in feedback[:200]:
                pid      = row.get("product_id", "")
                rating   = row.get("rating", "?")
                rec      = row.get("is_recommended")
                review   = row.get("review_text") or ""
                ts       = (row.get("created_at") or "")[:19].replace("T", " ")
                prod     = row.get("products") or {}
                p_name   = prod.get("product_name", pid) if isinstance(prod, dict) else pid
                rec_str  = "👍 Recommended" if rec else ("👎 Not recommended" if rec is False else "")
                st.markdown(
                    f"**{p_name}** &nbsp;·&nbsp; ⭐ {rating}/5 {rec_str} &nbsp;·&nbsp; {ts}"
                    + (f"<br><small style='color:#555;'>{review}</small>" if review else ""),
                    unsafe_allow_html=True,
                )
                st.divider()


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
    elif page == "profile":
        render_profile_page()
    elif page == "product_detail":
        render_product_detail_page()
    elif page == "admin":
        render_admin_page()
    else:
        render_recommendations_page()