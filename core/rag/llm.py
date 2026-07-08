from __future__ import annotations

from core.config import get_api_key
from core.exceptions import LLMError


def get_llm(provider: str, model: str, temperature: float = 0.2, max_output_tokens: int = 2048):
    api_key = get_api_key(provider)
    if not api_key:
        raise LLMError(
            f"Missing API key for LLM provider '{provider}'. Set the corresponding environment variable."
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model, api_key=api_key, temperature=temperature, max_tokens=max_output_tokens)

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model, google_api_key=api_key, temperature=temperature, max_output_tokens=max_output_tokens
        )

    raise LLMError(f"Unknown LLM provider: {provider}")
