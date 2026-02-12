"""End-to-end integration tests for the full agentic loop.

Tests complete workflow execution with mock runner.
"""

from tests.integration.conftest import (
    copy_to_container,
    create_project_tarball,
    run_in_container,
    run_python_in_container,
)


class TestEndToEndFlow:
    """Test complete end-to-end workflow."""

    def test_full_loop_with_mock_runner(self, bootstrapped_container, clean_python_project):
        """Test a full loop execution using mock runner."""
        # Create task artifacts
        task_files = {
            **clean_python_project,
            "docs/tasks/e2e-task/task-description.md": """# E2E Test Task

## Overview
Add a divide function to the clean_project module.

## Requirements
- Add a divide(a, b) function that divides a by b
- Handle division by zero with a ValueError
- Add tests for the new function
""",
            "docs/tasks/e2e-task/README.md": "# E2E Task",
            "docs/tasks/e2e-task/user-stories/US-001.md": """# US-001: Add Divide Function

## Acceptance Criteria
- [ ] divide(10, 2) returns 5
- [ ] divide(0, 5) returns 0
- [ ] divide(5, 0) raises ValueError
""",
        }
        tarball = create_project_tarball(task_files)
        copy_to_container(bootstrapped_container, tarball)

        # Run the full orchestrator with mock runner
        python_code = """
from pathlib import Path
from saha.config.settings import Settings
from saha.runners import MockRunner
from saha.tools import create_default_registry
from saha.hooks import HookRegistry
from saha.hooks.notification import LoggingHook
from saha.orchestrator.state import StateManager
from saha.orchestrator.loop import AgenticLoop, LoopConfig

settings = Settings(runner="mock", agents_path=Path("claude_plugin/agents"))
runner = MockRunner(responses={
    "execution-implementer": "code written",
    "execution-qa": "dod achieved",
    "execution-manager": "task updated",
    "execution-dod": "task complete",
})

tools = create_default_registry()
hooks = HookRegistry()
hooks.register(LoggingHook())

state_manager = StateManager(Path(".sahaidachny"))

orchestrator = AgenticLoop(
    runner=runner,
    tool_registry=tools,
    hook_registry=hooks,
    state_manager=state_manager,
    settings=settings,
)

config = LoopConfig(
    task_id="e2e-task",
    task_path=Path("docs/tasks/e2e-task"),
    max_iterations=3,
    enabled_tools=["ruff", "pytest"],
)

try:
    state = orchestrator.run(config)
    print(f"Final phase: {state.current_phase.value}")
    print(f"Iterations: {state.current_iteration}")
    print(f"Task ID: {state.task_id}")
    print(f"Runner calls: {len(runner.call_history)}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
"""
        exit_code, output = run_python_in_container(bootstrapped_container, python_code)

        assert exit_code == 0, f"E2E test failed: {output}"
        assert "Final phase:" in output
        assert "e2e-task" in output

    def test_loop_handles_qa_failure(self, bootstrapped_container):
        """Test that loop handles QA failure correctly."""
        task_files = {
            "docs/tasks/qa-fail-task/task-description.md": "# QA Fail Task",
            "docs/tasks/qa-fail-task/README.md": "# Task",
        }
        tarball = create_project_tarball(task_files)
        copy_to_container(bootstrapped_container, tarball)

        python_code = """
from pathlib import Path
from saha.config.settings import Settings
from saha.runners import MockRunner
from saha.tools import create_default_registry
from saha.hooks import HookRegistry
from saha.orchestrator.state import StateManager
from saha.orchestrator.loop import AgenticLoop, LoopConfig
from saha.runners.base import RunnerResult

settings = Settings(runner="mock", agents_path=Path("claude_plugin/agents"))
call_count = {"qa": 0}

class CountingMockRunner(MockRunner):
    def run_agent(self, agent_spec_path, prompt, context=None, timeout=300):
        key = agent_spec_path.stem
        if key == "execution-qa":
            call_count["qa"] += 1
            if call_count["qa"] == 1:
                return RunnerResult.success_result(
                    "dod failed",
                    structured_output={"dod_achieved": False, "fix_info": "Tests failing"}
                )
            else:
                return RunnerResult.success_result(
                    "dod passed",
                    structured_output={"dod_achieved": True}
                )
        elif key == "execution-dod":
            return RunnerResult.success_result(
                "complete",
                structured_output={"task_complete": True}
            )
        return super().run_agent(agent_spec_path, prompt, context, timeout)

runner = CountingMockRunner()
tools = create_default_registry()
hooks = HookRegistry()
state_manager = StateManager(Path(".sahaidachny"))

orchestrator = AgenticLoop(
    runner=runner,
    tool_registry=tools,
    hook_registry=hooks,
    state_manager=state_manager,
    settings=settings,
)

config = LoopConfig(
    task_id="qa-fail-task",
    task_path=Path("docs/tasks/qa-fail-task"),
    max_iterations=5,
    enabled_tools=[],
)

state = orchestrator.run(config)

print(f"Final phase: {state.current_phase.value}")
print(f"Total iterations: {state.current_iteration}")
qa_calls = call_count["qa"]
print(f"QA calls: {qa_calls}")

assert state.current_iteration >= 2
assert qa_calls >= 2
print("QA failure handling works!")
"""
        exit_code, output = run_python_in_container(bootstrapped_container, python_code)

        assert exit_code == 0, f"QA failure test failed: {output}"
        assert "QA failure handling works!" in output

    def test_loop_respects_max_iterations(self, bootstrapped_container):
        """Test that loop stops at max iterations."""
        task_files = {
            "docs/tasks/max-iter-task/task-description.md": "# Max Iter Task",
            "docs/tasks/max-iter-task/README.md": "# Task",
        }
        tarball = create_project_tarball(task_files)
        copy_to_container(bootstrapped_container, tarball)

        python_code = """
from pathlib import Path
from saha.config.settings import Settings
from saha.runners import MockRunner
from saha.tools import create_default_registry
from saha.hooks import HookRegistry
from saha.orchestrator.state import StateManager
from saha.orchestrator.loop import AgenticLoop, LoopConfig
from saha.runners.base import RunnerResult

class AlwaysFailQARunner(MockRunner):
    def run_agent(self, agent_spec_path, prompt, context=None, timeout=300):
        key = agent_spec_path.stem
        if key == "execution-qa":
            return RunnerResult.success_result(
                "always fail",
                structured_output={"dod_achieved": False, "fix_info": "Still failing"}
            )
        return super().run_agent(agent_spec_path, prompt, context, timeout)

settings = Settings(runner="mock", agents_path=Path("claude_plugin/agents"))
runner = AlwaysFailQARunner()
tools = create_default_registry()
hooks = HookRegistry()
state_manager = StateManager(Path(".sahaidachny"))

orchestrator = AgenticLoop(
    runner=runner,
    tool_registry=tools,
    hook_registry=hooks,
    state_manager=state_manager,
    settings=settings,
)

MAX_ITER = 3
config = LoopConfig(
    task_id="max-iter-task",
    task_path=Path("docs/tasks/max-iter-task"),
    max_iterations=MAX_ITER,
    enabled_tools=[],
)

state = orchestrator.run(config)

print(f"Final phase: {state.current_phase.value}")
print(f"Final iteration: {state.current_iteration}")
print(f"Max allowed: {MAX_ITER}")

assert state.current_iteration == MAX_ITER
assert state.current_phase.value != "completed"
print("Max iteration limit works!")
"""
        exit_code, output = run_python_in_container(bootstrapped_container, python_code)

        assert exit_code == 0, f"Max iterations test failed: {output}"
        assert "Max iteration limit works!" in output


class TestStatePersistence:
    """Test state persistence across operations."""

    def test_state_survives_restart(self, bootstrapped_container):
        """Test that state persists and can be resumed."""
        task_files = {
            "docs/tasks/persist-task/task-description.md": "# Persist Task",
            "docs/tasks/persist-task/README.md": "# Task",
        }
        tarball = create_project_tarball(task_files)
        copy_to_container(bootstrapped_container, tarball)

        # First: Create state
        python_code_create = """
from pathlib import Path
from saha.orchestrator.state import StateManager
from saha.models.state import LoopPhase

manager = StateManager(Path(".sahaidachny"))
state = manager.create(
    task_id="persist-task",
    task_path=Path("docs/tasks/persist-task"),
    max_iterations=10,
    enabled_tools=["ruff", "pytest"],
)

# Modify state
state.current_phase = LoopPhase.IMPLEMENTATION
state.current_iteration = 2
state.context["some_data"] = "test_value"
manager.save(state)

print(f"Created state: {state.task_id}")
print(f"Phase: {state.current_phase.value}")
print(f"Iteration: {state.current_iteration}")
"""
        exit_code, _ = run_python_in_container(bootstrapped_container, python_code_create)
        assert exit_code == 0

        # Second: Load state in new Python process
        python_code_load = """
from pathlib import Path
from saha.orchestrator.state import StateManager

manager = StateManager(Path(".sahaidachny"))
state = manager.load("persist-task")

print(f"Loaded state: {state.task_id}")
print(f"Phase: {state.current_phase.value}")
print(f"Iteration: {state.current_iteration}")
print(f"Context data: {state.context.get(chr(39) + "some_data" + chr(39))}")

assert state.task_id == "persist-task"
assert state.current_phase.value == "implementation"
assert state.current_iteration == 2

print("State persistence works!")
"""
        exit_code, output = run_python_in_container(bootstrapped_container, python_code_load)

        assert exit_code == 0, f"State load test failed: {output}"
        assert "State persistence works!" in output


class TestAgentSpecifications:
    """Test agent specification loading."""

    def test_agent_specs_exist(self, bootstrapped_container):
        """Test that all agent specs exist in the plugin."""
        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && ls -la claude_plugin/agents/",
        )

        assert exit_code == 0, f"Agent listing failed: {output}"
        assert "execution-implementer.md" in output
        assert "execution-qa.md" in output

    def test_agent_specs_readable(self, bootstrapped_container):
        """Test that agent specs can be read."""
        python_code = """
from pathlib import Path

agents_path = Path("claude_plugin/agents")

for agent_file in agents_path.glob("execution-*.md"):
    content = agent_file.read_text()
    print(f"{agent_file.name}: {len(content)} bytes")
    assert len(content) > 100
    assert "##" in content

print("All agent specs readable!")
"""
        exit_code, output = run_python_in_container(bootstrapped_container, python_code)

        assert exit_code == 0, f"Agent spec read test failed: {output}"
        assert "All agent specs readable!" in output
