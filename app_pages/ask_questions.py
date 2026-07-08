from __future__ import annotations

import streamlit as st

from core.config import load_app_config
from core.exceptions import LLMError, VectorStoreError
from core.rag.pipeline import answer_question

st.title("💬 Ask Your Knowledge Base")

config = load_app_config()
st.caption(f"Using **{config.llm_provider}** ({config.llm_model}) with **{config.embedding_provider}** embeddings.")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


def render_sources(sources: list[dict]) -> None:
    if not sources:
        return
    with st.expander("Sources"):
        for source in sources:
            label = source["title"] or source["source_url"]
            st.markdown(f"- [{label}]({source['source_url']}) — `{source['file_path']}`")


for turn in st.session_state.chat_history:
    with st.chat_message("user"):
        st.write(turn["question"])
    with st.chat_message("assistant"):
        st.write(turn["answer"])
        render_sources(turn["sources"])

question = st.chat_input("Ask a question about your added sources...")

if question:
    with st.chat_message("user"):
        st.write(question)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                result = answer_question(question, config)
                st.write(result.text)
                render_sources(result.sources)
                st.session_state.chat_history.append(
                    {"question": question, "answer": result.text, "sources": result.sources}
                )
            except (LLMError, VectorStoreError) as exc:
                st.error(str(exc))
            except Exception as exc:  # noqa: BLE001
                st.error(f"Unexpected error: {exc}")
