from __future__ import annotations

import hmac

import streamlit as st

from core.config import get_app_password

SESSION_KEY = "is_admin_authenticated"


def is_authenticated() -> bool:
    return bool(st.session_state.get(SESSION_KEY))


def log_out() -> None:
    st.session_state[SESSION_KEY] = False


def render_login() -> None:
    st.title("🔒 Admin Login")
    st.caption("Home, Add Sources, and View Sources require the admin password. Ask Questions stays public.")

    configured_password = get_app_password()
    if not configured_password:
        st.error(
            "No admin password is configured. Set APP_PASSWORD in setEnv.env "
            "(or your hosting platform's secrets) to enable admin access."
        )
        return

    with st.form("admin_login_form"):
        entered = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Unlock")

    if submitted:
        if hmac.compare_digest(entered, configured_password):
            st.session_state[SESSION_KEY] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
