from __future__ import annotations

import streamlit as st

from core.config import (
    EMBEDDING_PROVIDERS,
    LLM_MODELS,
    LLM_PROVIDERS,
    get_api_key,
    load_app_config,
    save_app_config,
)

st.set_page_config(page_title="RAG Knowledge Assistant", page_icon="📚", layout="wide")


def render_sidebar_config() -> None:
    config = load_app_config()

    st.sidebar.header("⚙️ LLM Configuration")

    llm_provider = st.sidebar.selectbox(
        "LLM Provider", LLM_PROVIDERS, index=LLM_PROVIDERS.index(config.llm_provider)
    )
    model_options = LLM_MODELS[llm_provider]
    model_index = model_options.index(config.llm_model) if config.llm_model in model_options else 0
    llm_model = st.sidebar.selectbox("LLM Model", model_options, index=model_index)

    embedding_provider = st.sidebar.selectbox(
        "Embedding Provider",
        EMBEDDING_PROVIDERS,
        index=EMBEDDING_PROVIDERS.index(config.embedding_provider),
        help="Changing this after you've added sources means new questions will search "
        "with a different embedding space than existing chunks were stored with.",
    )

    if st.sidebar.button("Save configuration", use_container_width=True):
        config.llm_provider = llm_provider
        config.llm_model = llm_model
        config.embedding_provider = embedding_provider
        save_app_config(config)
        st.sidebar.success("Configuration saved.")

    st.sidebar.divider()
    st.sidebar.subheader("API Key Status")
    for provider in LLM_PROVIDERS:
        icon = "✅" if get_api_key(provider) else "❌"
        st.sidebar.write(f"{icon} {provider.capitalize()}")


render_sidebar_config()

st.title("📚 RAG Knowledge Assistant")
st.markdown(
    """
Welcome! This app builds a personal knowledge base from **YouTube videos** and
**website articles**, then answers your questions grounded in that content.

**Get started:**
1. Open **Add Sources** to submit YouTube links or website URLs.
2. Open **View Sources** to see everything that has been indexed.
3. Open **Ask Questions** to chat with your knowledge base.

Configure your preferred LLM and embedding provider in the sidebar. Make sure the
relevant API key is set as an environment variable — see the status panel above.
"""
)
