"""Offline unit tests for model runners and factory."""

import httpx
import pytest
import respx

from chilango_bench.core.exceptions import ConfigurationError, RunnerError
from chilango_bench.runners.factory import create_runner
from chilango_bench.runners.mock import MockRunner
from chilango_bench.runners.openai import OpenAIRunner


def test_mock_runner_default_behavior() -> None:
    """Ensure MockRunner returns deterministic canned output and increments call count."""
    runner = MockRunner(model_name="mock-v1", default_response="B")
    resp = runner.generate(prompt="¿Cuál es la respuesta?")

    assert resp.text == "B"
    assert resp.model_name == "mock-v1"
    assert resp.prompt_tokens == 15
    assert resp.completion_tokens == 5
    assert resp.latency_seconds > 0
    assert runner.call_count == 1


def test_mock_runner_canned_substring_matching() -> None:
    """Ensure MockRunner returns specific responses when prompt substrings match."""
    canned = {"tamal": "Guajolota", "metro": "La Raza"}
    runner = MockRunner(canned_responses=canned, default_response="Default")

    resp1 = runner.generate(prompt="Dime el nombre de la torta de tamal")
    assert resp1.text == "Guajolota"

    resp2 = runner.generate(prompt="¿Cuál es la estación de metro más larga?")
    assert resp2.text == "La Raza"

    resp3 = runner.generate(prompt="Una pregunta no registrada")
    assert resp3.text == "Default"


def test_mock_runner_injected_exception() -> None:
    """Ensure MockRunner raises configured exceptions."""
    runner = MockRunner(should_raise=RunnerError("Simulated failure"))
    with pytest.raises(RunnerError, match="Simulated failure"):
        runner.generate(prompt="Cualquier prompt")


@respx.mock
def test_openai_runner_success() -> None:
    """Ensure OpenAIRunner parses chat completion payloads correctly."""
    endpoint = "https://api.openai.com/v1/chat/completions"
    fake_payload = {
        "id": "chatcmpl-123",
        "model": "gpt-4o-mini",
        "choices": [{"message": {"role": "assistant", "content": "B"}}],
        "usage": {"prompt_tokens": 20, "completion_tokens": 5},
    }
    respx.post(endpoint).respond(status_code=200, json=fake_payload)

    runner = OpenAIRunner(model_name="gpt-4o-mini", api_key="sk-test-key")
    resp = runner.generate(
        prompt="¿Cuál es la opción correcta?", system_prompt="Responde solo la letra"
    )

    assert resp.text == "B"
    assert resp.prompt_tokens == 20
    assert resp.completion_tokens == 5
    assert resp.model_name == "gpt-4o-mini"
    assert resp.raw_response["id"] == "chatcmpl-123"


@respx.mock
def test_openai_runner_retry_on_rate_limit() -> None:
    """Ensure OpenAIRunner retries on HTTP 429 and succeeds on subsequent attempt."""
    endpoint = "https://api.openai.com/v1/chat/completions"
    route = respx.post(endpoint)
    # First attempt fails with 429, second attempt succeeds
    route.side_effect = [
        httpx.Response(429, text="Rate limit exceeded"),
        httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Respuesta tras reintento"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        ),
    ]

    runner = OpenAIRunner(model_name="gpt-4o-mini", api_key="sk-test", max_retries=2)
    resp = runner.generate(prompt="Prueba")
    assert resp.text == "Respuesta tras reintento"


@respx.mock
def test_openai_runner_max_retries_exceeded() -> None:
    """Ensure OpenAIRunner raises RunnerError when rate limit retries are exhausted."""
    endpoint = "https://api.openai.com/v1/chat/completions"
    respx.post(endpoint).respond(status_code=429, text="Rate limit exceeded")

    runner = OpenAIRunner(model_name="gpt-4o-mini", api_key="sk-test", max_retries=1)
    with pytest.raises(RunnerError, match="failed with HTTP 429"):
        runner.generate(prompt="Prueba")


@respx.mock
def test_openai_runner_timeout() -> None:
    """Ensure OpenAIRunner converts httpx TimeoutException to RunnerError."""
    endpoint = "https://api.openai.com/v1/chat/completions"
    respx.post(endpoint).mock(side_effect=httpx.TimeoutException("Connection timed out"))

    runner = OpenAIRunner(
        model_name="gpt-4o-mini", api_key="sk-test", timeout_seconds=1.0, max_retries=0
    )
    with pytest.raises(RunnerError, match="timed out"):
        runner.generate(prompt="Prueba timeout")


@respx.mock
def test_openai_runner_malformed_response() -> None:
    """Ensure OpenAIRunner handles JSON missing choices field."""
    endpoint = "https://api.openai.com/v1/chat/completions"
    respx.post(endpoint).respond(status_code=200, json={"id": "bad-payload"})

    runner = OpenAIRunner(model_name="gpt-4o-mini", api_key="sk-test")
    with pytest.raises(RunnerError, match="Unexpected response format"):
        runner.generate(prompt="Prueba")


def test_openai_runner_missing_api_key_for_official_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure ConfigurationError is raised when official OpenAI URL is used without key."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ConfigurationError, match="OPENAI_API_KEY environment variable is required"):
        OpenAIRunner(model_name="gpt-4o-mini", api_key=None, base_url="https://api.openai.com/v1")


def test_openai_runner_local_endpoint_without_key() -> None:
    """Ensure local OpenAI-compatible endpoints (like Ollama) work without API key."""
    runner = OpenAIRunner(model_name="llama3", api_key=None, base_url="http://localhost:11434/v1")
    assert runner.base_url == "http://localhost:11434/v1"
    assert runner.api_key == "dummy-key-for-local-endpoint"


def test_create_runner_factory() -> None:
    """Ensure create_runner instantiates expected runner classes."""
    mock_runner = create_runner(model="mock-fast", provider="mock")
    assert isinstance(mock_runner, MockRunner)

    auto_mock = create_runner(model="mock-model", provider="auto")
    assert isinstance(auto_mock, MockRunner)

    openai_runner = create_runner(
        model="gpt-4o-mini", provider="openai", api_key="test-key", base_url="https://mock.api"
    )
    assert isinstance(openai_runner, OpenAIRunner)

    with pytest.raises(RunnerError, match="Unsupported model provider"):
        create_runner(model="test", provider="unknown_provider")


@respx.mock
def test_openai_runner_http_status_error() -> None:
    """Ensure OpenAIRunner converts non-retryable 4xx errors to RunnerError."""
    endpoint = "https://api.openai.com/v1/chat/completions"
    respx.post(endpoint).respond(status_code=400, text="Invalid parameters")

    runner = OpenAIRunner(model_name="gpt-4o-mini", api_key="sk-test", max_retries=0)
    with pytest.raises(RunnerError, match="HTTP error 400"):
        runner.generate(prompt="Prueba")


@respx.mock
def test_openai_runner_network_request_error() -> None:
    """Ensure OpenAIRunner converts transport ConnectErrors to RunnerError."""
    endpoint = "https://api.openai.com/v1/chat/completions"
    respx.post(endpoint).mock(side_effect=httpx.ConnectError("Connection refused"))

    runner = OpenAIRunner(model_name="gpt-4o-mini", api_key="sk-test", max_retries=0)
    with pytest.raises(RunnerError, match="Network transport error"):
        runner.generate(prompt="Prueba")


def test_config_settings_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure get_settings parses custom environment variables correctly."""
    from chilango_bench.config import get_settings

    monkeypatch.setenv("OPENAI_API_KEY", "sk-custom")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://custom.api/v1")
    monkeypatch.setenv("CHILANGO_LOG_LEVEL", "debug")
    monkeypatch.setenv("CHILANGO_TIMEOUT_SECONDS", "45.5")
    monkeypatch.setenv("CHILANGO_MAX_RETRIES", "5")

    settings = get_settings()
    assert settings.openai_api_key == "sk-custom"
    assert settings.openai_base_url == "https://custom.api/v1"
    assert settings.log_level == "DEBUG"
    assert settings.timeout_seconds == 45.5
    assert settings.max_retries == 5
