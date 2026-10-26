"""Base abstractions and protocols for model runners."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RunnerResponse:
    """Standardized response from an LLM invocation."""

    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_seconds: float = 0.0
    model_name: str = ""
    raw_response: dict[str, object] = field(default_factory=dict)


class BaseRunner(ABC):
    """Abstract base class for all model runners."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
    ) -> RunnerResponse:
        """Execute a completion prompt against the underlying model.

        Args:
            prompt: User/eval prompt.
            system_prompt: Optional system directive.
            temperature: Sampling temperature (default 0.0 for deterministic evaluation).
            max_tokens: Maximum tokens in generated completion.

        Returns:
            RunnerResponse containing generated text and execution metadata.
        """
