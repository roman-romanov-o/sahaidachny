"""Task verification checker for pre-execution readiness validation.

Performs fast, Python-based checks on task artifacts to ensure
the task is ready for execution. No AI calls needed.
"""

import re
from enum import Enum
from pathlib import Path

from pydantic import BaseModel


class VerificationStatus(str, Enum):
    """Overall verification result status."""

    PASSED = "passed"
    WARNINGS = "warnings"
    FAILED = "failed"


class CheckResult(BaseModel):
    """Result of a single verification check."""

    name: str
    passed: bool
    message: str
    is_warning: bool = False  # True = warning (can proceed), False = error (blocks execution)


class VerificationResult(BaseModel):
    """Complete verification result for a task."""

    task_id: str
    task_path: Path
    status: VerificationStatus
    checks: list[CheckResult]

    @property
    def errors(self) -> list[CheckResult]:
        """Get all failed checks that are errors (not warnings)."""
        return [c for c in self.checks if not c.passed and not c.is_warning]

    @property
    def warnings(self) -> list[CheckResult]:
        """Get all failed checks that are warnings."""
        return [c for c in self.checks if not c.passed and c.is_warning]

    @property
    def passed_checks(self) -> list[CheckResult]:
        """Get all passed checks."""
        return [c for c in self.checks if c.passed]

    def can_proceed(self) -> bool:
        """Check if execution can proceed (no errors, warnings are OK)."""
        return len(self.errors) == 0


class TaskVerifier:
    """Verifies task artifacts are complete and ready for execution."""

    def __init__(self, task_path: Path) -> None:
        self.task_path = task_path
        self.checks: list[CheckResult] = []

    def verify(self, task_id: str) -> VerificationResult:
        """Run all verification checks and return the result."""
        self.checks = []

        self._check_task_description()
        self._check_user_stories()
        self._check_test_specs()
        self._check_implementation_plan()
        self._check_design_decisions()
        self._check_story_phase_assignment()

        status = self._determine_status()

        return VerificationResult(
            task_id=task_id,
            task_path=self.task_path,
            status=status,
            checks=self.checks,
        )

    def _determine_status(self) -> VerificationStatus:
        """Determine overall status from individual check results."""
        has_errors = any(not c.passed and not c.is_warning for c in self.checks)
        has_warnings = any(not c.passed and c.is_warning for c in self.checks)

        if has_errors:
            return VerificationStatus.FAILED
        if has_warnings:
            return VerificationStatus.WARNINGS
        return VerificationStatus.PASSED

    def _check_task_description(self) -> None:
        """Check that task-description.md exists and has content."""
        desc_path = self.task_path / "task-description.md"

        if not desc_path.exists():
            self.checks.append(
                CheckResult(
                    name="task-description",
                    passed=False,
                    message="task-description.md not found",
                    is_warning=False,
                )
            )
            return

        content = desc_path.read_text()
        if len(content.strip()) < 50:
            self.checks.append(
                CheckResult(
                    name="task-description",
                    passed=False,
                    message="task-description.md seems too short (< 50 chars)",
                    is_warning=True,
                )
            )
            return

        self.checks.append(
            CheckResult(
                name="task-description",
                passed=True,
                message="task-description.md present",
            )
        )

    def _check_user_stories(self) -> None:
        """Check that at least one user story exists."""
        stories_dir = self.task_path / "user-stories"

        if not stories_dir.exists():
            self.checks.append(
                CheckResult(
                    name="user-stories",
                    passed=False,
                    message="user-stories/ directory not found",
                    is_warning=False,
                )
            )
            return

        stories = list(stories_dir.glob("*.md"))
        if not stories:
            self.checks.append(
                CheckResult(
                    name="user-stories",
                    passed=False,
                    message="No user story files found in user-stories/",
                    is_warning=False,
                )
            )
            return

        self.checks.append(
            CheckResult(
                name="user-stories",
                passed=True,
                message=f"{len(stories)} user story file(s) found",
            )
        )

    def _check_test_specs(self) -> None:
        """Check that at least one test spec exists."""
        specs_dir = self.task_path / "test-specs"

        if not specs_dir.exists():
            self.checks.append(
                CheckResult(
                    name="test-specs",
                    passed=False,
                    message="test-specs/ directory not found",
                    is_warning=False,
                )
            )
            return

        # Check for .md files in test-specs/ and subdirectories
        specs = list(specs_dir.rglob("*.md"))
        if not specs:
            self.checks.append(
                CheckResult(
                    name="test-specs",
                    passed=False,
                    message="No test spec files found in test-specs/",
                    is_warning=False,
                )
            )
            return

        self.checks.append(
            CheckResult(
                name="test-specs",
                passed=True,
                message=f"{len(specs)} test spec file(s) found",
            )
        )

    def _check_implementation_plan(self) -> None:
        """Check that at least one implementation phase exists."""
        plan_dir = self.task_path / "implementation-plan"

        if not plan_dir.exists():
            self.checks.append(
                CheckResult(
                    name="implementation-plan",
                    passed=False,
                    message="implementation-plan/ directory not found",
                    is_warning=False,
                )
            )
            return

        phases = list(plan_dir.glob("phase-*.md"))
        if not phases:
            self.checks.append(
                CheckResult(
                    name="implementation-plan",
                    passed=False,
                    message="No phase-*.md files found in implementation-plan/",
                    is_warning=False,
                )
            )
            return

        self.checks.append(
            CheckResult(
                name="implementation-plan",
                passed=True,
                message=f"{len(phases)} implementation phase(s) found",
            )
        )

    def _check_design_decisions(self) -> None:
        """Check for design decisions (warning only if missing)."""
        decisions_dir = self.task_path / "design-decisions"

        if not decisions_dir.exists():
            self.checks.append(
                CheckResult(
                    name="design-decisions",
                    passed=False,
                    message="design-decisions/ directory not found (optional)",
                    is_warning=True,
                )
            )
            return

        decisions = list(decisions_dir.glob("*.md"))
        if not decisions:
            self.checks.append(
                CheckResult(
                    name="design-decisions",
                    passed=False,
                    message="No design decision files found (optional)",
                    is_warning=True,
                )
            )
            return

        self.checks.append(
            CheckResult(
                name="design-decisions",
                passed=True,
                message=f"{len(decisions)} design decision(s) found",
            )
        )

    def _check_story_phase_assignment(self) -> None:
        """Check that user stories are assigned to phases."""
        stories_dir = self.task_path / "user-stories"
        plan_dir = self.task_path / "implementation-plan"

        if not stories_dir.exists() or not plan_dir.exists():
            return  # Skip if prerequisites missing

        stories = list(stories_dir.glob("*.md"))
        phases = list(plan_dir.glob("phase-*.md"))

        if not stories or not phases:
            return

        # Extract story IDs from filenames (e.g., US-001-login.md -> US-001)
        story_ids = set()
        for story in stories:
            match = re.match(r"(US-\d+)", story.stem)
            if match:
                story_ids.add(match.group(1))

        # Check if stories are referenced in phases
        referenced_stories = set()
        for phase in phases:
            content = phase.read_text()
            for sid in story_ids:
                if sid in content:
                    referenced_stories.add(sid)

        unassigned = story_ids - referenced_stories
        if unassigned:
            self.checks.append(
                CheckResult(
                    name="story-assignment",
                    passed=False,
                    message=f"Stories not assigned to phases: {', '.join(sorted(unassigned))}",
                    is_warning=True,
                )
            )
        else:
            self.checks.append(
                CheckResult(
                    name="story-assignment",
                    passed=True,
                    message="All stories assigned to phases",
                )
            )
