"""Rich-enhanced logging for Sahaidachny.

Provides colored, readable log output with filtering for verbose tool messages.
"""

import logging
from typing import Any, ClassVar

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

# Cossack-inspired theme: bold blue/yellow palette with good terminal visibility
SAHA_THEME = Theme({
    # Log levels
    "info": "bright_cyan",
    "warning": "bright_yellow",
    "error": "bold red",
    "critical": "bold white on red",
    "debug": "bright_black",
    # Execution phases
    "phase": "bold bright_blue",
    "phase.border": "bright_blue",
    "iteration": "bold bright_yellow",
    "iteration.border": "bright_yellow",
    "task": "bold bright_cyan",
    # Tool calls
    "tool": "bright_cyan",
    "tool.name": "bold bright_yellow",
    "tool.detail": "white",
    # Status indicators
    "success": "bold bright_green",
    "failure": "bold bright_red",
    # Prompt display
    "prompt": "white",
    "prompt.header": "bold bright_yellow",
    "prompt.border": "bright_yellow",
})

# Shared console instance
console = Console(theme=SAHA_THEME)


class SahaLogFilter(logging.Filter):
    """Filter out verbose/noisy log messages unless in debug mode."""

    VERBOSE_PATTERNS: ClassVar[list[str]] = [
        "Command stdout length:",
        "Command exit code:",
        "Executing command:",
        "Command stderr:",
    ]

    def __init__(self, debug: bool = False):
        super().__init__()
        self.debug = debug

    def filter(self, record: logging.LogRecord) -> bool:
        if self.debug:
            return True

        msg = record.getMessage()
        return not any(pattern in msg for pattern in self.VERBOSE_PATTERNS)


class SahaRichHandler(RichHandler):
    """Custom RichHandler with Sahaidachny-specific formatting."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            console=console,
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
            tracebacks_show_locals=False,
            markup=True,
            **kwargs,
        )


def setup_logging(verbose: bool = False) -> None:
    """Configure rich logging for CLI commands.

    Args:
        verbose: If True, set DEBUG level and show all messages;
                otherwise INFO level with filtering.
    """
    level = logging.DEBUG if verbose else logging.INFO

    # Create handler
    handler = SahaRichHandler()
    handler.addFilter(SahaLogFilter(debug=verbose))

    # Configure root logger
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%H:%M:%S]",
        handlers=[handler],
        force=True,
    )

    # Reduce noise from third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def log_phase_start(phase: str, task_id: str) -> None:
    """Log the start of a loop phase with prominent styling."""
    console.print(f"\n[phase.border]{'─' * 50}[/phase.border]")
    console.print(f"[phase]▶ {phase.upper()}[/phase] [task]{task_id}[/task]")
    console.print(f"[phase.border]{'─' * 50}[/phase.border]")


def log_phase_complete(phase: str, message: str = "") -> None:
    """Log successful phase completion."""
    msg = f"[success]✓ {phase} complete[/success]"
    if message:
        msg += f" - {message}"
    console.print(msg)


def log_phase_failed(phase: str, error: str) -> None:
    """Log phase failure."""
    console.print(f"[failure]✗ {phase} failed[/failure]: {error}")


def log_iteration_start(iteration: int, max_iterations: int) -> None:
    """Log the start of a loop iteration."""
    console.print(f"\n[iteration.border]━━━[/iteration.border] [iteration]Iteration {iteration}/{max_iterations}[/iteration] [iteration.border]━━━[/iteration.border]")


def log_iteration_complete(iteration: int, dod_achieved: bool, quality_passed: bool) -> None:
    """Log iteration completion with status."""
    status_parts = []
    if dod_achieved:
        status_parts.append("[success]DoD ✓[/success]")
    else:
        status_parts.append("[failure]DoD ✗[/failure]")
    if quality_passed:
        status_parts.append("[success]Quality ✓[/success]")
    else:
        status_parts.append("[failure]Quality ✗[/failure]")

    console.print(f"[iteration.border]━━━[/iteration.border] [iteration]Iteration {iteration} complete[/iteration]: {' | '.join(status_parts)}")


def log_tool_call(tool_name: str, details: str = "") -> None:
    """Log a tool being called."""
    msg = f"[tool.name]\\[{tool_name}][/tool.name]"
    if details:
        msg += f" [tool.detail]{details[:80]}{'...' if len(details) > 80 else ''}[/tool.detail]"
    console.print(msg)


def log_task_complete(task_id: str, iterations: int) -> None:
    """Log successful task completion."""
    console.print(f"\n[success]{'═' * 50}[/success]")
    console.print(f"[success]✓ TASK COMPLETE: {task_id}[/success]")
    console.print(f"[success]  Iterations: {iterations}[/success]")
    console.print(f"[success]{'═' * 50}[/success]")


def log_task_failed(task_id: str, error: str) -> None:
    """Log task failure."""
    console.print(f"\n[failure]{'═' * 50}[/failure]")
    console.print(f"[failure]✗ TASK FAILED: {task_id}[/failure]")
    console.print(f"[failure]  Error: {error}[/failure]")
    console.print(f"[failure]{'═' * 50}[/failure]")


def log_agent_prompt(agent_name: str, prompt: str) -> None:
    """Log the prompt being sent to an agent.

    Args:
        agent_name: Name of the agent (e.g., "Implementation", "QA").
        prompt: The full prompt text.
    """
    console.print(f"[prompt.border]┌─[/prompt.border] [prompt.header]Prompt → {agent_name}[/prompt.header]")
    # Indent each line of the prompt
    for line in prompt.split("\n"):
        console.print(f"[prompt.border]│[/prompt.border] [prompt]{line}[/prompt]")
    console.print(f"[prompt.border]└{'─' * 40}[/prompt.border]")
