"""Build the runner for a provider."""

from enum import StrEnum

from chilango_bench.config import get_settings
from chilango_bench.runners.base import BaseRunner
from chilango_bench.runners.mock import MockRunner
from chilango_bench.runners.openai import OpenAIRunner


class Provider(StrEnum):
    MOCK = "mock"
    """Offline runner that always answers "B"; for smoke tests."""
    OPENAI = "openai"
    """Any OpenAI-compatible chat completions endpoint (OpenAI, Groq, vLLM, LM Studio...)."""
    OLLAMA = "ollama"
    """Local Ollama through its OpenAI-compatible API; no key needed."""


def create_runner(model: str, provider: Provider, base_url: str | None = None) -> BaseRunner:
    if provider is Provider.MOCK:
        return MockRunner(model_name=model)
    if provider is Provider.OLLAMA:
        return OpenAIRunner(
            model, api_key="ollama", base_url=base_url or get_settings().ollama_base_url
        )
    return OpenAIRunner(model, base_url=base_url)
