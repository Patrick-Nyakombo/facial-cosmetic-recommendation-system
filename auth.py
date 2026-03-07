"""
auth.py - Authentication layer using Supabase Auth
MSc Thesis Prototype

Responsibilities:
  - Sign up new users (email + password + skin profile)
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


def _get_service_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise EnvironmentError("Missing SUPABASE_SERVICE_KEY in .env")
    return create_client(url, key)


def sign_up(
    email: str,
    password: str,
    display_name: str = "",
    skin_type: str = "",
    skin_concerns: list[str] | None = None,
) -> tuple[bool, str]:
    """
    Register a new user and create their skin profile.
    Returns (True, "") on success or (False, error_message).
    """
    import json
    try:
        client = _get_client()
        res = client.auth.sign_up({"email": email, "password": password})
        if not res.user:
            return False, "Sign-up failed. Please try again."

        # Save skin profile via service role
        svc = _get_service_client()
        svc.table("user_profiles").upsert({
            "user_id":       res.user.id,
            "display_name":  display_name,
            "skin_type":     skin_type,
            "skin_concerns": json.dumps(skin_concerns or []),
        }).execute()

        return True, ""
    except Exception as exc:
        return False, str(exc)


def sign_in(email: str, password: str) -> tuple[bool, str]:
    """
    Sign in an existing user. Loads their skin profile into session state.
    Returns (True, "") on success or (False, error_message).
    """
    import json
    try:
        client = _get_client()
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        if not (res.session and res.user):
            return False, "Invalid credentials."

        st.session_state["supabase_session"] = res.session
        st.session_state["user"] = {
            "id":    res.user.id,
            "email": res.user.email,
        }

        # Load skin profile
        svc = _get_service_client()
        profile_res = (
            svc.table("user_profiles")
            .select("*")
            .eq("user_id", res.user.id)
            .execute()
        )
        rows = profile_res.data or []
        if rows:
            p = rows[0]
            concerns_raw = p.get("skin_concerns", "[]")
            try:
                concerns = json.loads(concerns_raw) if isinstance(concerns_raw, str) else concerns_raw
            except Exception:
                concerns = []
            st.session_state["user_profile"] = {
                "display_name":  p.get("display_name", ""),
                "skin_type":     p.get("skin_type", ""),
                "skin_concerns": concerns,
            }
        else:
            st.session_state["user_profile"] = {
                "display_name": "", "skin_type": "", "skin_concerns": []
            }

        # Check admin status
        admin_res = (
            svc.table("admin_users")
            .select("email")
            .eq("email", res.user.email)
            .execute()
        )
        st.session_state["is_admin"] = bool(admin_res.data)

        return True, ""
    except Exception as exc:
        return False, str(exc)


def sign_out() -> None:
    """Clear the session from Supabase and Streamlit state."""
    try:
        _get_client().auth.sign_out()
    except Exception:
        pass
    for key in [
        "supabase_session", "user", "user_profile", "is_admin",
        "recommendations", "last_profile", "_products_cache",
    ]:
        st.session_state.pop(key, None)


def get_current_user() -> dict | None:
    """Return the logged-in user dict or None if not authenticated."""
    return st.session_state.get("user")


def is_admin() -> bool:
    """Return True if the current user has admin privileges."""
    return st.session_state.get("is_admin", False)
