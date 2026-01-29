"""Integration tests for hooks system in containers.

Tests hook registration, triggering, and notification hooks.
"""


from tests.integration.conftest import (
    run_python_in_container,
)


class TestHookSystem:
    """Test the hook registration and triggering system."""

    def test_hook_events_defined(self, bootstrapped_container):
        """Test that all hook events are defined."""
        python_code = '''
from saha.hooks.base import HookEvent

events = [e.value for e in HookEvent]
print(f"Events: {events}")

assert "loop_start" in events
assert "loop_complete" in events
assert "loop_failed" in events
assert "loop_error" in events
assert "iteration_start" in events
assert "iteration_complete" in events
assert "implementation_start" in events
assert "qa_start" in events
assert "qa_failed" in events
assert "quality_start" in events
assert "quality_failed" in events

print(f"Total events: {len(events)}")
print("All events defined!")
'''
        exit_code, output = run_python_in_container(bootstrapped_container, python_code)

        assert exit_code == 0, f"Hook events test failed: {output}"
        assert "All events defined!" in output

    def test_hook_registry_basics(self, bootstrapped_container):
        """Test hook registry registration and listing."""
        python_code = '''
from saha.hooks import HookRegistry
from saha.hooks.base import Hook, HookEvent

class TestHook1(Hook):
    @property
    def name(self):
        return "test1"
    def execute(self, event, **kwargs):
        pass

class TestHook2(Hook):
    @property
    def name(self):
        return "test2"
    @property
    def events(self):
        return [HookEvent.LOOP_COMPLETE]
    def execute(self, event, **kwargs):
        pass

registry = HookRegistry()
registry.register(TestHook1())
registry.register(TestHook2())

hooks = registry.list_hooks()
print(f"Registered hooks: {hooks}")
assert "test1" in hooks
assert "test2" in hooks
print("Hook registration works!")
'''
        exit_code, output = run_python_in_container(bootstrapped_container, python_code)

        assert exit_code == 0, f"Hook registry test failed: {output}"
        assert "Hook registration works!" in output

    def test_hook_filtering_by_event(self, bootstrapped_container):
        """Test that hooks are only triggered for their events."""
        python_code = '''
from saha.hooks import HookRegistry
from saha.hooks.base import Hook, HookEvent

class AllEventsHook(Hook):
    def __init__(self):
        self.calls = []
    @property
    def name(self):
        return "all_events"
    def execute(self, event, **kwargs):
        self.calls.append(event.value)

class OnlyCompleteHook(Hook):
    def __init__(self):
        self.calls = []
    @property
    def name(self):
        return "only_complete"
    @property
    def events(self):
        return [HookEvent.LOOP_COMPLETE]
    def execute(self, event, **kwargs):
        self.calls.append(event.value)

all_hook = AllEventsHook()
complete_hook = OnlyCompleteHook()

registry = HookRegistry()
registry.register(all_hook)
registry.register(complete_hook)

registry.trigger("loop_start")
registry.trigger("iteration_start")
registry.trigger("loop_complete")
registry.trigger("loop_failed")

print(f"All events hook calls: {all_hook.calls}")
print(f"Complete only hook calls: {complete_hook.calls}")

assert len(all_hook.calls) == 4
assert len(complete_hook.calls) == 1
assert complete_hook.calls[0] == "loop_complete"
print("Event filtering works!")
'''
        exit_code, output = run_python_in_container(bootstrapped_container, python_code)

        assert exit_code == 0, f"Hook filtering test failed: {output}"
        assert "Event filtering works!" in output


class TestLoggingHook:
    """Test the logging hook."""

    def test_logging_hook_logs_events(self, bootstrapped_container):
        """Test that logging hook logs events."""
        python_code = '''
import logging
from io import StringIO
from pathlib import Path
from datetime import datetime

from saha.hooks import HookRegistry
from saha.hooks.notification import LoggingHook
from saha.models.state import ExecutionState

log_capture = StringIO()
handler = logging.StreamHandler(log_capture)
handler.setLevel(logging.INFO)
logging.getLogger("saha.hooks.notification").addHandler(handler)
logging.getLogger("saha.hooks.notification").setLevel(logging.INFO)

hook = LoggingHook()
registry = HookRegistry()
registry.register(hook)

state = ExecutionState(
    task_id="test-task",
    task_path=Path("test"),
    started_at=datetime.now(),
)

registry.trigger("loop_start", state=state)
registry.trigger("iteration_start", state=state)
registry.trigger("loop_complete", state=state)

log_output = log_capture.getvalue()
print(f"Log output: {log_output}")

assert "test-task" in log_output or "loop_start" in log_output.lower()
print("Logging hook works!")
'''
        exit_code, output = run_python_in_container(bootstrapped_container, python_code)

        assert exit_code == 0, f"Logging hook test failed: {output}"
        assert "Logging hook works!" in output


class TestNtfyHook:
    """Test the ntfy notification hook."""

    def test_ntfy_hook_builds_notification(self, bootstrapped_container):
        """Test that ntfy hook builds correct notification content."""
        python_code = '''
from pathlib import Path
from datetime import datetime

from saha.hooks.notification import NtfyHook
from saha.hooks.base import HookEvent
from saha.models.state import ExecutionState

hook = NtfyHook(topic="test-topic", enabled=False)

state = ExecutionState(
    task_id="test-task",
    task_path=Path("test"),
    started_at=datetime.now(),
    current_iteration=3,
)

title, message, priority, tags = hook._build_notification(
    HookEvent.LOOP_COMPLETE, state, None
)
print(f"Complete - Title: {title}")
print(f"Complete - Priority: {priority}")
assert "test-task" in title

title, message, priority, tags = hook._build_notification(
    HookEvent.LOOP_FAILED, state, None
)
print(f"Failed - Title: {title}")
print(f"Failed - Priority: {priority}")
assert "test-task" in title
assert priority == "high"

title, message, priority, tags = hook._build_notification(
    HookEvent.LOOP_ERROR, state, "Test error message"
)
print(f"Error - Title: {title}")
print(f"Error - Priority: {priority}")
assert priority == "urgent"

print("Ntfy notification building works!")
'''
        exit_code, output = run_python_in_container(bootstrapped_container, python_code)

        assert exit_code == 0, f"Ntfy hook test failed: {output}"
        assert "Ntfy notification building works!" in output

    def test_ntfy_hook_events_filter(self, bootstrapped_container):
        """Test that ntfy hook only triggers on completion events."""
        python_code = '''
from saha.hooks.notification import NtfyHook
from saha.hooks.base import HookEvent

hook = NtfyHook(topic="test", enabled=False)
events = hook.events

print(f"Ntfy hook events: {[e.value for e in events]}")

assert HookEvent.LOOP_COMPLETE in events
assert HookEvent.LOOP_FAILED in events
assert HookEvent.LOOP_ERROR in events

assert HookEvent.ITERATION_START not in events
assert HookEvent.IMPLEMENTATION_START not in events
assert HookEvent.QA_START not in events

print("Ntfy event filtering correct!")
'''
        exit_code, output = run_python_in_container(bootstrapped_container, python_code)

        assert exit_code == 0, f"Ntfy events test failed: {output}"
        assert "Ntfy event filtering correct!" in output


class TestCustomHooks:
    """Test creating custom hooks."""

    def test_custom_hook_implementation(self, bootstrapped_container):
        """Test that custom hooks can be implemented."""
        python_code = '''
from pathlib import Path
from datetime import datetime
from typing import Any

from saha.hooks import HookRegistry
from saha.hooks.base import Hook, HookEvent
from saha.models.state import ExecutionState

class MetricsHook(Hook):
    def __init__(self):
        self.metrics = {
            "iterations": 0,
            "qa_failures": 0,
            "quality_failures": 0,
        }

    @property
    def name(self):
        return "metrics"

    @property
    def events(self):
        return [
            HookEvent.ITERATION_COMPLETE,
            HookEvent.QA_FAILED,
            HookEvent.QUALITY_FAILED,
        ]

    def execute(self, event: HookEvent, **kwargs: Any):
        if event == HookEvent.ITERATION_COMPLETE:
            self.metrics["iterations"] += 1
        elif event == HookEvent.QA_FAILED:
            self.metrics["qa_failures"] += 1
        elif event == HookEvent.QUALITY_FAILED:
            self.metrics["quality_failures"] += 1

metrics_hook = MetricsHook()
registry = HookRegistry()
registry.register(metrics_hook)

state = ExecutionState(
    task_id="test",
    task_path=Path("test"),
    started_at=datetime.now(),
)

registry.trigger("iteration_complete", state=state)
registry.trigger("iteration_complete", state=state)
registry.trigger("qa_failed", state=state)
registry.trigger("iteration_complete", state=state)
registry.trigger("quality_failed", state=state)

print(f"Metrics: {metrics_hook.metrics}")
assert metrics_hook.metrics["iterations"] == 3
assert metrics_hook.metrics["qa_failures"] == 1
assert metrics_hook.metrics["quality_failures"] == 1

print("Custom hook works!")
'''
        exit_code, output = run_python_in_container(bootstrapped_container, python_code)

        assert exit_code == 0, f"Custom hook test failed: {output}"
        assert "Custom hook works!" in output
