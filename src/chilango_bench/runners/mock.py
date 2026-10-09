"""Deterministic mock runner for offline testing and continuous integration."""

from chilango_bench.runners.base import BaseRunner, RunnerResponse


class MockRunner(BaseRunner):
    """Offline, deterministic model runner for testing."""

    def __init__(
        self,
        model_name: str = "mock-model",
        default_response: str = "B",
        canned_responses: dict[str, str] | None = None,
        simulated_latency: float = 0.005,
        simulated_tokens: tuple[int, int] = (15, 5),
        should_raise: Exception | None = None,
    ):
        super().__init__(model_name)
        self.default_response = default_response
        self.canned_responses = canned_responses or {}
        self.simulated_latency = simulated_latency
        self.prompt_tokens, self.completion_tokens = simulated_tokens
        self.should_raise = should_raise
        self.call_count = 0

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
    ) -> RunnerResponse:
        """Return a deterministic canned response without network calls."""
        self.call_count += 1

        if self.should_raise:
            raise self.should_raise

        response_text = self.default_response
        for key, val in self.canned_responses.items():
            if key in prompt:
                response_text = val
                break

        return RunnerResponse(
            text=response_text,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            latency_seconds=self.simulated_latency,
            model_name=self.model_name,
            raw_response={"mock": True, "call_index": self.call_count},
        )
