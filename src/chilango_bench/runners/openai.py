"""Runner for OpenAI-compatible chat completion APIs."""

import time
from typing import Any

import httpx

from chilango_bench.config import get_settings
from chilango_bench.core.exceptions import ConfigurationError, RunnerError
from chilango_bench.runners.base import BaseRunner, RunnerResponse


class OpenAIRunner(BaseRunner):
    """Universal runner for OpenAI-compatible HTTP endpoints (OpenAI, Ollama, vLLM, Groq)."""

    def __init__(
        self,
        model_name: str,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        client: httpx.Client | None = None,
    ):
        super().__init__(model_name)
        settings = get_settings()

        self.base_url = (base_url or settings.openai_base_url).rstrip("/")
        self.timeout_seconds = (
            timeout_seconds if timeout_seconds is not None else settings.timeout_seconds
        )
        self.max_retries = max_retries if max_retries is not None else settings.max_retries

        # Validate authentication credentials
        key = api_key if api_key is not None else settings.openai_api_key
        is_official_openai = "api.openai.com" in self.base_url
        if is_official_openai and not key:
            raise ConfigurationError(
                "OPENAI_API_KEY environment variable is required when using official OpenAI API."
            )

        self.api_key = key or "dummy-key-for-local-endpoint"

        self._client = client or httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout_seconds,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
    ) -> RunnerResponse:
        """Call the OpenAI-compatible endpoint with retries and timing."""
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        last_error: Exception | None = None
        attempt = 0

        while attempt <= self.max_retries:
            attempt += 1
            start_time = time.perf_counter()

            try:
                response = self._client.post("/chat/completions", json=payload)
                elapsed = time.perf_counter() - start_time

                # Check retryable status codes (429 Rate Limit, 5xx Server Error)
                if response.status_code in (429, 500, 502, 503, 504):
                    if attempt <= self.max_retries:
                        backoff = 0.5 * (2 ** (attempt - 1))
                        time.sleep(backoff)
                        continue
                    raise RunnerError(
                        f"API request failed with HTTP {response.status_code}: {response.text}"
                    )

                response.raise_for_status()
                data: dict[str, Any] = response.json()

                choices = data.get("choices", [])
                if not choices or not isinstance(choices, list):
                    raise RunnerError(f"Unexpected response format, missing choices: {data}")

                first_choice = choices[0]
                message_obj = first_choice.get("message", {})
                content = message_obj.get("content", "")

                usage = data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0) if isinstance(usage, dict) else 0
                completion_tokens = (
                    usage.get("completion_tokens", 0) if isinstance(usage, dict) else 0
                )

                raw_resp: dict[str, object] = {
                    "id": str(data.get("id", "")),
                    "model": str(data.get("model", self.model_name)),
                }

                return RunnerResponse(
                    text=content or "",
                    prompt_tokens=int(prompt_tokens),
                    completion_tokens=int(completion_tokens),
                    latency_seconds=elapsed,
                    model_name=self.model_name,
                    raw_response=raw_resp,
                )

            except httpx.TimeoutException as exc:
                last_error = exc
                if attempt <= self.max_retries:
                    time.sleep(0.5 * (2 ** (attempt - 1)))
                    continue
                raise RunnerError(
                    f"Request to {self.base_url} timed out after {self.timeout_seconds}s"
                ) from exc

            except httpx.HTTPStatusError as exc:
                raise RunnerError(
                    f"HTTP error {exc.response.status_code}: {exc.response.text}"
                ) from exc

            except httpx.RequestError as exc:
                last_error = exc
                if attempt <= self.max_retries:
                    time.sleep(0.5 * (2 ** (attempt - 1)))
                    continue
                raise RunnerError(f"Network transport error: {exc}") from exc

        raise RunnerError(f"Failed after {self.max_retries} retries: {last_error}")
