"""Factory for instantiating model runners."""

from chilango_bench.core.exceptions import RunnerError
from chilango_bench.runners.base import BaseRunner
from chilango_bench.runners.mock import MockRunner
from chilango_bench.runners.openai import OpenAIRunner


def create_runner(
    model: str,
    provider: str = "auto",
    **kwargs: object,
) -> BaseRunner:
    """Create a configured model runner instance.

    Args:
        model: Name of the model (e.g. 'mock-model', 'gpt-4o-mini', 'llama3').
        provider: Provider identifier ('mock', 'openai', or 'auto').
        **kwargs: Provider-specific arguments.

    Returns:
        Configured BaseRunner implementation.

    Raises:
        RunnerError: If provider is unrecognized.
    """
    provider_normalized = provider.strip().lower()
    is_mock = provider_normalized == "mock" or (
        provider_normalized == "auto" and model.startswith("mock")
    )

    if is_mock:
        mock_resp = str(kwargs.get("default_response", "B"))
        return MockRunner(model_name=model, default_response=mock_resp)

    if provider_normalized in ("openai", "auto"):
        api_key_val = kwargs.get("api_key")
        api_key = str(api_key_val) if api_key_val is not None else None

        base_url_val = kwargs.get("base_url")
        base_url = str(base_url_val) if base_url_val is not None else None

        return OpenAIRunner(model_name=model, api_key=api_key, base_url=base_url)

    raise RunnerError(f"Unsupported model provider: '{provider}'")
