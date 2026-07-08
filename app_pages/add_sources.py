from __future__ import annotations

import streamlit as st

from core.config import load_app_config
from core.exceptions import IngestionError, VectorStoreError
from core.rag.pipeline import ingest_source

st.title("➕ Add a Knowledge Source")

config = load_app_config()

tab_youtube, tab_website, tab_manual = st.tabs(["YouTube Video", "Website URL", "Paste Content"])

with tab_youtube:
    with st.form("youtube_form", clear_on_submit=True):
        youtube_url = st.text_input("YouTube video URL", placeholder="https://www.youtube.com/watch?v=...")
        submitted = st.form_submit_button("Add YouTube video")
    if submitted:
        if not youtube_url:
            st.error("Please enter a YouTube URL.")
        else:
            with st.spinner("Fetching transcript and indexing..."):
                try:
                    record = ingest_source(youtube_url, "youtube", config.embedding_provider)
                    st.success(f"Added '{record.title}' ({record.char_count} characters indexed).")
                except (IngestionError, VectorStoreError) as exc:
                    st.error(str(exc))
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Unexpected error: {exc}")

with tab_website:
    st.caption(
        "Some sites block automated scraping (bot/WAF protection). If adding a website "
        "fails with a 403/forbidden error, use the **Paste Content** tab instead."
    )
    with st.form("website_form", clear_on_submit=True):
        website_url = st.text_input("Website URL", placeholder="https://example.com/article")
        submitted_web = st.form_submit_button("Add website")
    if submitted_web:
        if not website_url:
            st.error("Please enter a website URL.")
        else:
            with st.spinner("Scraping and indexing..."):
                try:
                    record = ingest_source(website_url, "website", config.embedding_provider)
                    st.success(f"Added '{record.title}' ({record.char_count} characters indexed).")
                except (IngestionError, VectorStoreError) as exc:
                    st.error(str(exc))
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Unexpected error: {exc}")

with tab_manual:
    st.caption(
        "For pages that block automated scraping: open the page in your own browser, "
        "copy the article text, and paste it below. It's indexed exactly like a scraped site."
    )
    with st.form("manual_form", clear_on_submit=True):
        manual_url = st.text_input("Source URL (for attribution)", placeholder="https://example.com/article")
        manual_title = st.text_input("Title (optional)", placeholder="Article title")
        manual_text = st.text_area("Pasted content", height=250, placeholder="Paste the article text here...")
        submitted_manual = st.form_submit_button("Add pasted content")
    if submitted_manual:
        if not manual_url or not manual_text:
            st.error("Please provide both the source URL and the pasted content.")
        else:
            with st.spinner("Indexing..."):
                try:
                    record = ingest_source(
                        manual_url,
                        "manual",
                        config.embedding_provider,
                        title=manual_title,
                        manual_content=manual_text,
                    )
                    st.success(f"Added '{record.title}' ({record.char_count} characters indexed).")
                except (IngestionError, VectorStoreError) as exc:
                    st.error(str(exc))
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Unexpected error: {exc}")
