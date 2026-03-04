"""
auth.py - Authentication layer using Supabase Auth
MSc Thesis Prototype

Responsibilities:
  - Sign up new users (email + password)
  - Sign in existing users
  - Sign out
  - Expose the current session user
"""

import os
import streamlit as st
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


def _get_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise EnvironmentError("Missing SUPABASE_URL or SUPABASE_KEY in .env")
    return create_client(url, key)


# ─────────────────────────────────────────────
# Sign Up
# ─────────────────────────────────────────────

def sign_up(email: str, password: str) -> tuple[bool, str]:
    """
    Register a new user via Supabase Auth.

    Returns:
        (True, "") on success or (False, error_message) on failure.
    """
    try:
        client = _get_client()
        res = client.auth.sign_up({"email": email, "password": password})
        if res.user:
            return True, ""
        return False, "Sign-up failed. Please try again."
    except Exception as exc:
        return False, str(exc)


# ─────────────────────────────────────────────
# Sign In
# ─────────────────────────────────────────────

def sign_in(email: str, password: str) -> tuple[bool, str]:
    """
    Sign in an existing user via Supabase Auth.

    On success, stores the session and user in st.session_state.

    Returns:
        (True, "") on success or (False, error_message) on failure.
    """
    try:
        client = _get_client()
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        if res.session and res.user:
            st.session_state["supabase_session"] = res.session
            st.session_state["user"] = {
                "id":    res.user.id,
                "email": res.user.email,
            }
            return True, ""
        return False, "Invalid credentials."
    except Exception as exc:
        return False, str(exc)


# ─────────────────────────────────────────────
# Sign Out
# ─────────────────────────────────────────────

def sign_out() -> None:
    """Clear the session from Supabase and Streamlit state."""
    try:
        client = _get_client()
        client.auth.sign_out()
    except Exception:
        pass
    for key in ["supabase_session", "user", "recommendations", "last_profile"]:
        st.session_state.pop(key, None)


# ─────────────────────────────────────────────
# Current user helper
# ─────────────────────────────────────────────

def get_current_user() -> dict | None:
    """Return the logged-in user dict or None if not authenticated."""
    return st.session_state.get("user")
