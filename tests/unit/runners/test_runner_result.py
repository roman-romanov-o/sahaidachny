"""Unit tests for RunnerResult helper methods.

Tests: TC-UNIT-040 through TC-UNIT-042
Covers: success_result, failure, token inference.
"""

from saha.runners.base import RunnerResult


class TestRunnerResult:
    """Tests for RunnerResult dataclass helpers."""

    def test_success_result_creates_success(self) -> None:
        """TC-UNIT-040: RunnerResult.success_result creates success."""
        result = RunnerResult.success_result(
            output="Agent output",
            structured_output={"status": "done"},
            tokens_used=100,
        )

        assert result.success is True
        assert result.exit_code == 0
        assert result.output == "Agent output"
        assert result.structured_output is not None
        assert result.structured_output["status"] == "done"
        assert result.tokens_used == 100

    def test_failure_creates_failure(self) -> None:
        """TC-UNIT-041: RunnerResult.failure creates failure."""
        result = RunnerResult.failure(
            error="CLI not found",
            exit_code=127,
        )

        assert result.success is False
        assert result.exit_code == 127
        assert result.error == "CLI not found"
        assert result.output == ""

    def test_infers_total_tokens_from_usage(self) -> None:
        """TC-UNIT-042: RunnerResult infers total tokens from usage dict."""
        result = RunnerResult.success_result(
            output="test",
            token_usage={"input_tokens": 50, "output_tokens": 30},
        )

        assert result.tokens_used == 80
        assert result.token_usage is not None
        assert result.token_usage["input_tokens"] == 50
        assert result.token_usage["output_tokens"] == 30

    def test_success_result_defaults(self) -> None:
        """RunnerResult.success_result has reasonable defaults."""
        result = RunnerResult.success_result(output="hello")

        assert result.success is True
        assert result.output == "hello"
        assert result.structured_output is None
        assert result.tokens_used == 0
        assert result.token_usage is None
        assert result.error is None
        assert result.exit_code == 0

    def test_failure_defaults(self) -> None:
        """RunnerResult.failure has reasonable defaults."""
        result = RunnerResult.failure(error="something broke")

        assert result.success is False
        assert result.error == "something broke"
        assert result.exit_code == 1  # default exit code
        assert result.output == ""

    def test_infers_total_from_total_tokens_key(self) -> None:
        """Token inference uses total_tokens key directly."""
        result = RunnerResult.success_result(
            output="test",
            token_usage={"total_tokens": 200, "input_tokens": 150, "output_tokens": 50},
        )

        assert result.tokens_used == 200
