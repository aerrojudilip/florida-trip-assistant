from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MARKDOWN_DIR = DATA_DIR / "markdown"
CHROMA_DIR = DATA_DIR / "chroma_db"
METADATA_FILE = DATA_DIR / "metadata.json"
APP_CONFIG_FILE = DATA_DIR / "app_config.json"

for _path in (DATA_DIR, MARKDOWN_DIR, CHROMA_DIR):
    _path.mkdir(parents=True, exist_ok=True)

LLM_PROVIDERS = ["openai", "gemini"]
EMBEDDING_PROVIDERS = ["openai", "gemini"]

LLM_MODELS = {
    "openai": ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"],
    "gemini": ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
}

EMBEDDING_MODELS = {
    "openai": "text-embedding-3-small",
    "gemini": "models/embedding-001",
}

_ENV_VAR_BY_PROVIDER = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GOOGLE_API_KEY",
}


@dataclass
class AppConfig:
    llm_provider: str = os.getenv("DEFAULT_LLM_PROVIDER", "openai")
    llm_model: str = LLM_MODELS.get(os.getenv("DEFAULT_LLM_PROVIDER", "openai"), ["gpt-4o-mini"])[0]
    embedding_provider: str = os.getenv("DEFAULT_EMBEDDING_PROVIDER", "openai")
    retrieval_k: int = 4


def load_app_config() -> AppConfig:
    if APP_CONFIG_FILE.exists():
        try:
            data = json.loads(APP_CONFIG_FILE.read_text(encoding="utf-8"))
            return AppConfig(**data)
        except (json.JSONDecodeError, TypeError):
            pass
    return AppConfig()


def save_app_config(config: AppConfig) -> None:
    APP_CONFIG_FILE.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")


def get_youtube_proxy_config():
    """Optional HTTP(S) proxy for youtube-transcript-api.

    YouTube sometimes rate-limits or blocks a host's IP for transcript requests
    (the library raises IpBlocked/RequestBlocked when this happens). Set YT_PROXY_URL
    (or separate YT_PROXY_HTTP/YT_PROXY_HTTPS) to route around that, e.g. using a
    residential proxy provider such as Webshare. Returns None if unconfigured.
    """
    single = os.getenv("YT_PROXY_URL")
    http_proxy = os.getenv("YT_PROXY_HTTP", single)
    https_proxy = os.getenv("YT_PROXY_HTTPS", single)
    if not http_proxy and not https_proxy:
        return None

    from youtube_transcript_api.proxies import GenericProxyConfig

    return GenericProxyConfig(http_url=http_proxy, https_url=https_proxy)


def get_youtube_proxy_url() -> str | None:
    """Single proxy URL form (used by yt-dlp, which takes one URL for both schemes)."""
    return os.getenv("YT_PROXY_URL") or os.getenv("YT_PROXY_HTTPS") or os.getenv("YT_PROXY_HTTP")


def get_api_key(provider: str) -> str | None:
    """Look up an API key from env vars first, then Streamlit secrets (for cloud deployment)."""
    env_var = _ENV_VAR_BY_PROVIDER.get(provider)
    if not env_var:
        return None

    value = os.getenv(env_var)
    if value:
        return value

    try:
        import streamlit as st

        return st.secrets.get(env_var)
    except Exception:
        return None
