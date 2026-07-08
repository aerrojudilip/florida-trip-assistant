from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.config import AppConfig
from core.exceptions import IngestionError, LLMError, VectorStoreError
from core.ingestion.manual_ingest import ingest_manual_content
from core.ingestion.markdown_writer import save_markdown
from core.ingestion.web_ingest import ingest_website
from core.ingestion.youtube_ingest import ingest_youtube
from core.metadata.store import MetadataStore, SourceRecord
from core.rag.chunking import split_markdown
from core.rag.embeddings import get_embedding_function
from core.rag.llm import get_llm
from core.rag.vector_store import add_documents, delete_by_source_id, get_vector_store, similarity_search

store = MetadataStore()

ANSWER_PROMPT = """You are a knowledgeable assistant that answers questions using ONLY the context provided below.
If the context does not contain enough information to answer, say so clearly instead of guessing.

Context:
{context}

Question: {question}

Write a thorough, well-organized answer that makes full use of the relevant information in
the context — don't compress it into one or two sentences if more detail is available.
Use multiple paragraphs, bullet points, or numbered steps where that makes the answer easier
to follow. Include specifics (names, numbers, steps, caveats) from the context rather than
vague generalities. End with a "Sources:" line listing which source title(s) you drew from.
"""


def ingest_source(
    url: str,
    source_type: str,
    embedding_provider: str,
    *,
    title: str | None = None,
    manual_content: str | None = None,
) -> SourceRecord:
    url = url.strip()
    if store.get_by_url(url):
        raise IngestionError(f"'{url}' has already been added. Delete it first to re-ingest.")

    if source_type == "youtube":
        result = ingest_youtube(url)
    elif source_type == "website":
        result = ingest_website(url)
    elif source_type == "manual":
        result = ingest_manual_content(url, title or "", manual_content or "")
    else:
        raise IngestionError(f"Unknown source type: {source_type}")

    file_path = save_markdown(result["title"], result["content"])

    record = store.add(
        title=result["title"],
        source_url=result["source_url"],
        source_type=result["source_type"],
        file_path=str(file_path),
        char_count=len(result["content"]),
    )

    try:
        embedding_function = get_embedding_function(embedding_provider)
        vector_store = get_vector_store(embedding_function)
        documents = split_markdown(result["content"], record)
        add_documents(vector_store, documents)
    except VectorStoreError:
        store.delete(record.id)
        file_path.unlink(missing_ok=True)
        raise

    return record


def delete_source(source_id: str, embedding_provider: str) -> None:
    record = store.delete(source_id)
    if record is None:
        return
    try:
        embedding_function = get_embedding_function(embedding_provider)
        vector_store = get_vector_store(embedding_function)
        delete_by_source_id(vector_store, source_id)
    finally:
        md_path = Path(record.file_path)
        if md_path.exists():
            md_path.unlink()


@dataclass
class Answer:
    text: str
    sources: list[dict]


def answer_question(question: str, config: AppConfig) -> Answer:
    question = question.strip()
    if not question:
        raise LLMError("Question cannot be empty.")

    embedding_function = get_embedding_function(config.embedding_provider)
    vector_store = get_vector_store(embedding_function)
    docs = similarity_search(vector_store, question, k=config.retrieval_k)

    if not docs:
        return Answer(
            text="No relevant content was found in the knowledge base yet. Add some sources first.",
            sources=[],
        )

    context = "\n\n---\n\n".join(f"[{doc.metadata.get('title')}]\n{doc.page_content}" for doc in docs)
    prompt = ANSWER_PROMPT.format(context=context, question=question)

    llm = get_llm(config.llm_provider, config.llm_model)
    try:
        response = llm.invoke(prompt)
    except Exception as exc:  # noqa: BLE001
        raise LLMError(f"LLM request failed: {exc}") from exc

    seen = set()
    sources = []
    for doc in docs:
        key = doc.metadata.get("source_id")
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            {
                "title": doc.metadata.get("title"),
                "source_url": doc.metadata.get("source_url"),
                "file_path": doc.metadata.get("file_path"),
            }
        )

    return Answer(text=response.content, sources=sources)
