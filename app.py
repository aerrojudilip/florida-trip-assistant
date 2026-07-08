from __future__ import annotations

import streamlit as st

from core.auth import is_authenticated

st.set_page_config(page_title="RAG Knowledge Assistant", page_icon="📚", layout="wide")

if is_authenticated():
    pages = [
        st.Page("app_pages/home.py", title="Home", icon="📚", default=True),
        st.Page("app_pages/add_sources.py", title="Add Sources", icon="➕"),
        st.Page("app_pages/ask_questions.py", title="Ask Questions", icon="💬"),
        st.Page("app_pages/view_sources.py", title="View Sources", icon="📄"),
    ]
else:
    pages = [
        st.Page("app_pages/ask_questions.py", title="Ask Questions", icon="💬", default=True),
        st.Page("app_pages/admin_login.py", title="Admin Login", icon="🔒"),
    ]

navigation = st.navigation(pages)
navigation.run()
