from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from core.config import METADATA_FILE

_lock = threading.Lock()


@dataclass
class SourceRecord:
    id: str
    title: str
    source_url: str
    source_type: str
    file_path: str
    date_added: str
    char_count: int
    status: str = "indexed"
    error: Optional[str] = None


class MetadataStore:
    def __init__(self, path: Path = METADATA_FILE):
        self.path = path
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def _read(self) -> list[dict]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8") or "[]")
        except json.JSONDecodeError:
            return []

    def _write(self, records: list[dict]) -> None:
        self.path.write_text(json.dumps(records, indent=2), encoding="utf-8")

    def list_sources(self) -> list[SourceRecord]:
        with _lock:
            return [SourceRecord(**r) for r in self._read()]

    def get_by_url(self, source_url: str) -> Optional[SourceRecord]:
        for record in self.list_sources():
            if record.source_url == source_url:
                return record
        return None

    def get(self, source_id: str) -> Optional[SourceRecord]:
        for record in self.list_sources():
            if record.id == source_id:
                return record
        return None

    def add(
        self,
        title: str,
        source_url: str,
        source_type: str,
        file_path: str,
        char_count: int,
        status: str = "indexed",
        error: Optional[str] = None,
    ) -> SourceRecord:
        record = SourceRecord(
            id=uuid.uuid4().hex,
            title=title,
            source_url=source_url,
            source_type=source_type,
            file_path=file_path,
            date_added=datetime.now(timezone.utc).isoformat(),
            char_count=char_count,
            status=status,
            error=error,
        )
        with _lock:
            records = self._read()
            records.append(asdict(record))
            self._write(records)
        return record

    def delete(self, source_id: str) -> Optional[SourceRecord]:
        with _lock:
            records = self._read()
            remaining = [r for r in records if r["id"] != source_id]
            deleted = next((r for r in records if r["id"] == source_id), None)
            self._write(remaining)
        return SourceRecord(**deleted) if deleted else None
