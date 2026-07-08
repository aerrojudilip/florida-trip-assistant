from __future__ import annotations

from datetime import datetime, timezone

from core.exceptions import EmptyContentError, InvalidLinkError
from core.ingestion.web_ingest import validate_url


def ingest_manual_content(source_url: str, title: str, content: str) -> dict:
    """Build a knowledge source from content the user already copied themselves.

    Fallback for sites whose bot/WAF protection blocks automated scraping — the
    user has legitimate access via their own browser and can paste what they see.
    """
    source_url = source_url.strip()
    content = content.strip()
    title = title.strip() or source_url

    if not source_url:
        raise InvalidLinkError("Please provide the source URL this content came from.")
    validate_url(source_url)

    if not content or len(content) < 20:
        raise EmptyContentError("Pasted content is empty or too short to index.")

    markdown = (
        f"# {title}\n\n"
        f"Source: {source_url}\n\n"
        f"Retrieved: {datetime.now(timezone.utc).isoformat()} (manually pasted)\n\n"
        f"## Content\n\n{content}\n"
    )

    return {
        "title": title,
        "source_url": source_url,
        "source_type": "manual",
        "content": markdown,
    }
