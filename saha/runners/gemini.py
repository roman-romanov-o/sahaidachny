"""Gemini CLI subprocess runner implementation.

This module provides a runner for Google's Gemini CLI, allowing
Gemini models to be used as an alternative to Claude for certain agents.
"""

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

from saha.runners._utils import (
    FileChangeTracker,
    build_prompt_with_context,
    build_skills_prompt,
    extract_system_prompt,
    try_parse_json,
)
from saha.runners.base import Runner, RunnerResult

logger = logging.getLogger(__name__)


class GeminiRunner(Runner):
    """Runner that executes prompts via Gemini CLI subprocess.

    This runner invokes the `gemini` CLI tool as a subprocess,
    passing prompts and capturing output. It's useful for:
    - Using Gemini's capabilities for specific tasks
    - Cost optimization by using different models for different agents
    - Redundancy when one provider is unavailable

    Note: Gemini CLI must be installed and authenticated.
    See: https://github.com/google-gemini/gemini-cli
    """

    def __init__(
        self,
        model: str = "gemini-2.5-pro",
        working_dir: Path | None = None,
        sandbox: bool = False,
    ):
        """Initialize Gemini runner.

        Args:
            model: Gemini model to use (e.g., gemini-2.5-pro, gemini-2.5-flash).
            working_dir: Working directory for command execution.
            sandbox: Whether to run in sandboxed mode (limited tools).
        """
        self._model = model
        self._working_dir = working_dir or Path.cwd()
        self._sandbox = sandbox

    def run_agent(
        self,
        agent_spec_path: Path,
        prompt: str,
        context: dict[str, Any] | None = None,
        timeout: int = 300,
    ) -> RunnerResult:
        """Run an agent-style prompt via Gemini CLI.

        Unlike Claude Code, Gemini CLI doesn't have native agent support,
        so we embed the agent spec content (and referenced skills) into the prompt.

        Args:
            agent_spec_path: Path to agent spec (used to extract system prompt).
            prompt: The prompt to send.
            context: Additional context to pass.
            timeout: Maximum execution time in seconds.

        Returns:
            RunnerResult with Gemini's output.
        """
        system_prompt = extract_system_prompt(agent_spec_path)
        skills_prompt = build_skills_prompt(agent_spec_path, self._working_dir)
        full_prompt = build_prompt_with_context(prompt, context, system_prompt, skills_prompt)

        return self._run(full_prompt, timeout)

    def run_prompt(
        self,
        prompt: str,
        system_prompt: str | None = None,
        timeout: int = 300,
    ) -> RunnerResult:
        """Run a simple prompt via Gemini CLI.

        Args:
            prompt: The prompt to send.
            system_prompt: Optional system prompt.
            timeout: Maximum execution time in seconds.

        Returns:
            RunnerResult with the output.
        """
        full_prompt = build_prompt_with_context(prompt, None, system_prompt)
        return self._run(full_prompt, timeout)

    def _run(
        self,
        prompt: str,
        timeout: int = 300,
    ) -> RunnerResult:
        """Execute the Gemini CLI command.

        Uses FileChangeTracker to detect file modifications during execution.

        Args:
            prompt: Full prompt (with system prompt, skills, and context embedded).
            timeout: Maximum execution time.

        Returns:
            RunnerResult from execution.
        """
        tracker = FileChangeTracker(self._working_dir)
        cmd = self._build_command(prompt)
        logger.info(f"Running agent with {self.get_name()}")
        logger.info(f"Command: {' '.join(cmd)}")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self._working_dir,
            )

            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                return RunnerResult.failure(
                    f"Command timed out after {timeout} seconds",
                    exit_code=124,
                )
            except KeyboardInterrupt:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                raise

            if process.returncode != 0:
                return RunnerResult(
                    success=False,
                    output=stdout,
                    error=stderr or f"Exit code: {process.returncode}",
                    exit_code=process.returncode,
                )

            structured_output = try_parse_json(stdout) or {}

            files_changed, files_added = tracker.diff()
            if files_changed or files_added:
                structured_output["files_changed"] = files_changed
                structured_output["files_added"] = files_added

            return RunnerResult.success_result(
                output=stdout,
                structured_output=structured_output if structured_output else None,
            )

        except subprocess.TimeoutExpired:
            return RunnerResult.failure(
                f"Command timed out after {timeout} seconds",
                exit_code=124,
            )
        except FileNotFoundError:
            return RunnerResult.failure(
                "Gemini CLI not found. See: https://github.com/google-gemini/gemini-cli",
                exit_code=127,
            )
        except Exception as e:
            return RunnerResult.failure(str(e), exit_code=1)

    def is_available(self) -> bool:
        """Check if gemini CLI is available."""
        return shutil.which("gemini") is not None

    def get_name(self) -> str:
        """Get runner name."""
        return f"gemini-cli ({self._model})"

    def _build_command(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> list[str]:
        """Build the gemini CLI command.

        Gemini CLI supports:
        - gemini -p "prompt" for simple prompts
        - gemini --model <model> for model selection
        - gemini --sandbox for sandboxed mode

        Note: The --yolo flag does NOT exist in Gemini CLI.
        Non-interactive mode is the default for -p flag.

        Args:
            prompt: User prompt to send.
            system_prompt: System instructions (prepended to prompt).

        Returns:
            Command list for subprocess.
        """
        cmd = ["gemini"]

        # Model selection
        if self._model:
            cmd.extend(["--model", self._model])

        # Sandbox mode (disables dangerous tools)
        if self._sandbox:
            cmd.append("--sandbox")

        # Combine system prompt and user prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n---\n\n{prompt}"
        else:
            full_prompt = prompt

        cmd.extend(["-p", full_prompt])

        return cmd
