"""Current task context management.

Provides functions to set, get, clear, and resolve the active task context.
The current task is stored in `.sahaidachny/current-task` file.
"""

from pathlib import Path

from saha.config.settings import Settings

CONTEXT_FILENAME = "current-task"


def get_current_task(settings: Settings | None = None) -> str | None:
    """Read the current task ID from the context file.

    Returns None if the file doesn't exist or the task directory
    has been deleted (stale context).
    """
    settings = settings or Settings()
    context_file = settings.state_dir / CONTEXT_FILENAME

    if not context_file.exists():
        return None

    task_id = context_file.read_text().strip()
    if not task_id:
        return None

    # Validate the task directory still exists
    task_path = _find_task_dir(task_id, settings)
    if task_path is None:
        return None

    return task_id


def set_current_task(task_id: str, settings: Settings | None = None) -> None:
    """Set the current task context.

    Validates that the task directory exists before writing.

    Raises:
        ValueError: If no matching task directory is found.
    """
    settings = settings or Settings()
    task_path = _find_task_dir(task_id, settings)

    if task_path is None:
        raise ValueError(f"No task directory found for '{task_id}' in {settings.task_base_path}")

    settings.state_dir.mkdir(parents=True, exist_ok=True)
    context_file = settings.state_dir / CONTEXT_FILENAME
    context_file.write_text(task_id)


def clear_current_task(settings: Settings | None = None) -> bool:
    """Clear the current task context.

    Returns True if a context was cleared, False if none existed.
    """
    settings = settings or Settings()
    context_file = settings.state_dir / CONTEXT_FILENAME

    if not context_file.exists():
        return False

    context_file.unlink()
    return True


def resolve_task_id(explicit_id: str | None = None, settings: Settings | None = None) -> str:
    """Resolve the task ID from explicit argument or current context.

    Priority:
    1. Explicit argument (if provided)
    2. Current task context file
    3. Raise ValueError

    Raises:
        ValueError: If no task ID can be resolved.
    """
    if explicit_id is not None:
        return explicit_id

    settings = settings or Settings()
    current = get_current_task(settings)
    if current is not None:
        return current

    raise ValueError(
        "No task ID provided and no current task set. "
        "Use 'saha use <task-id>' to set the active task."
    )


def _find_task_dir(task_id: str, settings: Settings) -> Path | None:
    """Find a task directory matching the task ID.

    Supports both exact match (task_base_path/task_id) and
    prefix match (task_base_path/task-XX-*).
    """
    base = settings.task_base_path

    # Exact match
    exact = base / task_id
    if exact.is_dir():
        return exact

    # Prefix match (e.g., task-01 matches task-01-my-feature)
    if base.is_dir():
        for entry in base.iterdir():
            if entry.is_dir() and entry.name.startswith(f"{task_id}-"):
                return entry

    return None
