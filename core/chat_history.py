from __future__ import annotations

import json
import re
from pathlib import Path

from core.config import CHAT_HISTORY_DIR

_SESSION_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")


def _history_path(session_id: str) -> Path | None:
    if not _SESSION_ID_PATTERN.match(session_id):
        return None
    return CHAT_HISTORY_DIR / f"{session_id}.json"


def load_history(session_id: str) -> list[dict]:
    path = _history_path(session_id)
    if not path or not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def save_history(session_id: str, history: list[dict]) -> None:
    path = _history_path(session_id)
    if not path:
        return
    path.write_text(json.dumps(history, indent=2), encoding="utf-8")
