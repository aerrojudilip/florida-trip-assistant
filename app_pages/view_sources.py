from __future__ import annotations

import streamlit as st

from core.config import load_app_config
from core.exceptions import VectorStoreError
from core.metadata.store import MetadataStore
from core.rag.pipeline import delete_source

st.title("📄 Added Sources")

config = load_app_config()
metadata_store = MetadataStore()
sources = metadata_store.list_sources()

if not sources:
    st.info("No sources added yet. Go to 'Add Sources' to get started.")
else:
    st.caption(f"{len(sources)} source(s) indexed.")
    for record in sorted(sources, key=lambda r: r.date_added, reverse=True):
        with st.container(border=True):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"**{record.title}**")
                st.caption(f"{record.source_type.capitalize()} • added {record.date_added}")
                st.markdown(f"[{record.source_url}]({record.source_url})")
                st.caption(f"File: `{record.file_path}` • {record.char_count} characters")
            with col2:
                if st.button("Delete", key=f"delete_{record.id}"):
                    try:
                        delete_source(record.id, config.embedding_provider)
                        st.success("Deleted.")
                        st.rerun()
                    except VectorStoreError as exc:
                        st.error(str(exc))
