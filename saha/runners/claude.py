"""Claude Code subprocess runner implementation."""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from saha.runners.base import Runner, RunnerResult


class ClaudeRunner(Runner):
    """Runner that executes prompts via Claude Code CLI subprocess.

    This runner invokes the `claude` CLI tool as a subprocess,
    passing prompts and capturing output. It's useful for:
    - Leveraging Claude Code's built-in tools (Read, Write, Bash, etc.)
    - Using Claude Code's context management
    - Running native Claude Code agents from .claude/agents/
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        working_dir: Path | None = None,
        allowed_tools: list[str] | None = None,
    ):
        self._model = model
        self._working_dir = working_dir or Path.cwd()
        self._allowed_tools = allowed_tools

    def run_agent(
        self,
        agent_spec_path: Path,
        prompt: str,
        context: dict[str, Any] | None = None,
        timeout: int = 300,
    ) -> RunnerResult:
        """Run a native Claude Code agent.

        The agent_spec_path is used to derive the agent name. The agent must
        exist in .claude/agents/ directory with proper YAML frontmatter.
        """
        # Derive agent name from path (e.g., execution_implementer -> execution-implementer)
        agent_name = agent_spec_path.stem.replace("_", "-")

        # Build prompt with context
        full_prompt = self._build_agent_prompt(prompt, context)

        return self._run_with_agent(agent_name, full_prompt, timeout=timeout)

    def run_prompt(
        self,
        prompt: str,
        system_prompt: str | None = None,
        timeout: int = 300,
    ) -> RunnerResult:
        """Run a prompt via Claude Code CLI."""
        cmd = self._build_command(prompt, system_prompt)
        return self._execute_command(cmd, timeout)

    def _run_with_agent(
        self,
        agent_name: str,
        prompt: str,
        timeout: int = 300,
    ) -> RunnerResult:
        """Run a native Claude Code agent."""
        cmd = self._build_agent_command(agent_name, prompt)
        return self._execute_command(cmd, timeout)

    def _execute_command(
        self,
        cmd: list[str],
        timeout: int,
    ) -> RunnerResult:
        """Execute a claude CLI command and return the result."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self._working_dir,
            )

            if result.returncode != 0:
                return RunnerResult(
                    success=False,
                    output=result.stdout,
                    error=result.stderr or f"Exit code: {result.returncode}",
                    exit_code=result.returncode,
                )

            return RunnerResult.success_result(
                output=result.stdout,
                structured_output=self._try_parse_json(result.stdout),
            )

        except subprocess.TimeoutExpired:
            return RunnerResult.failure(
                f"Command timed out after {timeout} seconds",
                exit_code=124,
            )
        except FileNotFoundError:
            return RunnerResult.failure(
                "Claude CLI not found. Is it installed?",
                exit_code=127,
            )
        except Exception as e:
            return RunnerResult.failure(str(e), exit_code=1)

    def is_available(self) -> bool:
        """Check if claude CLI is available."""
        return shutil.which("claude") is not None

    def get_name(self) -> str:
        """Get runner name."""
        return f"claude-cli ({self._model})"

    def _build_command(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> list[str]:
        """Build the claude CLI command for direct prompts."""
        cmd = [
            "claude",
            "--print",  # Print output without interactive mode
            "--model", self._model,
        ]

        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])

        if self._allowed_tools:
            cmd.extend(["--allowedTools", ",".join(self._allowed_tools)])

        cmd.extend(["--prompt", prompt])

        return cmd

    def _build_agent_command(
        self,
        agent_name: str,
        prompt: str,
    ) -> list[str]:
        """Build the claude CLI command for native agent invocation."""
        cmd = [
            "claude",
            "--print",  # Print output without interactive mode
            "--agent", agent_name,  # Use native agent
        ]

        # Note: --model is typically set in agent frontmatter, but can override
        # Note: --allowedTools is set in agent frontmatter

        cmd.extend(["--prompt", prompt])

        return cmd

    def _build_agent_prompt(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Build the prompt with context for agent invocation."""
        parts = [prompt]

        if context:
            parts.extend([
                "",
                "## Context",
                "",
                "```json",
                json.dumps(context, indent=2, default=str),
                "```",
            ])

        return "\n".join(parts)

    def _try_parse_json(self, output: str) -> dict[str, Any] | None:
        """Try to extract JSON from output."""
        # Look for JSON blocks in the output
        lines = output.strip().split("\n")
        json_lines = []
        in_json = False

        for line in lines:
            if line.strip().startswith("{") or line.strip() == "```json":
                in_json = True
                if line.strip() != "```json":
                    json_lines.append(line)
            elif in_json:
                if line.strip() == "```":
                    break
                json_lines.append(line)

        if json_lines:
            try:
                parsed: dict[str, Any] = json.loads("\n".join(json_lines))
                return parsed
            except json.JSONDecodeError:
                pass

        return None


class MockRunner(Runner):
    """Mock runner for testing without actual LLM calls."""

    def __init__(self, responses: dict[str, str] | None = None):
        self._responses = responses or {}
        self._call_history: list[dict[str, Any]] = []

    def run_agent(
        self,
        agent_spec_path: Path,
        prompt: str,
        context: dict[str, Any] | None = None,
        timeout: int = 300,
    ) -> RunnerResult:
        """Record the call and return a mock response."""
        self._call_history.append({
            "type": "agent",
            "agent_spec_path": str(agent_spec_path),
            "prompt": prompt,
            "context": context,
        })

        key = agent_spec_path.stem
        if key in self._responses:
            return RunnerResult.success_result(self._responses[key])

        return RunnerResult.success_result(
            f"Mock response for agent: {agent_spec_path.name}"
        )

    def run_prompt(
        self,
        prompt: str,
        system_prompt: str | None = None,
        timeout: int = 300,
    ) -> RunnerResult:
        """Record the call and return a mock response."""
        self._call_history.append({
            "type": "prompt",
            "prompt": prompt,
            "system_prompt": system_prompt,
        })

        return RunnerResult.success_result("Mock response")

    def is_available(self) -> bool:
        """Mock runner is always available."""
        return True

    def get_name(self) -> str:
        """Get runner name."""
        return "mock"

    @property
    def call_history(self) -> list[dict[str, Any]]:
        """Get the call history for testing."""
        return self._call_history
