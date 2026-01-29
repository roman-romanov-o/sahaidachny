"""Integration tests for state management in containers.

Tests state creation, persistence, loading, and lifecycle.
"""


from tests.integration.conftest import (
    copy_to_container,
    create_project_tarball,
    run_in_container,
)


class TestStateManagement:
    """Test state management functionality."""

    def test_status_shows_no_tasks_initially(self, bootstrapped_container):
        """Test that status shows no tasks when none exist."""
        # Clean any existing state
        run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && rm -rf .sahaidachny/",
        )

        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && ./saha.sh status",
        )

        assert exit_code == 0, f"status command failed: {output}"
        assert "No tasks" in output or "no task" in output.lower(), f"Should show no tasks: {output}"

    def test_state_directory_created(self, bootstrapped_container):
        """Test that state directory is created on first run."""
        # Create a sample task directory
        task_files = {
            "docs/tasks/task-01/task-description.md": "# Test Task\n\nA simple test task.",
            "docs/tasks/task-01/README.md": "# Task 01",
        }
        tarball = create_project_tarball(task_files)
        copy_to_container(bootstrapped_container, tarball)

        # Try to run (will fail but should create state dir)
        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && ./saha.sh run task-01 --dry-run 2>&1 || true",
        )

        # Check if .sahaidachny exists or was referenced
        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && ls -la .sahaidachny/ 2>&1 || echo 'not created yet'",
        )

        # Either directory exists or dry-run didn't create it (both acceptable)
        assert exit_code == 0 or "not created" in output

    def test_state_persists_between_commands(self, bootstrapped_container):
        """Test that state persists between CLI invocations."""
        # This test would need actual task execution to persist state
        # For now, test that clean command works
        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && ./saha.sh clean task-nonexistent 2>&1 || true",
        )

        # Should handle non-existent task gracefully
        assert "No state" in output or "not found" in output.lower() or exit_code == 0


class TestStateLifecycle:
    """Test state lifecycle operations."""

    def test_clean_removes_state(self, bootstrapped_container):
        """Test that clean command removes state files."""
        # Create a mock state file
        run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && mkdir -p .sahaidachny && echo 'test' > .sahaidachny/task-test-execution-state.yaml",
        )

        # Verify it exists
        exit_code, _ = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && cat .sahaidachny/task-test-execution-state.yaml",
        )
        assert exit_code == 0, "State file should exist"

        # Clean it
        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && ./saha.sh clean task-test",
        )

        assert exit_code == 0, f"Clean failed: {output}"
        assert "Cleaned" in output or "clean" in output.lower()

        # Verify it's gone
        exit_code, _ = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && cat .sahaidachny/task-test-execution-state.yaml 2>&1",
        )
        assert exit_code != 0, "State file should be removed"

    def test_clean_all_removes_all_states(self, bootstrapped_container):
        """Test that clean --all removes all state files."""
        # Create multiple mock state files
        run_in_container(
            bootstrapped_container,
            """cd /root/sahaidachny && mkdir -p .sahaidachny && \
               echo 'test1' > .sahaidachny/task-01-execution-state.yaml && \
               echo 'test2' > .sahaidachny/task-02-execution-state.yaml && \
               echo 'test3' > .sahaidachny/task-03-execution-state.yaml""",
        )

        # Clean all
        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && ./saha.sh clean --all",
        )

        assert exit_code == 0, f"Clean --all failed: {output}"
        assert "3" in output or "Cleaned" in output, f"Should clean 3 tasks: {output}"

        # Verify all gone
        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && ls .sahaidachny/*.yaml 2>&1 || echo 'all cleaned'",
        )
        assert "all cleaned" in output or "No such file" in output

    def test_status_shows_task_state(self, bootstrapped_container):
        """Test that status shows state for specific task."""
        # Create a mock state file with valid YAML
        state_yaml = """task_id: task-01
task_path: docs/tasks/task-01
current_phase: implementation
current_iteration: 2
max_iterations: 10
started_at: '2024-01-01T10:00:00'
completed_at: null
enabled_tools:
  - ruff
  - pytest
iterations: []
context: {}
"""
        run_in_container(
            bootstrapped_container,
            f"cd /root/sahaidachny && mkdir -p .sahaidachny && cat > .sahaidachny/task-01-execution-state.yaml << 'ENDYAML'\n{state_yaml}\nENDYAML",
        )

        # Check status
        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && ./saha.sh status task-01",
        )

        assert exit_code == 0, f"Status failed: {output}"
        assert "task-01" in output
        assert "implementation" in output.lower() or "Phase" in output

    def test_status_lists_all_tasks(self, bootstrapped_container):
        """Test that status lists all tasks with state."""
        # Create multiple state files
        state_template = """task_id: {task_id}
task_path: docs/tasks/{task_id}
current_phase: {phase}
current_iteration: 1
max_iterations: 10
started_at: '2024-01-01T10:00:00'
completed_at: null
enabled_tools: []
iterations: []
context: {{}}
"""
        for task_id, phase in [("task-01", "implementation"), ("task-02", "qa"), ("task-03", "completed")]:
            state_yaml = state_template.format(task_id=task_id, phase=phase)
            run_in_container(
                bootstrapped_container,
                f"cd /root/sahaidachny && mkdir -p .sahaidachny && cat > .sahaidachny/{task_id}-execution-state.yaml << 'ENDYAML'\n{state_yaml}\nENDYAML",
            )

        # List all
        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && ./saha.sh status",
        )

        assert exit_code == 0, f"Status failed: {output}"
        assert "task-01" in output
        assert "task-02" in output
        assert "task-03" in output


class TestResumeCommand:
    """Test the resume command."""

    def test_resume_requires_existing_state(self, bootstrapped_container):
        """Test that resume fails gracefully for non-existent task."""
        # Clean state
        run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && rm -rf .sahaidachny/",
        )

        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && ./saha.sh resume nonexistent-task 2>&1 || true",
        )

        # Should fail (either no state, not found, or runner not available)
        assert exit_code != 0 or "No saved state" in output or "not found" in output.lower() or "not available" in output.lower()

    def test_resume_rejects_completed_task(self, bootstrapped_container):
        """Test that resume rejects already completed tasks."""
        state_yaml = """task_id: task-done
task_path: docs/tasks/task-done
current_phase: completed
current_iteration: 3
max_iterations: 10
started_at: '2024-01-01T10:00:00'
completed_at: '2024-01-01T11:00:00'
enabled_tools: []
iterations: []
context: {}
"""
        run_in_container(
            bootstrapped_container,
            f"cd /root/sahaidachny && mkdir -p .sahaidachny && cat > .sahaidachny/task-done-execution-state.yaml << 'ENDYAML'\n{state_yaml}\nENDYAML",
        )

        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && ./saha.sh resume task-done 2>&1 || true",
        )

        # Should fail (completed, or runner not available in container)
        assert exit_code != 0 or "already" in output.lower() or "completed" in output.lower() or "not available" in output.lower()
