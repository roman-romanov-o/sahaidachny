"""Integration tests for saha.context module."""

from pathlib import Path

import pytest

from saha.config.settings import Settings
from saha.context import clear_current_task, get_current_task, resolve_task_id, set_current_task


@pytest.fixture
def task_settings(tmp_path: Path) -> Settings:
    """Create settings pointing to a temporary directory."""
    state_dir = tmp_path / ".sahaidachny"
    state_dir.mkdir()
    task_base = tmp_path / "docs" / "tasks"
    task_base.mkdir(parents=True)
    return Settings(state_dir=state_dir, task_base_path=task_base)


@pytest.fixture
def task_with_dir(task_settings: Settings) -> str:
    """Create a task directory and return its folder name."""
    folder_name = "task-01-my-feature"
    (task_settings.task_base_path / folder_name).mkdir()
    return folder_name


class TestSetGetRoundTrip:
    def test_set_and_get(self, task_settings: Settings, task_with_dir: str) -> None:
        set_current_task(task_with_dir, task_settings)
        result = get_current_task(task_settings)
        assert result == task_with_dir

    def test_set_with_prefix_match(self, task_settings: Settings, task_with_dir: str) -> None:
        """Setting 'task-01' should work when 'task-01-my-feature' exists."""
        set_current_task("task-01", task_settings)
        result = get_current_task(task_settings)
        assert result == "task-01"

    def test_get_returns_none_when_no_context(self, task_settings: Settings) -> None:
        assert get_current_task(task_settings) is None


class TestSetNonexistentTask:
    def test_raises_for_nonexistent_task(self, task_settings: Settings) -> None:
        with pytest.raises(ValueError, match="No task directory found"):
            set_current_task("task-99-nonexistent", task_settings)

    def test_does_not_create_file_on_error(self, task_settings: Settings) -> None:
        with pytest.raises(ValueError):
            set_current_task("task-99-nonexistent", task_settings)
        context_file = task_settings.state_dir / "current-task"
        assert not context_file.exists()


class TestStaleContext:
    def test_stale_context_returns_none(self, task_settings: Settings, task_with_dir: str) -> None:
        """If the task directory is deleted after setting, get returns None."""
        set_current_task(task_with_dir, task_settings)

        # Delete the task directory
        (task_settings.task_base_path / task_with_dir).rmdir()

        result = get_current_task(task_settings)
        assert result is None


class TestClear:
    def test_clear_existing(self, task_settings: Settings, task_with_dir: str) -> None:
        set_current_task(task_with_dir, task_settings)
        assert clear_current_task(task_settings) is True
        assert get_current_task(task_settings) is None

    def test_clear_nonexistent(self, task_settings: Settings) -> None:
        assert clear_current_task(task_settings) is False


class TestResolveTaskId:
    def test_explicit_id_takes_priority(self, task_settings: Settings, task_with_dir: str) -> None:
        set_current_task(task_with_dir, task_settings)
        result = resolve_task_id("task-99-explicit", task_settings)
        assert result == "task-99-explicit"

    def test_falls_back_to_context(self, task_settings: Settings, task_with_dir: str) -> None:
        set_current_task(task_with_dir, task_settings)
        result = resolve_task_id(None, task_settings)
        assert result == task_with_dir

    def test_raises_when_no_id_and_no_context(self, task_settings: Settings) -> None:
        with pytest.raises(ValueError, match="No task ID provided"):
            resolve_task_id(None, task_settings)

    def test_explicit_none_uses_context(self, task_settings: Settings, task_with_dir: str) -> None:
        set_current_task(task_with_dir, task_settings)
        result = resolve_task_id(None, task_settings)
        assert result == task_with_dir


class TestStateDir:
    def test_set_creates_state_dir_if_missing(self, tmp_path: Path) -> None:
        """set_current_task should create .sahaidachny/ if it doesn't exist."""
        state_dir = tmp_path / ".sahaidachny"
        task_base = tmp_path / "docs" / "tasks"
        task_base.mkdir(parents=True)
        (task_base / "task-01-feature").mkdir()

        settings = Settings(state_dir=state_dir, task_base_path=task_base)
        set_current_task("task-01-feature", settings)

        assert state_dir.exists()
        assert get_current_task(settings) == "task-01-feature"
