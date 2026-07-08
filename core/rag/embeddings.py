from __future__ import annotations

from core.config import EMBEDDING_MODELS, get_api_key
from core.exceptions import VectorStoreError


def get_embedding_function(provider: str):
    api_key = get_api_key(provider)
    if not api_key:
        raise VectorStoreError(
            f"Missing API key for embedding provider '{provider}'. Set the corresponding environment variable."
        )

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=EMBEDDING_MODELS["openai"], api_key=api_key)

    if provider == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODELS["gemini"], google_api_key=api_key)

    raise VectorStoreError(f"Unknown embedding provider: {provider}")
