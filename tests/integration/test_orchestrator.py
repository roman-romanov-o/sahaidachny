"""Integration tests for orchestrator loop phases in containers.

Tests each phase of the agentic loop: Implementation, QA, Code Quality, Manager, DoD.
"""

from tests.integration.conftest import (
    copy_to_container,
    create_project_tarball,
    run_in_container,
    run_python_in_container,
)


class TestRunCommand:
    """Test the run command."""

    def test_run_requires_task_path(self, bootstrapped_container):
        """Test that run fails gracefully when task path doesn't exist."""
        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && ./saha.sh run nonexistent-task 2>&1 || true",
        )

        assert exit_code != 0 or "does not exist" in output.lower() or "not found" in output.lower()

    def test_run_dry_run_mode(self, bootstrapped_container):
        """Test that --dry-run doesn't actually execute."""
        # Create task directory
        task_files = {
            "docs/tasks/task-01/task-description.md": "# Test Task\n\nSimple test.",
            "docs/tasks/task-01/README.md": "# Task 01",
        }
        tarball = create_project_tarball(task_files)
        copy_to_container(bootstrapped_container, tarball)

        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && ./saha.sh run task-01 --dry-run",
        )

        assert exit_code == 0, f"Dry run failed: {output}"
        assert "DRY RUN" in output or "dry" in output.lower()
        assert "Would execute" in output or "without making changes" in output.lower()

    def test_run_with_max_iterations(self, bootstrapped_container):
        """Test that --max-iter option is accepted."""
        task_files = {
            "docs/tasks/task-02/task-description.md": "# Test Task 2",
            "docs/tasks/task-02/README.md": "# Task 02",
        }
        tarball = create_project_tarball(task_files)
        copy_to_container(bootstrapped_container, tarball)

        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && ./saha.sh run task-02 --max-iter 3 --dry-run",
        )

        assert exit_code == 0, f"Run with max-iter failed: {output}"
        assert "3" in output or "iterations" in output.lower()

    def test_run_with_specific_tools(self, bootstrapped_container):
        """Test that --tools option limits enabled tools."""
        task_files = {
            "docs/tasks/task-03/task-description.md": "# Test Task 3",
            "docs/tasks/task-03/README.md": "# Task 03",
        }
        tarball = create_project_tarball(task_files)
        copy_to_container(bootstrapped_container, tarball)

        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && ./saha.sh run task-03 --tools ruff,pytest --dry-run",
        )

        assert exit_code == 0, f"Run with tools failed: {output}"

    def test_run_verbose_output(self, bootstrapped_container):
        """Test that --verbose provides more output."""
        task_files = {
            "docs/tasks/task-04/task-description.md": "# Test Task 4",
            "docs/tasks/task-04/README.md": "# Task 04",
        }
        tarball = create_project_tarball(task_files)
        copy_to_container(bootstrapped_container, tarball)

        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && ./saha.sh run task-04 --verbose --dry-run",
        )

        assert exit_code == 0, f"Verbose run failed: {output}"


class TestOrchestratorWithMockRunner:
    """Test orchestrator phases using mock runner (via Python directly)."""

    def test_mock_runner_available(self, bootstrapped_container):
        """Test that mock runner can be imported and used."""
        python_code = """
from saha.runners import MockRunner

runner = MockRunner()
print(f"Runner available: {runner.is_available()}")
print(f"Runner name: {runner.get_name()}")
"""
        exit_code, output = run_python_in_container(bootstrapped_container, python_code)

        assert exit_code == 0, f"Mock runner test failed: {output}"
        assert "Runner available: True" in output
        assert "mock" in output.lower()

    def test_state_manager_creates_state(self, bootstrapped_container):
        """Test that state manager can create and persist state."""
        python_code = """
from pathlib import Path
from saha.orchestrator.state import StateManager

manager = StateManager(Path(".sahaidachny"))
state = manager.create(
    task_id="test-task",
    task_path=Path("docs/tasks/test-task"),
    max_iterations=5,
    enabled_tools=["ruff", "pytest"],
)
print(f"Created state for: {state.task_id}")
print(f"Phase: {state.current_phase}")
print(f"Tools: {state.enabled_tools}")

loaded = manager.load("test-task")
print(f"Loaded task_id: {loaded.task_id}")
print(f"Loaded tools: {loaded.enabled_tools}")
"""
        exit_code, output = run_python_in_container(bootstrapped_container, python_code)

        assert exit_code == 0, f"State manager test failed: {output}"
        assert "Created state for: test-task" in output
        assert "ruff" in output
        assert "pytest" in output
        assert "Loaded task_id: test-task" in output

    def test_tool_registry_runs_tools(self, bootstrapped_container, clean_python_project):
        """Test that tool registry can execute tools."""
        tarball = create_project_tarball(clean_python_project)
        copy_to_container(bootstrapped_container, tarball)

        python_code = """
from pathlib import Path
from saha.tools import create_default_registry

registry = create_default_registry()

result = registry.run_tool("ruff", Path("clean_project/"))
print(f"Ruff passed: {result.passed}")
print(f"Ruff issues: {len(result.issues)}")

result = registry.run_tool("pytest", Path("tests/"))
print(f"Pytest status: {result.status}")
"""
        exit_code, output = run_python_in_container(bootstrapped_container, python_code)

        assert exit_code == 0, f"Tool registry test failed: {output}"
        assert "Ruff passed:" in output
        assert "Pytest status:" in output

    def test_hook_registry_triggers_hooks(self, bootstrapped_container):
        """Test that hook registry can trigger hooks."""
        python_code = """
from saha.hooks import HookRegistry
from saha.hooks.base import Hook, HookEvent
from saha.models.state import ExecutionState
from pathlib import Path
from datetime import datetime

class TestHook(Hook):
    def __init__(self):
        self.triggered = []

    @property
    def name(self):
        return "test"

    def execute(self, event, **kwargs):
        self.triggered.append(event.value)
        print(f"Hook triggered: {event.value}")

registry = HookRegistry()
test_hook = TestHook()
registry.register(test_hook)

state = ExecutionState(
    task_id="test",
    task_path=Path("test"),
    started_at=datetime.now(),
)

registry.trigger("loop_start", state=state)
registry.trigger("iteration_start", state=state)
registry.trigger("loop_complete", state=state)

print(f"Events triggered: {test_hook.triggered}")
"""
        exit_code, output = run_python_in_container(bootstrapped_container, python_code)

        assert exit_code == 0, f"Hook registry test failed: {output}"
        assert "Hook triggered: loop_start" in output
        assert "Hook triggered: iteration_start" in output
        assert "Hook triggered: loop_complete" in output


class TestPhaseTransitions:
    """Test phase transitions in the orchestrator."""

    def test_loop_phase_enum(self, bootstrapped_container):
        """Test that all loop phases are defined."""
        python_code = """
from saha.models.state import LoopPhase

phases = [p.value for p in LoopPhase]
print(f"Phases: {phases}")

assert "idle" in phases
assert "implementation" in phases
assert "qa" in phases
assert "code_quality" in phases
assert "manager" in phases
assert "dod_check" in phases
assert "stopped" in phases
assert "completed" in phases
assert "failed" in phases

print("All phases present!")
"""
        exit_code, output = run_python_in_container(bootstrapped_container, python_code)

        assert exit_code == 0, f"Phase enum test failed: {output}"
        assert "All phases present!" in output

    def test_state_phase_transitions(self, bootstrapped_container):
        """Test that state can transition between phases."""
        python_code = """
from pathlib import Path
from datetime import datetime
from saha.models.state import ExecutionState, LoopPhase

state = ExecutionState(
    task_id="test",
    task_path=Path("test"),
    started_at=datetime.now(),
)

assert state.current_phase == LoopPhase.IDLE
print(f"Initial phase: {state.current_phase.value}")

state.current_phase = LoopPhase.IMPLEMENTATION
print(f"After impl start: {state.current_phase.value}")

state.current_phase = LoopPhase.QA
print(f"QA phase: {state.current_phase.value}")

state.current_phase = LoopPhase.CODE_QUALITY
print(f"Quality phase: {state.current_phase.value}")

state.current_phase = LoopPhase.COMPLETED
print(f"Completed phase: {state.current_phase.value}")

print("Phase transitions work!")
"""
        exit_code, output = run_python_in_container(bootstrapped_container, python_code)

        assert exit_code == 0, f"Phase transition test failed: {output}"
        assert "Initial phase: idle" in output
        assert "QA phase: qa" in output
        assert "Phase transitions work!" in output
