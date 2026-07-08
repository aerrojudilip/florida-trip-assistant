from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from core.metadata.store import SourceRecord

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


def split_markdown(content: str, source: SourceRecord) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_text(content)
    return [
        Document(
            page_content=chunk,
            metadata={
                "source_id": source.id,
                "title": source.title,
                "source_url": source.source_url,
                "source_type": source.source_type,
                "file_path": source.file_path,
            },
        )
        for chunk in chunks
    ]
