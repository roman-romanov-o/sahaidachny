"""Abstract base runner interface for LLM-agnostic execution."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class RunnerResult:
    """Result from running an LLM agent."""

    success: bool
    output: str
    structured_output: dict[str, Any] | None = None
    error: str | None = None
    tokens_used: int = 0
    token_usage: dict[str, int] | None = None
    exit_code: int = 0

    @classmethod
    def failure(cls, error: str, exit_code: int = 1) -> "RunnerResult":
        """Create a failure result."""
        return cls(
            success=False,
            output="",
            error=error,
            exit_code=exit_code,
        )

    @classmethod
    def success_result(
        cls,
        output: str,
        structured_output: dict[str, Any] | None = None,
        tokens_used: int | None = None,
        token_usage: dict[str, int] | None = None,
    ) -> "RunnerResult":
        """Create a success result."""
        if tokens_used is None and token_usage:
            tokens_used = _infer_total_tokens(token_usage)
        if tokens_used is None:
            tokens_used = 0
        return cls(
            success=True,
            output=output,
            structured_output=structured_output,
            tokens_used=tokens_used,
            token_usage=token_usage,
        )


def _infer_total_tokens(token_usage: dict[str, int]) -> int:
    """Infer total tokens from a usage dict."""
    for key in ("total_tokens", "total"):
        value = token_usage.get(key)
        if isinstance(value, int):
            return value
    input_tokens = token_usage.get("input_tokens")
    output_tokens = token_usage.get("output_tokens")
    if isinstance(input_tokens, int) and isinstance(output_tokens, int):
        return input_tokens + output_tokens
    if isinstance(input_tokens, int):
        return input_tokens
    if isinstance(output_tokens, int):
        return output_tokens
    return 0


class Runner(ABC):
    """Abstract base class for LLM runners.

    This interface allows the orchestrator to be LLM-agnostic.
    Implementations can use Claude Code CLI, direct API calls, or other LLMs.
    """

    @abstractmethod
    def run_agent(
        self,
        agent_spec_path: Path,
        prompt: str,
        context: dict[str, Any] | None = None,
        timeout: int = 300,
    ) -> RunnerResult:
        """Run an agent with the given specification and prompt.

        Args:
            agent_spec_path: Path to the agent specification file (markdown).
            prompt: The prompt to send to the agent.
            context: Additional context to pass to the agent.
            timeout: Maximum execution time in seconds.

        Returns:
            RunnerResult with the agent's output.
        """
        ...

    @abstractmethod
    def run_prompt(
        self,
        prompt: str,
        system_prompt: str | None = None,
        timeout: int = 300,
    ) -> RunnerResult:
        """Run a simple prompt without agent specification.

        Args:
            prompt: The prompt to send.
            system_prompt: Optional system prompt.
            timeout: Maximum execution time in seconds.

        Returns:
            RunnerResult with the output.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the runner is available and properly configured."""
        ...

    @abstractmethod
    def get_name(self) -> str:
        """Get the runner name for identification."""
        ...
