"""Intelligent mock runner for testing the agentic loop.

This runner simulates LLM behavior by actually reading task artifacts
and making decisions based on their content. It's useful for:
- Integration testing without real LLM calls
- Testing the orchestration logic
- Validating the full agentic loop flow
"""

import logging
import re
import subprocess
from pathlib import Path
from typing import Any

from saha.runners.base import Runner, RunnerResult

logger = logging.getLogger(__name__)


class IntelligentMockRunner(Runner):
    """A mock runner that simulates realistic agent behavior.

    Unlike the simple MockRunner, this runner actually:
    - Reads task artifacts to understand the task
    - Makes decisions based on file content
    - Produces structured outputs that drive the loop correctly
    - Can optionally make actual code changes for implementation testing
    """

    def __init__(
        self,
        working_dir: Path | None = None,
        fail_qa_count: int = 0,
        fail_quality_count: int = 0,
        make_code_changes: bool = True,
    ):
        """Initialize the intelligent mock runner.

        Args:
            working_dir: Working directory for file operations.
            fail_qa_count: Number of QA failures to simulate before passing.
            fail_quality_count: Number of quality failures before passing.
            make_code_changes: Whether to actually write code during implementation.
        """
        self._working_dir = working_dir or Path.cwd()
        self._fail_qa_count = fail_qa_count
        self._fail_quality_count = fail_quality_count
        self._make_code_changes = make_code_changes
        self._qa_calls = 0
        self._quality_calls = 0
        self._implementation_calls = 0
        self._call_history: list[dict[str, Any]] = []

    def run_agent(
        self,
        agent_spec_path: Path,
        prompt: str,
        context: dict[str, Any] | None = None,
        timeout: int = 300,
    ) -> RunnerResult:
        """Run an agent simulation based on the agent type."""
        agent_name = agent_spec_path.stem.replace("_", "-")
        context = context or {}

        self._call_history.append({
            "agent_name": agent_name,
            "prompt": prompt,
            "context": context,
        })

        logger.info(f"IntelligentMockRunner: Simulating agent {agent_name}")

        if "implementer" in agent_name:
            return self._run_implementation(context)
        elif "qa" in agent_name:
            return self._run_qa(context)
        elif "code-quality" in agent_name or "code_quality" in agent_name:
            return self._run_code_quality(context)
        elif "manager" in agent_name:
            return self._run_manager(context)
        elif "dod" in agent_name:
            return self._run_dod(context)
        else:
            return RunnerResult.success_result(
                f"Mock response for unknown agent: {agent_name}",
                structured_output={"status": "success"},
            )

    def run_prompt(
        self,
        prompt: str,
        system_prompt: str | None = None,
        timeout: int = 300,
    ) -> RunnerResult:
        """Run a simple prompt."""
        self._call_history.append({
            "type": "prompt",
            "prompt": prompt,
            "system_prompt": system_prompt,
        })
        return RunnerResult.success_result("Mock prompt response")

    def is_available(self) -> bool:
        """Always available."""
        return True

    def get_name(self) -> str:
        """Get runner name."""
        return "intelligent-mock"

    @property
    def call_history(self) -> list[dict[str, Any]]:
        """Get call history for assertions."""
        return self._call_history

    def _run_implementation(self, context: dict[str, Any]) -> RunnerResult:
        """Simulate implementation agent behavior."""
        self._implementation_calls += 1
        task_path = Path(context.get("task_path", "."))
        fix_info = context.get("fix_info")

        logger.info(f"Implementation agent: iteration {self._implementation_calls}")
        if fix_info:
            logger.info(f"Fix info received: {fix_info[:100]}...")

        files_changed = []
        files_added = []

        if self._make_code_changes:
            files_changed, files_added = self._make_actual_changes(task_path, fix_info)

        return RunnerResult.success_result(
            output="Implementation complete. Code changes made.",
            structured_output={
                "status": "success",
                "files_changed": files_changed,
                "files_added": files_added,
                "summary": f"Implementation iteration {self._implementation_calls}",
                "notes": "Mock implementation",
            },
        )

    def _run_qa(self, context: dict[str, Any]) -> RunnerResult:
        """Simulate QA agent behavior."""
        self._qa_calls += 1
        task_path = Path(context.get("task_path", "."))

        logger.info(f"QA agent: call {self._qa_calls}, fail_count={self._fail_qa_count}")

        # Simulate failures if configured
        if self._qa_calls <= self._fail_qa_count:
            return RunnerResult.success_result(
                output="QA verification failed - issues found",
                structured_output={
                    "dod_achieved": False,
                    "fix_info": f"QA failure #{self._qa_calls}: Tests need to pass. "
                    "Please ensure all acceptance criteria are met.",
                    "checks": [
                        {"criterion": "Tests pass", "passed": False, "details": "Some tests failing"},
                    ],
                },
            )

        # Run actual tests if possible
        test_result = self._run_tests(task_path)

        return RunnerResult.success_result(
            output="QA verification passed - all criteria met",
            structured_output={
                "dod_achieved": True,
                "checks": [
                    {"criterion": "Acceptance criteria met", "passed": True, "details": "All criteria satisfied"},
                    {"criterion": "Tests pass", "passed": test_result, "details": "Test suite executed"},
                ],
            },
        )

    def _run_code_quality(self, context: dict[str, Any]) -> RunnerResult:
        """Simulate code quality agent behavior."""
        self._quality_calls += 1
        task_path = Path(context.get("task_path", "."))
        files_changed = context.get("files_changed", [])

        logger.info(f"Code quality agent: call {self._quality_calls}")

        # Simulate failures if configured
        if self._quality_calls <= self._fail_quality_count:
            return RunnerResult.success_result(
                output="Code quality check failed",
                structured_output={
                    "quality_passed": False,
                    "fix_info": f"Quality failure #{self._quality_calls}: "
                    "Please fix linting issues and add type hints.",
                    "issues": [
                        {"file": "example.py", "line": 10, "message": "Missing type hint"},
                    ],
                    "blocking_issues_count": 1,
                },
            )

        # Run actual linters if available
        self._run_ruff(task_path, files_changed)

        return RunnerResult.success_result(
            output="Code quality check passed",
            structured_output={
                "quality_passed": True,
                "files_analyzed": files_changed,
                "issues": [],
                "blocking_issues_count": 0,
                "ignored_issues_count": 0,
            },
        )

    def _run_manager(self, context: dict[str, Any]) -> RunnerResult:
        """Simulate manager agent behavior."""
        task_path = Path(context.get("task_path", "."))
        iteration = context.get("iteration", 1)

        logger.info(f"Manager agent: updating task status for iteration {iteration}")

        # Update user story status files if they exist
        self._update_task_status(task_path)

        return RunnerResult.success_result(
            output="Task status updated successfully",
            structured_output={
                "status": "success",
                "updates_made": ["user-stories", "implementation-plan"],
            },
        )

    def _run_dod(self, context: dict[str, Any]) -> RunnerResult:
        """Simulate DoD agent behavior."""
        task_path = Path(context.get("task_path", "."))
        iterations = context.get("iterations_completed", 1)

        logger.info(f"DoD agent: checking completion after {iterations} iterations")

        # Check if task is complete by reading artifacts
        complete = self._check_task_complete(task_path)

        return RunnerResult.success_result(
            output="Task completion check finished",
            structured_output={
                "task_complete": complete,
                "confidence": "high",
                "summary": {
                    "user_stories_total": 1,
                    "user_stories_done": 1 if complete else 0,
                    "phases_total": 1,
                    "phases_done": 1 if complete else 0,
                },
                "reasoning": "All requirements met" if complete else "Work remaining",
                "remaining_items": [] if complete else ["Implementation needed"],
            },
        )

    def _make_actual_changes(
        self, task_path: Path, fix_info: str | None
    ) -> tuple[list[str], list[str]]:
        """Make actual code changes based on task artifacts.

        Returns:
            Tuple of (files_changed, files_added).
        """
        files_changed = []
        files_added = []

        # Read task description to understand what to implement
        task_desc_path = self._working_dir / task_path / "task-description.md"
        if not task_desc_path.exists():
            logger.warning(f"Task description not found: {task_desc_path}")
            return files_changed, files_added

        task_content = task_desc_path.read_text()

        # Look for target file patterns in task description
        target_file = self._extract_target_file(task_content)
        if not target_file:
            logger.info("No target file found in task description")
            return files_changed, files_added

        target_path = self._working_dir / target_file
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate code based on task
        code = self._generate_code(task_content, fix_info)

        if target_path.exists():
            # Append to existing file
            existing = target_path.read_text()
            target_path.write_text(existing + "\n\n" + code)
            files_changed.append(str(target_file))
        else:
            # Create new file
            target_path.write_text(code)
            files_added.append(str(target_file))

        logger.info(f"Code changes made: changed={files_changed}, added={files_added}")
        return files_changed, files_added

    def _extract_target_file(self, task_content: str) -> str | None:
        """Extract target file path from task description."""
        # Look for patterns like "in file.py" or "to module.py"
        patterns = [
            r"(?:in|to|file|module)\s+[`'\"]?([a-zA-Z0-9_/]+\.py)[`'\"]?",
            r"[`'\"]([a-zA-Z0-9_/]+\.py)[`'\"]",
        ]
        for pattern in patterns:
            match = re.search(pattern, task_content, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _generate_code(self, task_content: str, fix_info: str | None) -> str:
        """Generate code based on task description."""
        # Extract function names from task
        func_names = re.findall(r"(?:function|def)\s+(\w+)", task_content, re.IGNORECASE)
        if not func_names:
            func_names = re.findall(r"`(\w+)\(`", task_content)

        if not func_names:
            func_names = ["example_function"]

        code_parts = ['"""Generated code for task implementation."""\n']

        for func_name in func_names:
            code_parts.append(f"""
def {func_name}(value: str) -> str:
    \"\"\"Process the input value.\"\"\"
    return value
""")

        return "\n".join(code_parts)

    def _run_tests(self, task_path: Path) -> bool:
        """Run pytest if available."""
        test_dir = self._working_dir / task_path / "tests"
        if not test_dir.exists():
            test_dir = self._working_dir / "tests"

        if not test_dir.exists():
            return True  # No tests to run

        try:
            result = subprocess.run(
                ["pytest", str(test_dir), "-q", "--tb=no"],
                capture_output=True,
                timeout=60,
                cwd=self._working_dir,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return True  # Assume pass if pytest not available

    def _run_ruff(self, task_path: Path, files: list[str]) -> bool:
        """Run ruff if available."""
        if not files:
            return True

        try:
            result = subprocess.run(
                ["ruff", "check"] + files,
                capture_output=True,
                timeout=30,
                cwd=self._working_dir,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return True  # Assume pass if ruff not available

    def _update_task_status(self, task_path: Path) -> None:
        """Update task status markers in user stories."""
        stories_dir = self._working_dir / task_path / "user-stories"
        if not stories_dir.exists():
            return

        for story_file in stories_dir.glob("*.md"):
            content = story_file.read_text()
            # Mark acceptance criteria as done
            updated = re.sub(r"\[ \]", "[x]", content)
            if updated != content:
                story_file.write_text(updated)
                logger.info(f"Updated status in {story_file}")

    def _check_task_complete(self, task_path: Path) -> bool:
        """Check if the task is complete based on artifacts."""
        stories_dir = self._working_dir / task_path / "user-stories"

        if not stories_dir.exists():
            # No user stories = assume complete after implementation
            return True

        # Check if all acceptance criteria are marked done
        for story_file in stories_dir.glob("*.md"):
            content = story_file.read_text()
            pending = content.count("[ ]")
            if pending > 0:
                return False

        return True
