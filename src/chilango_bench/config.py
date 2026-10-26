"""Runtime configuration loaded from environment variables."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Benchmark environment settings."""

    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    ollama_base_url: str = "http://localhost:11434/v1"
    timeout_seconds: float = 30.0
    max_retries: int = 3


def get_settings() -> Settings:
    """Read configuration from environment variables with safe defaults."""
    api_key = os.getenv("OPENAI_API_KEY")
    # Treat empty string as None
    if api_key is not None and not api_key.strip():
        api_key = None

    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
    if not base_url:
        base_url = "https://api.openai.com/v1"

    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "").strip() or "http://localhost:11434/v1"

    try:
        timeout = float(os.getenv("CHILANGO_TIMEOUT_SECONDS", "30.0"))
    except ValueError:
        timeout = 30.0

    try:
        retries = int(os.getenv("CHILANGO_MAX_RETRIES", "3"))
    except ValueError:
        retries = 3

    return Settings(
        openai_api_key=api_key,
        openai_base_url=base_url,
        ollama_base_url=ollama_base_url,
        timeout_seconds=timeout,
        max_retries=retries,
    )
