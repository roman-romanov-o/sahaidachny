"""Unit tests for FileChangeTracker.

Tests: TC-UNIT-001 through TC-UNIT-004
Covers: Modified file detection, added file detection, nested directories, mtime changes.
"""

import os
import time
from pathlib import Path

import pytest

from saha.runners._utils import FileChangeTracker


@pytest.fixture()
def project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory."""
    d = tmp_path / "project"
    d.mkdir()
    return d


class TestFileChangeTracker:
    """Tests for FileChangeTracker snapshot-based change detection."""

    def test_detects_modified_files(self, project_dir: Path) -> None:
        """TC-UNIT-001: FileChangeTracker detects modified files."""
        (project_dir / "file.txt").write_text("original content")
        tracker = FileChangeTracker(project_dir)

        # Modify file
        time.sleep(0.01)  # Ensure mtime changes
        (project_dir / "file.txt").write_text("new content")

        changed, added = tracker.diff()
        assert "file.txt" in changed
        assert len(added) == 0

    def test_detects_added_files(self, project_dir: Path) -> None:
        """TC-UNIT-002: FileChangeTracker detects added files."""
        tracker = FileChangeTracker(project_dir)

        # Create new file
        (project_dir / "new.txt").write_text("content")

        changed, added = tracker.diff()
        assert len(changed) == 0
        assert "new.txt" in added

    def test_handles_nested_directories(self, project_dir: Path) -> None:
        """TC-UNIT-003: FileChangeTracker handles nested directories."""
        tracker = FileChangeTracker(project_dir)

        # Create nested structure
        (project_dir / "src" / "utils").mkdir(parents=True)
        (project_dir / "src" / "utils" / "helper.py").write_text("code")

        changed, added = tracker.diff()
        assert "src/utils/helper.py" in added

    def test_detects_mtime_changes(self, project_dir: Path) -> None:
        """TC-UNIT-004: FileChangeTracker detects mtime changes."""
        file_path = project_dir / "file.txt"
        file_path.write_text("content")
        tracker = FileChangeTracker(project_dir)

        # Touch file to change mtime
        time.sleep(0.01)
        os.utime(file_path, None)

        changed, added = tracker.diff()
        assert "file.txt" in changed

    def test_skips_hidden_directories(self, project_dir: Path) -> None:
        """FileChangeTracker should skip .git, __pycache__, etc."""
        (project_dir / "src").mkdir()
        (project_dir / "src" / "main.py").write_text("code")
        tracker = FileChangeTracker(project_dir)

        # Create files in skip dirs (should be ignored)
        (project_dir / ".git").mkdir()
        (project_dir / ".git" / "index").write_text("git stuff")
        (project_dir / "__pycache__").mkdir()
        (project_dir / "__pycache__" / "mod.pyc").write_bytes(b"\x00")

        changed, added = tracker.diff()
        assert not any(".git" in f for f in added)
        assert not any("__pycache__" in f for f in added)

    def test_handles_nonexistent_root(self, tmp_path: Path) -> None:
        """FileChangeTracker handles nonexistent root directory gracefully."""
        tracker = FileChangeTracker(tmp_path / "nonexistent")
        changed, added = tracker.diff()
        assert changed == []
        assert added == []

    def test_empty_directory_no_initial_snapshot(self, project_dir: Path) -> None:
        """FileChangeTracker with empty dir then files added."""
        tracker = FileChangeTracker(project_dir)

        (project_dir / "a.txt").write_text("hello")
        (project_dir / "b.txt").write_text("world")

        changed, added = tracker.diff()
        assert len(changed) == 0
        assert sorted(added) == ["a.txt", "b.txt"]

    @pytest.mark.parametrize(
        ("before_files", "after_action", "expected_changed", "expected_added"),
        [
            pytest.param(
                {"a.txt": "v1"},
                {"modify": {"a.txt": "v2"}},
                ["a.txt"],
                [],
                id="modified_file",
            ),
            pytest.param(
                {"a.txt": "v1"},
                {"add": {"b.txt": "new"}},
                [],
                ["b.txt"],
                id="added_file",
            ),
            pytest.param(
                {},
                {"add": {"a.txt": "new"}},
                [],
                ["a.txt"],
                id="added_to_empty",
            ),
        ],
    )
    def test_parametrized_detection(
        self,
        project_dir: Path,
        before_files: dict[str, str],
        after_action: dict[str, dict[str, str]],
        expected_changed: list[str],
        expected_added: list[str],
    ) -> None:
        """Parametrized file change detection scenarios."""
        for name, content in before_files.items():
            (project_dir / name).write_text(content)

        tracker = FileChangeTracker(project_dir)
        time.sleep(0.01)

        for name, content in after_action.get("modify", {}).items():
            (project_dir / name).write_text(content)
        for name, content in after_action.get("add", {}).items():
            (project_dir / name).write_text(content)

        changed, added = tracker.diff()
        assert sorted(changed) == sorted(expected_changed)
        assert sorted(added) == sorted(expected_added)
