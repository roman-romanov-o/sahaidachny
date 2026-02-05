"""Claude Code subprocess runner implementation."""

import json
import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.theme import Theme

from saha.runners.base import Runner, RunnerResult

logger = logging.getLogger(__name__)

# Theme for streaming output
_STREAM_THEME = Theme({
    "model": "cyan",  # Model's text responses
    "model.thinking": "dim cyan italic",  # Model's reasoning
    "tool": "dim",  # Tool calls (subdued)
    "tool.name": "dim yellow",  # Tool name in brackets
    "error": "bold red",
})

# Console for streaming output (separate from logging console)
_stream_console = Console(theme=_STREAM_THEME, highlight=False)


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
        stream_output: bool = False,
    ):
        self._model = model
        self._working_dir = working_dir or Path.cwd()
        self._allowed_tools = allowed_tools
        self._stream_output = stream_output

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
        logger.debug(f"Executing command: {' '.join(cmd)}")

        if self._stream_output:
            return self._execute_with_streaming(cmd, timeout)

        return self._execute_with_capture(cmd, timeout)

    def _execute_with_capture(
        self,
        cmd: list[str],
        timeout: int,
    ) -> RunnerResult:
        """Execute command with output capture (no streaming)."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self._working_dir,
            )

            logger.debug(f"Command exit code: {result.returncode}")
            logger.debug(f"Command stdout length: {len(result.stdout)}")
            if result.stderr:
                logger.debug(f"Command stderr: {result.stderr[:500]}")

            if result.returncode != 0:
                logger.warning(f"Claude CLI failed with exit code {result.returncode}: {result.stderr}")
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

    def _execute_with_streaming(
        self,
        cmd: list[str],
        timeout: int,
    ) -> RunnerResult:
        """Execute command with real-time output streaming using stream-json format."""
        # Modify command to use stream-json output format with partial messages for real-time streaming
        stream_cmd = cmd.copy()
        stream_cmd.extend(["--output-format", "stream-json", "--include-partial-messages"])

        try:
            process = subprocess.Popen(
                stream_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self._working_dir,
                bufsize=1,  # Line buffered
            )

            collected_text: list[str] = []
            tool_state: dict[str, Any] = {}  # Track current tool call state

            # Stream and parse NDJSON output in real-time
            if process.stdout:
                for line in process.stdout:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        event = json.loads(line)
                        # Only handle dict events, skip arrays/primitives
                        if isinstance(event, dict):
                            self._handle_stream_event(event, collected_text, tool_state)
                    except json.JSONDecodeError:
                        # Non-JSON line, just print it
                        print(line)

            # Collect stderr
            stderr = ""
            if process.stderr:
                stderr = process.stderr.read()
                if stderr:
                    sys.stderr.write(stderr)
                    sys.stderr.flush()

            process.wait(timeout=timeout)

            # Combine collected text as the output
            full_output = "".join(collected_text)

            logger.debug(f"Command exit code: {process.returncode}")
            logger.debug(f"Collected output length: {len(full_output)}")
            if stderr:
                logger.debug(f"Command stderr: {stderr[:500]}")

            if process.returncode != 0:
                logger.warning(f"Claude CLI failed with exit code {process.returncode}: {stderr}")
                return RunnerResult(
                    success=False,
                    output=full_output,
                    error=stderr or f"Exit code: {process.returncode}",
                    exit_code=process.returncode,
                )

            return RunnerResult.success_result(
                output=full_output,
                structured_output=self._try_parse_json(full_output),
            )

        except subprocess.TimeoutExpired:
            process.kill()
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

    def _handle_stream_event(
        self,
        event: dict[str, Any],
        collected_text: list[str],
        tool_state: dict[str, Any],
    ) -> None:
        """Handle a streaming event from claude CLI and print relevant info.

        Args:
            event: The parsed JSON event from the stream.
            collected_text: List to accumulate text output.
            tool_state: Mutable dict to track current tool call state.
                - current_tool: Name of tool being called (if any)
                - input_json: Accumulated JSON input for tool
                - last_was_tool: Whether last output was a tool call
                - text_buffer: Buffer for accumulating text before printing
        """
        event_type = event.get("type", "")

        if event_type == "stream_event":
            inner_event = event.get("event", {})
            if not isinstance(inner_event, dict):
                return
            inner_type = inner_event.get("type", "")

            if inner_type == "content_block_start":
                block = inner_event.get("content_block", {})
                if isinstance(block, dict):
                    if block.get("type") == "tool_use":
                        tool_state["current_tool"] = block.get("name", "unknown")
                        tool_state["input_json"] = ""
                    elif block.get("type") == "text":
                        # Starting text block - show indicator if coming from tools
                        if tool_state.get("last_was_tool"):
                            _stream_console.print("\n[model]▸[/model] ", end="")
                        tool_state["text_buffer"] = ""

            elif inner_type == "content_block_delta":
                delta = inner_event.get("delta", {})
                if not isinstance(delta, dict):
                    return
                if delta.get("type") == "text_delta":
                    text = delta.get("text", "")
                    # Print model text with styling
                    _stream_console.print(f"[model]{text}[/model]", end="")
                    collected_text.append(text)
                    tool_state["last_was_tool"] = False
                elif delta.get("type") == "input_json_delta":
                    # Accumulate tool input JSON
                    tool_state["input_json"] += delta.get("partial_json", "")

            elif inner_type == "content_block_stop":
                if tool_state.get("current_tool"):
                    self._print_tool_call(
                        tool_state["current_tool"],
                        tool_state.get("input_json", ""),
                    )
                    tool_state["current_tool"] = None
                    tool_state["input_json"] = ""
                    tool_state["last_was_tool"] = True
                else:
                    _stream_console.print()  # Newline after text block

        elif event_type == "assistant":
            pass  # Already streamed

        elif event_type == "user":
            # Tool result - show minimal feedback
            tool_result = event.get("tool_use_result", {})
            if isinstance(tool_result, dict):
                stderr = tool_result.get("stderr", "")
                if stderr:
                    _stream_console.print(f"[tool]  ⚠ {stderr[:100]}[/tool]")

        elif event_type == "error":
            error = event.get("error", {})
            if isinstance(error, dict):
                _stream_console.print(f"\n[error]✗ {error.get('message', 'Unknown error')}[/error]")
            else:
                _stream_console.print(f"\n[error]✗ {error}[/error]")

    def _print_tool_call(self, tool_name: str, input_json: str) -> None:
        """Print a formatted tool call with relevant details."""
        details = self._extract_tool_details(tool_name, input_json)
        # Format: [ToolName] details - tool name in yellow, rest dim
        if details:
            _stream_console.print(f"  [tool.name]\\[{tool_name}][/tool.name] [tool]{details}[/tool]")
        else:
            _stream_console.print(f"  [tool.name]\\[{tool_name}][/tool.name]")

    def _extract_tool_details(self, tool_name: str, input_json: str) -> str:
        """Extract human-readable details from tool input JSON."""
        if not input_json:
            return ""

        try:
            params = json.loads(input_json)
        except json.JSONDecodeError:
            return ""

        if not isinstance(params, dict):
            return ""

        # Extract relevant info based on tool type
        if tool_name == "Read":
            path = params.get("file_path", "")
            if path:
                # Show just filename or last 2 path components
                parts = path.split("/")
                return "/".join(parts[-2:]) if len(parts) > 2 else path

        elif tool_name == "Glob":
            pattern = params.get("pattern", "")
            path = params.get("path", "")
            if path:
                return f"{pattern} in {path}"
            return pattern

        elif tool_name == "Grep":
            pattern = params.get("pattern", "")
            path = params.get("path", ".")
            return f'"{pattern}" in {path}'

        elif tool_name == "Bash":
            cmd = params.get("command", "")
            desc = params.get("description", "")
            if desc:
                return desc
            # Show truncated command
            return cmd[:60] + "..." if len(cmd) > 60 else cmd

        elif tool_name == "Edit":
            path = params.get("file_path", "")
            if path:
                parts = path.split("/")
                return "/".join(parts[-2:]) if len(parts) > 2 else path

        elif tool_name == "Write":
            path = params.get("file_path", "")
            if path:
                parts = path.split("/")
                return "/".join(parts[-2:]) if len(parts) > 2 else path

        elif tool_name == "TodoWrite":
            todos = params.get("todos", [])
            return f"{len(todos)} items"

        elif tool_name.startswith("mcp__playwright__"):
            # Playwright tools - show the action
            action = tool_name.replace("mcp__playwright__", "")
            url = params.get("url", "")
            selector = params.get("selector", "")
            if url:
                return f"{action}: {url[:50]}"
            if selector:
                return f"{action}: {selector[:40]}"
            return action

        return ""

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

        # Prompt is a positional argument, must be last
        cmd.append(prompt)

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

        # Prompt is a positional argument, must be last
        cmd.append(prompt)

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
        """Try to extract JSON from output.

        Looks for JSON blocks in the output. If multiple JSON blocks exist,
        returns the last one (most likely the final output).
        """
        # Try to find JSON in code blocks first (```json ... ```)
        json_block_pattern = r"```json\s*\n(.*?)\n```"
        matches = re.findall(json_block_pattern, output, re.DOTALL)

        if matches:
            # Try each match from last to first (prefer later outputs)
            for match in reversed(matches):
                try:
                    parsed = json.loads(match.strip())
                    if isinstance(parsed, dict):
                        logger.debug(f"Parsed JSON from code block: {list(parsed.keys())}")
                        return parsed
                except json.JSONDecodeError:
                    continue

        # Fallback: look for standalone JSON object (not in code block)
        lines = output.strip().split("\n")
        json_blocks: list[list[str]] = []
        current_block: list[str] = []
        brace_count = 0

        for line in lines:
            stripped = line.strip()

            # Start of JSON object
            if stripped.startswith("{") and brace_count == 0:
                brace_count = stripped.count("{") - stripped.count("}")
                current_block = [line]
                if brace_count == 0:
                    # Single-line JSON
                    json_blocks.append(current_block)
                    current_block = []
            elif brace_count > 0:
                current_block.append(line)
                brace_count += stripped.count("{") - stripped.count("}")
                if brace_count <= 0:
                    json_blocks.append(current_block)
                    current_block = []
                    brace_count = 0

        # Try each block from last to first
        for block in reversed(json_blocks):
            try:
                parsed = json.loads("\n".join(block))
                if isinstance(parsed, dict):
                    logger.debug(f"Parsed standalone JSON: {list(parsed.keys())}")
                    return parsed
            except json.JSONDecodeError:
                continue

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
