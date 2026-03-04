"""
database.py - Supabase database layer
MSc Thesis Prototype

Uses two clients:
  - anon client  → read-only public data (products)
  - service role client → writes that bypass RLS (feedback, history)
"""

import os
import json
import streamlit as st
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


def _get_anon_client() -> Client:
    """Anon key client — for public read operations (products)."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise EnvironmentError("Missing SUPABASE_URL or SUPABASE_KEY in .env")
    return create_client(url, key)


def _get_service_client() -> Client:
    """
    Service role key client — bypasses RLS entirely.
    Used for inserts (feedback, history) from the backend.
    NEVER expose this key in the frontend / browser.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise EnvironmentError(
            "Missing SUPABASE_SERVICE_KEY in .env — "
            "add it from Supabase → Project Settings → API → service_role key"
        )
    return create_client(url, key)


# ─────────────────────────────────────────────
# Fetch products (anon, cached)
# ─────────────────────────────────────────────

@st.cache_data(ttl=300)
def fetch_products() -> list[dict]:
    """Retrieve all products. Cached 5 minutes."""
    try:
        client = _get_anon_client()
        response = client.table("products").select("*").execute()
        return response.data or []
    except Exception as exc:
        st.error(f"Database error while fetching products: {exc}")
        return []


# ─────────────────────────────────────────────
# Insert feedback (service role — bypasses RLS)
# ─────────────────────────────────────────────

def insert_feedback(product_id: str, rating: int) -> bool:
    """Insert a user feedback record into the feedback table."""
    try:
        client = _get_service_client()
        client.table("feedback").insert({
            "product_id": product_id,
            "rating":     rating,
        }).execute()
        return True
    except Exception as exc:
        st.error(f"Database error while saving feedback: {exc}")
        return False


# ─────────────────────────────────────────────
# Recommendation history (service role — bypasses RLS)
# ─────────────────────────────────────────────

def save_recommendation_history(user_id: str, profile: dict, products: list[dict]) -> bool:
    """Persist a recommendation session to recommendation_history."""
    try:
        client = _get_service_client()
        product_snapshot = [{k: v for k, v in p.items() if k != "score"} for p in products]
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
    """Retrieve all past recommendation sessions for a user, newest first."""
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