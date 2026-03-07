"""
database.py - Supabase database layer
MSc Thesis Prototype
"""

import os
import json
import streamlit as st
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


def _get_anon_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise EnvironmentError("Missing SUPABASE_URL or SUPABASE_KEY in .env")
    return create_client(url, key)


def _get_service_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise EnvironmentError("Missing SUPABASE_SERVICE_KEY in .env")
    return create_client(url, key)


# ── Products ─────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def fetch_products() -> list[dict]:
    try:
        client = _get_anon_client()
        response = client.table("products").select("*").execute()
        return response.data or []
    except Exception as exc:
        st.error(f"Database error while fetching products: {exc}")
        return []


# ── Feedback ─────────────────────────────────────────────────────

def insert_feedback(
    product_id: str,
    rating: int,
    is_recommended: bool | None = None,
    review_text: str = "",
    helpfulness: float = 0.0,
) -> bool:
    """Insert a rich feedback record from the user."""
    try:
        client = _get_service_client()
        record: dict = {"product_id": product_id, "rating": rating, "helpfulness": helpfulness}
        if is_recommended is not None:
            record["is_recommended"] = is_recommended
        if review_text.strip():
            record["review_text"] = review_text.strip()
        client.table("feedback").insert(record).execute()
        return True
    except Exception as exc:
        st.error(f"Database error while saving feedback: {exc}")
        return False


# ── User profiles ─────────────────────────────────────────────────

def save_user_profile(user_id: str, display_name: str, skin_type: str, skin_concerns: list[str]) -> bool:
    try:
        client = _get_service_client()
        client.table("user_profiles").upsert({
            "user_id":       user_id,
            "display_name":  display_name,
            "skin_type":     skin_type,
            "skin_concerns": json.dumps(skin_concerns),
            "updated_at":    "now()",
        }).execute()
        return True
    except Exception as exc:
        st.error(f"Error saving profile: {exc}")
        return False


def fetch_user_profile(user_id: str) -> dict:
    try:
        client = _get_service_client()
        res = client.table("user_profiles").select("*").eq("user_id", user_id).execute()
        rows = res.data or []
        if rows:
            p = rows[0]
            concerns_raw = p.get("skin_concerns", "[]")
            try:
                concerns = json.loads(concerns_raw) if isinstance(concerns_raw, str) else concerns_raw
            except Exception:
                concerns = []
            return {
                "display_name":  p.get("display_name", ""),
                "skin_type":     p.get("skin_type", ""),
                "skin_concerns": concerns,
            }
    except Exception as exc:
        st.error(f"Error fetching profile: {exc}")
    return {"display_name": "", "skin_type": "", "skin_concerns": []}


# ── Recommendation history ────────────────────────────────────────

def save_recommendation_history(user_id: str, profile: dict, products: list[dict]) -> bool:
    try:
        client = _get_service_client()
        snapshot_keys = {
            "product_id", "product_name", "brand_name", "price_usd",
            "rating", "loves_count", "reviews",
            "primary_category", "secondary_category", "tertiary_category",
            "highlights", "size",
        }
        product_snapshot = [{k: v for k, v in p.items() if k in snapshot_keys} for p in products]
        client.table("recommendation_history").insert({
            "user_id":  user_id,
            "profile":  json.dumps(profile),
            "products": json.dumps(product_snapshot),
        }).execute()
        return True
    except Exception as exc:
        st.error(f"Database error while saving history: {exc}")
        return False


def fetch_recommendation_history(user_id: str) -> list[dict]:
    try:
        client = _get_service_client()
        response = (
            client.table("recommendation_history")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        rows = response.data or []
        for row in rows:
            if isinstance(row.get("profile"), str):
                row["profile"] = json.loads(row["profile"])
            if isinstance(row.get("products"), str):
                row["products"] = json.loads(row["products"])
        return rows
    except Exception as exc:
        st.error(f"Database error while fetching history: {exc}")
        return []


# ── Collaborative filtering ───────────────────────────────────────

def fetch_collab_scores() -> list[dict]:
    try:
        client = _get_service_client()
        response = client.table("product_collab_scores").select("*").execute()
        return response.data or []
    except Exception as exc:
        print(f"[database] Could not fetch collab scores: {exc}")
        return []


# ── Admin helpers ─────────────────────────────────────────────────

def fetch_all_feedback() -> list[dict]:
    """For the admin panel — all feedback rows with product name joined."""
    try:
        client = _get_service_client()
        res = client.table("feedback").select("*, products(product_name, brand_name)").execute()
        return res.data or []
    except Exception as exc:
        st.error(f"Error fetching feedback: {exc}")
        return []


def fetch_product_stats() -> list[dict]:
    """Return products with their collab scores for the admin panel."""
    try:
        client = _get_service_client()
        res = client.table("product_collab_scores").select("*").execute()
        return res.data or []
    except Exception as exc:
        st.error(f"Error fetching product stats: {exc}")
        return []
