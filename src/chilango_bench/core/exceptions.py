"""Core exceptions for chilango-bench."""


class ChilangoBenchError(Exception):
    """Base exception for all chilango-bench errors."""


class DatasetError(ChilangoBenchError):
    """Raised when a dataset cannot be read, parsed, or processed."""


class DatasetValidationError(DatasetError):
    """Raised when a dataset item fails schema or semantic validation."""

    def __init__(
        self, message: str, line_number: int | None = None, item_id: str | None = None
    ) -> None:
        super().__init__(message)
        self.line_number = line_number
        self.item_id = item_id


class RunnerError(ChilangoBenchError):
    """Raised when an error occurs during model execution."""


class EvaluatorError(ChilangoBenchError):
    """Raised when an evaluation or grading operation fails."""


class ConfigurationError(ChilangoBenchError):
    """Raised when invalid or missing configuration is encountered."""
