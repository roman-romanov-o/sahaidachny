"""Gemini CLI subprocess runner implementation.

This module provides a runner for Google's Gemini CLI, allowing
Gemini models to be used as an alternative to Claude for certain agents.
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from saha.runners.base import Runner, RunnerResult


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
        so we build the agent behavior into the system prompt.

        Args:
            agent_spec_path: Path to agent spec (used to extract system prompt).
            prompt: The prompt to send.
            context: Additional context to pass.
            timeout: Maximum execution time in seconds.

        Returns:
            RunnerResult with Gemini's output.
        """
        # Extract system prompt from agent spec if it exists
        system_prompt = self._extract_system_prompt(agent_spec_path)

        # Build full prompt with context
        full_prompt = self._build_prompt_with_context(prompt, context)

        return self._run(full_prompt, system_prompt, timeout)

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
        return self._run(prompt, system_prompt, timeout)

    def _run(
        self,
        prompt: str,
        system_prompt: str | None = None,
        timeout: int = 300,
    ) -> RunnerResult:
        """Execute the Gemini CLI command.

        Args:
            prompt: User prompt.
            system_prompt: System instructions.
            timeout: Maximum execution time.

        Returns:
            RunnerResult from execution.
        """
        cmd = self._build_command(prompt, system_prompt)

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

            return RunnerResult.success_result(
                output=stdout,
                structured_output=self._try_parse_json(stdout),
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
        - gemini --yolo for auto-accepting tool calls

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

        # Non-interactive mode - auto-accept tool calls
        cmd.append("--yolo")

        # Combine system prompt and user prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n---\n\n{prompt}"
        else:
            full_prompt = prompt

        cmd.extend(["-p", full_prompt])

        return cmd

    def _build_prompt_with_context(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Build prompt with context JSON block.

        Args:
            prompt: Base prompt.
            context: Context dict to include.

        Returns:
            Prompt with context appended.
        """
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

    def _extract_system_prompt(self, agent_spec_path: Path) -> str | None:
        """Extract system prompt from agent spec markdown file.

        The agent spec is expected to have YAML frontmatter followed by
        markdown content that serves as the system prompt.

        Args:
            agent_spec_path: Path to agent spec file.

        Returns:
            System prompt text, or None if file doesn't exist.
        """
        if not agent_spec_path.exists():
            return None

        content = agent_spec_path.read_text()

        # Skip YAML frontmatter if present
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                # Return the content after frontmatter
                return parts[2].strip()

        return content

    def _try_parse_json(self, output: str) -> dict[str, Any] | None:
        """Try to extract JSON from output.

        Args:
            output: Raw output from Gemini.

        Returns:
            Parsed JSON dict, or None if no valid JSON found.
        """
        # Look for JSON blocks in the output
        lines = output.strip().split("\n")
        json_lines: list[str] = []
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
