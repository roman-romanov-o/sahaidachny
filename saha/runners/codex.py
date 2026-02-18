"""Codex CLI subprocess runner implementation."""

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from rich.console import Console

from saha.runners._utils import (
    FileChangeTracker,
    build_prompt_with_context,
    build_skills_prompt,
    extract_system_prompt,
    try_parse_json,
)
from saha.runners.base import Runner, RunnerResult
from saha.runners.usage import normalize_token_usage

logger = logging.getLogger(__name__)

# Console for streaming output
_console = Console()

# Backward-compatible alias for existing tests and imports
_FileChangeTracker = FileChangeTracker


class CodexRunner(Runner):
    """Runner that executes prompts via Codex CLI subprocess."""

    def __init__(
        self,
        model: str | None = None,
        working_dir: Path | None = None,
        sandbox: str | None = "workspace-write",
        dangerously_bypass: bool = False,
    ) -> None:
        self._model = model
        self._working_dir = working_dir or Path.cwd()
        self._sandbox = sandbox
        self._dangerously_bypass = dangerously_bypass

    def run_agent(
        self,
        agent_spec_path: Path,
        prompt: str,
        context: dict[str, Any] | None = None,
        timeout: int = 300,
    ) -> RunnerResult:
        """Run an agent-style prompt via Codex CLI.

        Codex CLI does not support native agent specs, so we embed the
        agent spec content (and referenced skills) into the prompt.
        """
        system_prompt = extract_system_prompt(agent_spec_path)
        skills_prompt = self._extract_skills_prompt(agent_spec_path)
        full_prompt = build_prompt_with_context(prompt, context, system_prompt, skills_prompt)
        return self._run(full_prompt, timeout)

    def run_prompt(
        self,
        prompt: str,
        system_prompt: str | None = None,
        timeout: int = 300,
    ) -> RunnerResult:
        """Run a simple prompt via Codex CLI."""
        full_prompt = build_prompt_with_context(prompt, None, system_prompt)
        return self._run(full_prompt, timeout)

    def is_available(self) -> bool:
        """Check if codex CLI is available."""
        return shutil.which("codex") is not None

    def get_name(self) -> str:
        """Get runner name."""
        if self._model:
            return f"codex-cli ({self._model})"
        return "codex-cli"

    def _run(self, prompt: str, timeout: int) -> RunnerResult:
        """Execute the Codex CLI command."""
        tracker = FileChangeTracker(self._working_dir)

        output_file = None
        try:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                output_file = Path(tmp.name)

            cmd = self._build_command(output_file)
            _console.print(f"[dim]Command: {' '.join(cmd[:4])}...[/dim]")

            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self._working_dir,
                bufsize=1,  # Line buffered
            )

            stdin_pipe = getattr(process, "stdin", None)
            stdout_pipe = getattr(process, "stdout", None)
            stderr_pipe = getattr(process, "stderr", None)
            can_stream = stdin_pipe is not None and stdout_pipe is not None

            if can_stream:
                # Send prompt and close stdin before streaming output.
                stdin_pipe.write(prompt)
                stdin_pipe.close()

                collected_stdout: list[str] = []
                interrupted = False
                try:
                    try:
                        for line in stdout_pipe:
                            # Display structured JSON events if available
                            self._display_json_event(line)
                            collected_stdout.append(line)
                    except KeyboardInterrupt:
                        _console.print("\n[yellow]⚠ Interrupt received, terminating Codex...[/yellow]")
                        interrupted = True

                    if not interrupted:
                        # Wait for process to complete
                        process.wait(timeout=timeout)
                    else:
                        # Terminate the process
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()

                    stdout = "".join(collected_stdout)
                    stderr = stderr_pipe.read() if stderr_pipe else ""

                    if interrupted:
                        raise KeyboardInterrupt
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout = "".join(collected_stdout)
                    stderr = stderr_pipe.read() if stderr_pipe else ""
                    return RunnerResult.failure(
                        f"Command timed out after {timeout} seconds",
                        exit_code=124,
                    )
                except KeyboardInterrupt:
                    _console.print("\n[yellow]Codex interrupted by user[/yellow]")
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    raise
            else:
                # Compatibility path for tests and mocked Popen objects without pipe attrs.
                try:
                    stdout, stderr = process.communicate(prompt, timeout=timeout)
                    stdout = stdout or ""
                    stderr = stderr or ""
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate()
                    return RunnerResult.failure(
                        f"Command timed out after {timeout} seconds",
                        exit_code=124,
                    )
                except KeyboardInterrupt:
                    _console.print("\n[yellow]Codex interrupted by user[/yellow]")
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

            raw_stdout = stdout
            text_output = stdout
            if output_file and output_file.exists():
                try:
                    last_message = output_file.read_text()
                    if last_message.strip():
                        text_output = last_message
                except OSError:
                    logger.debug("Failed to read Codex output file")

            structured_output = try_parse_json(text_output) or {}
            token_usage = self._extract_token_usage(text_output, structured_output, raw_stdout)
            if token_usage is None:
                token_usage = self._extract_token_usage_from_session_logs()

            files_changed, files_added = tracker.diff()
            if files_changed or files_added:
                structured_output["files_changed"] = files_changed
                structured_output["files_added"] = files_added

            return RunnerResult.success_result(
                output=text_output,
                structured_output=structured_output if structured_output else None,
                token_usage=token_usage,
            )

        except FileNotFoundError:
            return RunnerResult.failure(
                "Codex CLI not found. Is it installed?",
                exit_code=127,
            )
        except Exception as e:
            return RunnerResult.failure(str(e), exit_code=1)
        finally:
            if output_file and output_file.exists():
                try:
                    output_file.unlink()
                except OSError:
                    logger.debug("Failed to remove Codex output file")

    def _display_json_event(self, line: str) -> None:
        """Parse and display JSON events from Codex CLI output."""
        line = line.strip()
        if not line:
            return

        try:
            event = json.loads(line)
            event_type = event.get("type")

            if event_type == "thread.started":
                _console.print(f"[dim]Thread started: {event.get('thread_id', 'unknown')}[/dim]")
            elif event_type == "turn.started":
                _console.print("[cyan]▶ Turn started[/cyan]")
            elif event_type == "turn.completed":
                usage = event.get("usage", {})
                if usage:
                    _console.print(
                        f"[green]✓ Turn completed[/green] "
                        f"[dim](input: {usage.get('input_tokens', 0)}, "
                        f"output: {usage.get('output_tokens', 0)})[/dim]"
                    )
                else:
                    _console.print("[green]✓ Turn completed[/green]")
            elif event_type == "item.started":
                item = event.get("item", {})
                item_type = item.get("type")
                if item_type == "command_execution":
                    cmd = item.get("command", "")
                    _console.print(f"[yellow]⚙[/yellow] Executing: [dim]{cmd[:80]}...[/dim]")
                elif item_type == "reasoning":
                    _console.print("[blue]💭 Reasoning...[/blue]")
                elif item_type == "agent_message":
                    _console.print("[cyan]💬 Agent message[/cyan]")
            elif event_type == "item.completed":
                item = event.get("item", {})
                item_type = item.get("type")
                if item_type == "command_execution":
                    exit_code = item.get("exit_code", 0)
                    status_symbol = "✓" if exit_code == 0 else "✗"
                    status_color = "green" if exit_code == 0 else "red"
                    _console.print(f"[{status_color}]{status_symbol} Command completed (exit: {exit_code})[/{status_color}]")
                elif item_type == "reasoning":
                    text = item.get("text", "")
                    if text:
                        _console.print(f"[blue]💭[/blue] {text[:100]}...")
                elif item_type == "agent_message":
                    text = item.get("text", "")
                    if text and len(text) < 200:
                        _console.print(f"[cyan]💬[/cyan] {text}")
            else:
                # For unknown events, just log them at debug level
                logger.debug(f"Codex event: {event_type}")

        except json.JSONDecodeError:
            # Not JSON, might be raw output - display as-is
            if line:
                sys.stdout.write(line + "\n")
                sys.stdout.flush()

    def _build_command(self, output_file: Path) -> list[str]:
        """Build the codex exec command."""
        cmd = [
            "codex",
            "exec",
            "-",  # Read prompt from stdin
            "--output-last-message",
            str(output_file),
            "--json",  # Enable JSON streaming output
            "--color",
            "never",
            "--cd",
            str(self._working_dir),
            "--skip-git-repo-check",
        ]

        if self._model:
            cmd.extend(["--model", self._model])

        if self._dangerously_bypass:
            cmd.append("--dangerously-bypass-approvals-and-sandbox")
        elif self._sandbox:
            cmd.extend(["--sandbox", self._sandbox])

        return cmd

    def _extract_skills_prompt(self, agent_spec_path: Path) -> str | None:
        """Extract and render referenced skills for Codex prompts."""
        return build_skills_prompt(agent_spec_path, self._working_dir)

    def _build_prompt_with_context(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
        system_prompt: str | None = None,
        skills_prompt: str | None = None,
    ) -> str:
        """Backward-compatible wrapper for prompt building."""
        return build_prompt_with_context(prompt, context, system_prompt, skills_prompt)

    def _extract_token_usage(
        self,
        text_output: str,
        structured_output: dict[str, Any] | None,
        raw_stdout: str,
    ) -> dict[str, int] | None:
        """Extract token usage from codex outputs."""
        raw_candidates: list[dict[str, Any]] = []

        if structured_output:
            self._collect_usage_candidates(structured_output, raw_candidates)

        for payload in self._parse_json_payloads(raw_stdout):
            self._collect_usage_candidates(payload, raw_candidates)

        if text_output and text_output != raw_stdout:
            for payload in self._parse_json_payloads(text_output):
                self._collect_usage_candidates(payload, raw_candidates)

        if not raw_candidates:
            return None

        return normalize_token_usage(raw_candidates[-1])

    def _parse_json_payloads(self, text: str) -> list[Any]:
        """Parse JSON payloads from a string (single JSON or JSONL)."""
        payloads: list[Any] = []
        if not text:
            return payloads

        stripped = text.strip()
        if stripped:
            try:
                payloads.append(json.loads(stripped))
                return payloads
            except json.JSONDecodeError:
                pass

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payloads.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        parsed_block = try_parse_json(text)
        if parsed_block is not None:
            payloads.append(parsed_block)

        return payloads

    def _collect_usage_candidates(self, payload: Any, raw_candidates: list[dict[str, Any]]) -> None:
        """Collect raw usage dicts from nested payloads."""
        if isinstance(payload, dict):
            usage = payload.get("usage")
            if isinstance(usage, dict):
                raw_candidates.append(usage)
            token_usage = payload.get("token_usage")
            if isinstance(token_usage, dict):
                raw_candidates.append(token_usage)

            normalized = normalize_token_usage(payload)
            if normalized:
                raw_candidates.append(payload)

            for value in payload.values():
                self._collect_usage_candidates(value, raw_candidates)
        elif isinstance(payload, list):
            for item in payload:
                self._collect_usage_candidates(item, raw_candidates)

    def _extract_token_usage_from_session_logs(self) -> dict[str, int] | None:
        """Best-effort extraction from Codex session JSONL logs."""
        codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
        sessions_dir = codex_home / "sessions"
        if not sessions_dir.exists():
            return None

        log_files = sorted(
            sessions_dir.rglob("rollout-*.jsonl"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not log_files:
            return None

        latest_log = log_files[0]
        try:
            lines = latest_log.read_text().splitlines()
        except OSError:
            return None

        raw_candidates: list[dict[str, Any]] = []
        for line in lines[-200:]:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            self._collect_usage_candidates(payload, raw_candidates)

        if not raw_candidates:
            return None

        return normalize_token_usage(raw_candidates[-1])
