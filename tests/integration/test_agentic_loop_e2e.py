"""End-to-end integration tests for the complete agentic loop.

These tests exercise the full Sahaidachny workflow with realistic task artifacts
and the IntelligentMockRunner that simulates LLM behavior.

The tests validate:
- Full loop execution through all 5 phases
- QA failure and retry handling
- Code quality feedback loops
- State persistence and resumption
- DoD verification
"""

from pathlib import Path

from tests.integration.conftest import (
    copy_to_container,
    create_project_tarball,
    run_in_container,
    run_python_in_container,
)


# Sample task files that exercise the full Sahaidachny schema
SAMPLE_TASK_FILES = {
    # Task description
    "docs/tasks/add-string-utils/task-description.md": """# Add String Utilities

## Overview
Add string utility functions to the project's utility module.

## Goals
- Create a `reverse_string` function in `sample_project/utils.py`
- Create a `capitalize_words` function in `sample_project/utils.py`
- Add comprehensive tests

## Target File
The implementation should be in `sample_project/utils.py`.

## Success Criteria
- All functions have proper type hints
- All functions have docstrings
- All tests pass
""",
    # README
    "docs/tasks/add-string-utils/README.md": """# Task: Add String Utilities

This task adds string utility functions to the sample project.
""",
    # User story
    "docs/tasks/add-string-utils/user-stories/US-001.md": """# US-001: String Reversal Function

## Description
As a developer, I want a function to reverse strings so that I can easily transform text.

## Status
In Progress

## Acceptance Criteria
- [ ] `reverse_string(s)` returns the reversed string
- [ ] Empty strings are handled correctly
- [ ] Unicode strings are supported
- [ ] Type hints are present
- [ ] Unit tests exist and pass
""",
    "docs/tasks/add-string-utils/user-stories/US-002.md": """# US-002: Capitalize Words Function

## Description
As a developer, I want a function to capitalize each word in a string.

## Status
In Progress

## Acceptance Criteria
- [ ] `capitalize_words(s)` capitalizes the first letter of each word
- [ ] Already capitalized words remain unchanged
- [ ] Empty strings return empty strings
- [ ] Type hints are present
- [ ] Unit tests exist and pass
""",
    # Implementation plan
    "docs/tasks/add-string-utils/implementation-plan/phase-01.md": """# Phase 1: Core Implementation

## Status
Pending

## Objectives
1. Create `sample_project/utils.py` with both utility functions
2. Add proper type hints and docstrings
3. Create test file `tests/test_utils.py`

## Acceptance Criteria
- Both functions implemented
- All tests pass
- Code quality checks pass
""",
    # Test specifications
    "docs/tasks/add-string-utils/test-specs/test-cases.md": """# Test Specifications

## reverse_string Tests
- `reverse_string("hello")` -> `"olleh"`
- `reverse_string("")` -> `""`
- `reverse_string("a")` -> `"a"`

## capitalize_words Tests
- `capitalize_words("hello world")` -> `"Hello World"`
- `capitalize_words("")` -> `""`
- `capitalize_words("HELLO")` -> `"HELLO"`
""",
}

# Sample Python project to work with
SAMPLE_PROJECT_FILES = {
    "sample_project/__init__.py": '"""Sample project package."""\n',
    "sample_project/main.py": '''"""Main module with core functions."""


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b
''',
    "tests/__init__.py": "",
    "tests/test_main.py": '''"""Tests for main module."""

from sample_project.main import add, multiply


def test_add():
    """Test addition."""
    assert add(2, 3) == 5
    assert add(-1, 1) == 0


def test_multiply():
    """Test multiplication."""
    assert multiply(2, 3) == 6
    assert multiply(0, 5) == 0
''',
    "pyproject.toml": """[project]
name = "sample-project"
version = "0.1.0"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]
""",
}


class TestAgenticLoopE2E:
    """End-to-end tests for the complete agentic loop."""

    def test_full_loop_execution(self, bootstrapped_container):
        """Test a complete agentic loop execution with IntelligentMockRunner."""
        # Combine task files and project files
        all_files = {**SAMPLE_TASK_FILES, **SAMPLE_PROJECT_FILES}
        tarball = create_project_tarball(all_files)
        copy_to_container(bootstrapped_container, tarball)

        # Run the full agentic loop
        python_code = '''
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, "/root/sahaidachny")

from saha.config.settings import Settings
from saha.runners import IntelligentMockRunner
from saha.tools import create_default_registry
from saha.hooks import HookRegistry
from saha.hooks.notification import LoggingHook
from saha.orchestrator.state import StateManager
from saha.orchestrator.loop import AgenticLoop, LoopConfig

# Setup
settings = Settings(runner="mock", agents_path=Path("claude_plugin/agents"))
runner = IntelligentMockRunner(
    working_dir=Path("/root/sahaidachny"),
    fail_qa_count=0,  # No failures for basic test
    fail_quality_count=0,
    make_code_changes=True,
)

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
    task_id="add-string-utils",
    task_path=Path("docs/tasks/add-string-utils"),
    max_iterations=5,
    enabled_tools=["ruff", "pytest"],
)

# Execute the loop
try:
    state = orchestrator.run(config)

    print(f"STATUS: {state.current_phase.value}")
    print(f"ITERATIONS: {state.current_iteration}")
    print(f"TASK_ID: {state.task_id}")
    print(f"CALL_COUNT: {len(runner.call_history)}")

    # Verify all phases were called
    agents_called = [call["agent_name"] for call in runner.call_history]
    print(f"AGENTS_CALLED: {agents_called}")

    if state.current_phase.value == "completed":
        print("SUCCESS: Loop completed successfully")
    else:
        print(f"INCOMPLETE: Loop ended at {state.current_phase.value}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
'''
        exit_code, output = run_python_in_container(bootstrapped_container, python_code)

        print(f"Test output:\\n{output}")

        assert exit_code == 0, f"E2E test failed with exit code {exit_code}: {output}"
        assert "STATUS: completed" in output, f"Loop did not complete: {output}"
        assert "SUCCESS:" in output, f"Loop did not succeed: {output}"
        assert "execution-implementer" in output, "Implementation agent not called"
        assert "execution-qa" in output, "QA agent not called"

    def test_loop_with_qa_failure_recovery(self, bootstrapped_container):
        """Test that the loop handles QA failures and retries correctly."""
        all_files = {**SAMPLE_TASK_FILES, **SAMPLE_PROJECT_FILES}
        tarball = create_project_tarball(all_files)
        copy_to_container(bootstrapped_container, tarball)

        python_code = '''
import sys
from pathlib import Path

sys.path.insert(0, "/root/sahaidachny")

from saha.config.settings import Settings
from saha.runners import IntelligentMockRunner
from saha.tools import create_default_registry
from saha.hooks import HookRegistry
from saha.orchestrator.state import StateManager
from saha.orchestrator.loop import AgenticLoop, LoopConfig

settings = Settings(runner="mock", agents_path=Path("claude_plugin/agents"))

# Configure runner to fail QA twice before passing
runner = IntelligentMockRunner(
    working_dir=Path("/root/sahaidachny"),
    fail_qa_count=2,  # Fail QA twice, then pass
    fail_quality_count=0,
    make_code_changes=True,
)

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
    task_id="qa-retry-task",
    task_path=Path("docs/tasks/add-string-utils"),
    max_iterations=5,
    enabled_tools=[],
)

state = orchestrator.run(config)

print(f"STATUS: {state.current_phase.value}")
print(f"ITERATIONS: {state.current_iteration}")

# Count QA calls
qa_calls = sum(1 for call in runner.call_history if "qa" in call["agent_name"])
impl_calls = sum(1 for call in runner.call_history if "implementer" in call["agent_name"])

print(f"QA_CALLS: {qa_calls}")
print(f"IMPL_CALLS: {impl_calls}")

# Should have at least 3 iterations due to 2 QA failures
assert state.current_iteration >= 3, f"Expected at least 3 iterations, got {state.current_iteration}"
assert qa_calls >= 3, f"Expected at least 3 QA calls, got {qa_calls}"
print("SUCCESS: QA failure recovery works")
'''
        exit_code, output = run_python_in_container(bootstrapped_container, python_code)

        print(f"Test output:\\n{output}")

        assert exit_code == 0, f"QA retry test failed: {output}"
        assert "SUCCESS: QA failure recovery works" in output

    def test_loop_with_code_quality_failure(self, bootstrapped_container):
        """Test that code quality failures trigger fix loops."""
        all_files = {**SAMPLE_TASK_FILES, **SAMPLE_PROJECT_FILES}
        tarball = create_project_tarball(all_files)
        copy_to_container(bootstrapped_container, tarball)

        python_code = '''
import sys
from pathlib import Path

sys.path.insert(0, "/root/sahaidachny")

from saha.config.settings import Settings
from saha.runners import IntelligentMockRunner
from saha.tools import create_default_registry
from saha.hooks import HookRegistry
from saha.orchestrator.state import StateManager
from saha.orchestrator.loop import AgenticLoop, LoopConfig

settings = Settings(runner="mock", agents_path=Path("claude_plugin/agents"))

runner = IntelligentMockRunner(
    working_dir=Path("/root/sahaidachny"),
    fail_qa_count=0,
    fail_quality_count=1,  # Fail code quality once
    make_code_changes=True,
)

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
    task_id="quality-retry-task",
    task_path=Path("docs/tasks/add-string-utils"),
    max_iterations=5,
    enabled_tools=[],
)

state = orchestrator.run(config)

print(f"STATUS: {state.current_phase.value}")
print(f"ITERATIONS: {state.current_iteration}")

quality_calls = sum(1 for call in runner.call_history if "code-quality" in call["agent_name"])
print(f"QUALITY_CALLS: {quality_calls}")

assert state.current_iteration >= 2, "Should have at least 2 iterations due to quality failure"
print("SUCCESS: Code quality failure recovery works")
'''
        exit_code, output = run_python_in_container(bootstrapped_container, python_code)

        print(f"Test output:\\n{output}")

        assert exit_code == 0, f"Code quality test failed: {output}"
        assert "SUCCESS: Code quality failure recovery works" in output

    def test_state_persistence_across_runs(self, bootstrapped_container):
        """Test that execution state is properly persisted and can be loaded."""
        all_files = {**SAMPLE_TASK_FILES, **SAMPLE_PROJECT_FILES}
        tarball = create_project_tarball(all_files)
        copy_to_container(bootstrapped_container, tarball)

        # First: Create and save state
        python_code_save = '''
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, "/root/sahaidachny")

from saha.orchestrator.state import StateManager
from saha.models.state import LoopPhase

manager = StateManager(Path(".sahaidachny"))
state = manager.create(
    task_id="persistence-test",
    task_path=Path("docs/tasks/add-string-utils"),
    max_iterations=10,
    enabled_tools=["ruff", "pytest"],
)

# Modify state
state.current_phase = LoopPhase.QA
state.current_iteration = 3
state.context["fix_info"] = "Test fix info"
manager.save(state)

print(f"SAVED_TASK: {state.task_id}")
print(f"SAVED_PHASE: {state.current_phase.value}")
print(f"SAVED_ITERATION: {state.current_iteration}")
'''
        exit_code, output = run_python_in_container(bootstrapped_container, python_code_save)
        assert exit_code == 0, f"State save failed: {output}"
        assert "SAVED_TASK: persistence-test" in output

        # Second: Load state in new process
        python_code_load = '''
import sys
from pathlib import Path

sys.path.insert(0, "/root/sahaidachny")

from saha.orchestrator.state import StateManager

manager = StateManager(Path(".sahaidachny"))
state = manager.load("persistence-test")

print(f"LOADED_TASK: {state.task_id}")
print(f"LOADED_PHASE: {state.current_phase.value}")
print(f"LOADED_ITERATION: {state.current_iteration}")
print(f"LOADED_FIX_INFO: {state.context.get('fix_info', 'None')}")

assert state.task_id == "persistence-test"
assert state.current_phase.value == "qa"
assert state.current_iteration == 3
assert state.context.get("fix_info") == "Test fix info"

print("SUCCESS: State persistence works correctly")
'''
        exit_code, output = run_python_in_container(bootstrapped_container, python_code_load)

        print(f"Test output:\\n{output}")

        assert exit_code == 0, f"State load failed: {output}"
        assert "SUCCESS: State persistence works correctly" in output

    def test_all_agents_receive_correct_context(self, bootstrapped_container):
        """Test that each agent receives the appropriate context variables."""
        all_files = {**SAMPLE_TASK_FILES, **SAMPLE_PROJECT_FILES}
        tarball = create_project_tarball(all_files)
        copy_to_container(bootstrapped_container, tarball)

        python_code = '''
import sys
from pathlib import Path

sys.path.insert(0, "/root/sahaidachny")

from saha.config.settings import Settings
from saha.runners import IntelligentMockRunner
from saha.tools import create_default_registry
from saha.hooks import HookRegistry
from saha.orchestrator.state import StateManager
from saha.orchestrator.loop import AgenticLoop, LoopConfig

settings = Settings(runner="mock", agents_path=Path("claude_plugin/agents"))

runner = IntelligentMockRunner(
    working_dir=Path("/root/sahaidachny"),
    fail_qa_count=0,
    fail_quality_count=0,
    make_code_changes=False,  # Don't make actual changes for this test
)

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
    task_id="context-test",
    task_path=Path("docs/tasks/add-string-utils"),
    max_iterations=2,
    enabled_tools=["ruff"],
)

state = orchestrator.run(config)

# Analyze call history to verify context
errors = []

for call in runner.call_history:
    agent = call["agent_name"]
    context = call.get("context", {})

    # All agents should have task_id and task_path
    if "task_id" not in context:
        errors.append(f"{agent}: missing task_id")
    if "task_path" not in context:
        errors.append(f"{agent}: missing task_path")

    # Implementation should have iteration
    if "implementer" in agent and "iteration" not in context:
        errors.append(f"{agent}: missing iteration")

    # QA should have playwright_enabled
    if "qa" in agent and "playwright_enabled" not in context:
        errors.append(f"{agent}: missing playwright_enabled")

    # Code quality should have files_changed
    if "code-quality" in agent and "files_changed" not in context:
        errors.append(f"{agent}: missing files_changed")

if errors:
    print(f"ERRORS: {errors}")
else:
    print("SUCCESS: All agents received correct context")
'''
        exit_code, output = run_python_in_container(bootstrapped_container, python_code)

        print(f"Test output:\\n{output}")

        assert exit_code == 0, f"Context test failed: {output}"
        assert "SUCCESS: All agents received correct context" in output

    def test_max_iterations_limit(self, bootstrapped_container):
        """Test that the loop respects max_iterations limit."""
        all_files = {**SAMPLE_TASK_FILES, **SAMPLE_PROJECT_FILES}
        tarball = create_project_tarball(all_files)
        copy_to_container(bootstrapped_container, tarball)

        python_code = '''
import sys
from pathlib import Path

sys.path.insert(0, "/root/sahaidachny")

from saha.config.settings import Settings
from saha.runners import IntelligentMockRunner
from saha.tools import create_default_registry
from saha.hooks import HookRegistry
from saha.orchestrator.state import StateManager
from saha.orchestrator.loop import AgenticLoop, LoopConfig

settings = Settings(runner="mock", agents_path=Path("claude_plugin/agents"))

# Always fail QA to force iteration loop
runner = IntelligentMockRunner(
    working_dir=Path("/root/sahaidachny"),
    fail_qa_count=100,  # Always fail
    fail_quality_count=0,
    make_code_changes=False,
)

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
    task_id="max-iter-test",
    task_path=Path("docs/tasks/add-string-utils"),
    max_iterations=MAX_ITER,
    enabled_tools=[],
)

state = orchestrator.run(config)

print(f"STATUS: {state.current_phase.value}")
print(f"ITERATIONS: {state.current_iteration}")
print(f"MAX_ALLOWED: {MAX_ITER}")

assert state.current_iteration == MAX_ITER, f"Expected {MAX_ITER} iterations"
assert state.current_phase.value != "completed", "Should not have completed"

print("SUCCESS: Max iterations limit respected")
'''
        exit_code, output = run_python_in_container(bootstrapped_container, python_code)

        print(f"Test output:\\n{output}")

        assert exit_code == 0, f"Max iterations test failed: {output}"
        assert "SUCCESS: Max iterations limit respected" in output


class TestAgenticLoopCLI:
    """Test the CLI commands for the agentic loop."""

    def test_run_command_dry_run(self, bootstrapped_container):
        """Test that saha run --dry-run works correctly."""
        all_files = {**SAMPLE_TASK_FILES, **SAMPLE_PROJECT_FILES}
        tarball = create_project_tarball(all_files)
        copy_to_container(bootstrapped_container, tarball)

        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && ./saha.sh run add-string-utils --dry-run",
        )

        print(f"CLI output:\\n{output}")

        assert exit_code == 0, f"Dry run failed: {output}"
        assert "DRY RUN" in output.upper() or "dry" in output.lower()

    def test_status_command(self, bootstrapped_container):
        """Test that saha status works correctly."""
        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && ./saha.sh status",
        )

        # Status command should work even with no tasks
        assert exit_code == 0, f"Status command failed: {output}"

    def test_tools_command(self, bootstrapped_container):
        """Test that saha tools lists available tools."""
        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && ./saha.sh tools",
        )

        print(f"Tools output:\\n{output}")

        assert exit_code == 0, f"Tools command failed: {output}"
        assert "ruff" in output.lower() or "tool" in output.lower()


class TestHookIntegration:
    """Test hook system integration in the agentic loop."""

    def test_hooks_triggered_during_loop(self, bootstrapped_container):
        """Test that hooks are triggered at appropriate points."""
        all_files = {**SAMPLE_TASK_FILES, **SAMPLE_PROJECT_FILES}
        tarball = create_project_tarball(all_files)
        copy_to_container(bootstrapped_container, tarball)

        python_code = '''
import sys
from pathlib import Path

sys.path.insert(0, "/root/sahaidachny")

from saha.config.settings import Settings
from saha.runners import IntelligentMockRunner
from saha.tools import create_default_registry
from saha.hooks import HookRegistry
from saha.hooks.base import Hook, HookEvent
from saha.orchestrator.state import StateManager
from saha.orchestrator.loop import AgenticLoop, LoopConfig

# Custom hook to track events
class TrackingHook(Hook):
    def __init__(self):
        self._events = []

    @property
    def name(self):
        return "tracking"

    @property
    def events(self):
        return []

    def execute(self, event, **kwargs):
        self._events.append(event.value if hasattr(event, "value") else str(event))

settings = Settings(runner="mock", agents_path=Path("claude_plugin/agents"))
runner = IntelligentMockRunner(
    working_dir=Path("/root/sahaidachny"),
    fail_qa_count=0,
    fail_quality_count=0,
    make_code_changes=False,
)

tools = create_default_registry()
hooks = HookRegistry()
tracker = TrackingHook()
hooks.register(tracker)

state_manager = StateManager(Path(".sahaidachny"))

orchestrator = AgenticLoop(
    runner=runner,
    tool_registry=tools,
    hook_registry=hooks,
    state_manager=state_manager,
    settings=settings,
)

config = LoopConfig(
    task_id="hook-test",
    task_path=Path("docs/tasks/add-string-utils"),
    max_iterations=2,
    enabled_tools=[],
)

state = orchestrator.run(config)

print(f"EVENTS: {tracker._events}")

# Verify key events were triggered
expected_events = ["loop_start", "iteration_start"]
found_all = all(any(exp in evt for evt in tracker._events) for exp in expected_events)

if found_all:
    print("SUCCESS: All expected hooks triggered")
else:
    print(f"MISSING: Expected {expected_events}, got {tracker._events}")
'''
        exit_code, output = run_python_in_container(bootstrapped_container, python_code)

        print(f"Test output:\\n{output}")

        assert exit_code == 0, f"Hook test failed: {output}"
        assert "SUCCESS: All expected hooks triggered" in output
