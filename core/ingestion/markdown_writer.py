from __future__ import annotations

import re
import uuid
from pathlib import Path

from core.config import MARKDOWN_DIR


def slugify(text: str, max_length: int = 60) -> str:
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:max_length] or "source"


def save_markdown(title: str, content: str) -> Path:
    slug = slugify(title)
    unique_suffix = uuid.uuid4().hex[:8]
    file_path = MARKDOWN_DIR / f"{slug}-{unique_suffix}.md"
    file_path.write_text(content, encoding="utf-8")
    return file_path
