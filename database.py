"""
database.py - Supabase database layer
MSc Thesis Prototype

Responsibilities:
  - Connect to Supabase using env credentials
  - Fetch all products for the recommendation engine
  - Insert user feedback records
"""

import os
import streamlit as st
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ─────────────────────────────────────────────
# Supabase client — initialised once per session
# ─────────────────────────────────────────────

def _get_client() -> Client:
    """Create and return a Supabase client using env credentials."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise EnvironmentError(
            "Missing SUPABASE_URL or SUPABASE_KEY environment variables. "
            "Please add them to your .env file."
        )

    return create_client(url, key)


# ─────────────────────────────────────────────
# Fetch products (cached for performance)
# ─────────────────────────────────────────────

@st.cache_data(ttl=300)  # Cache for 5 minutes to avoid repeated DB round-trips
def fetch_products() -> list[dict]:
    """
    Retrieve all products from the Supabase `products` table.

    Returns:
        List of product dicts, or empty list on failure.
    """
    try:
        client = _get_client()
        response = client.table("products").select("*").execute()
        return response.data or []
    except Exception as exc:
        st.error(f"Database error while fetching products: {exc}")
        return []


# ─────────────────────────────────────────────
# Insert feedback
# ─────────────────────────────────────────────

def insert_feedback(product_id: str, rating: int) -> bool:
    """
    Insert a user feedback record into the `feedback` table.

    Args:
        product_id: UUID of the recommended product.
        rating:     User rating (1–5).

    Returns:
        True on success, False on failure.
    """
    try:
        client = _get_client()
        client.table("feedback").insert({
            "product_id": product_id,
            "rating": rating,
        }).execute()
        return True
    except Exception as exc:
        st.error(f"Database error while saving feedback: {exc}")
        return False
