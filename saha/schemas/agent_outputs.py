"""Agent output schemas for validation.

These schemas define the expected JSON output from each execution agent.
Used by the orchestrator to validate agent responses.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ImplementationStatus(str, Enum):
    """Status codes for implementation agent."""

    SUCCESS = "success"
    PARTIAL = "partial"
    BLOCKED = "blocked"


class TDDPhases(BaseModel):
    """TDD progress tracking for implementation agent."""

    interfaces_created: list[str] | None = Field(
        default=None,
        description="Names of interfaces/models created (e.g., UserCreateRequest, UserResponse)"
    )
    tests_written: int | None = Field(
        default=None,
        description="Number of test cases written from test specs"
    )
    tests_passing: int | None = Field(
        default=None,
        description="Number of tests currently passing"
    )
    tests_failing: int | None = Field(
        default=None,
        description="Number of tests currently failing (expected in Red phase)"
    )


class ImplementationOutput(BaseModel):
    """Output schema for execution-implementer agent.

    Supports TDD workflow with optional tdd_phases tracking.
    """

    status: ImplementationStatus = Field(
        description="Overall implementation status"
    )
    summary: str = Field(
        description="Brief description of TDD work done (1-2 sentences)"
    )
    tdd_phases: TDDPhases | None = Field(
        default=None,
        description="TDD progress: interfaces created, tests written/passing"
    )
    notes: str | None = Field(
        default=None,
        description="Important observations, concerns, or decisions made"
    )
    next_steps: str | None = Field(
        default=None,
        description="What should be verified or implemented next"
    )


class QACheck(BaseModel):
    """Individual criterion check result."""

    criterion: str = Field(description="The acceptance criterion being checked")
    passed: bool = Field(description="Whether the criterion passed")
    details: str = Field(description="Details about the check")
    verification_method: str | None = Field(
        default=None,
        description="How the criterion was verified (pytest, playwright, manual)"
    )


class TestResults(BaseModel):
    """Test suite execution results."""

    total: int = Field(description="Total number of tests")
    passed: int = Field(description="Number of passing tests")
    failed: int = Field(description="Number of failing tests")
    skipped: int = Field(default=0, description="Number of skipped tests")


class QAOutput(BaseModel):
    """Output schema for execution-qa agent."""

    dod_achieved: bool = Field(
        description="True only if ALL criteria pass"
    )
    summary: str = Field(
        description="Brief status summary"
    )
    checks: list[QACheck] | None = Field(
        default=None,
        description="Individual criterion checks"
    )
    test_results: TestResults | None = Field(
        default=None,
        description="Test suite results"
    )
    fix_info: str | None = Field(
        default=None,
        description="Detailed fix instructions (required if dod_achieved: false)"
    )


class PlaywrightResults(BaseModel):
    """Playwright UI verification results."""

    pages_tested: int = Field(description="Number of pages tested")
    interactions_verified: int = Field(description="Number of interactions verified")
    screenshots_captured: int = Field(description="Number of screenshots taken")


class QAPlaywrightOutput(QAOutput):
    """Output schema for execution-qa-playwright agent."""

    playwright_results: PlaywrightResults | None = Field(
        default=None,
        description="Summary of Playwright verification"
    )


class ManagerStatus(str, Enum):
    """Status codes for manager agent."""

    SUCCESS = "success"
    PARTIAL = "partial"


class UpdateRecord(BaseModel):
    """Record of a file update."""

    file: str = Field(description="Path to the updated file")
    change: str = Field(description="Description of the change made")
    verified: bool = Field(
        default=False,
        description="Whether the update was verified by re-reading"
    )


class FailedUpdate(BaseModel):
    """Record of a failed file update."""

    file: str = Field(description="Path to the file that couldn't be updated")
    reason: str = Field(description="Why the update failed")
    attempted: str = Field(description="What change was attempted")


class ManagerOutput(BaseModel):
    """Output schema for execution-manager agent."""

    status: ManagerStatus = Field(
        description="Overall update status"
    )
    updates_made: list[UpdateRecord] = Field(
        description="List of successful updates with verification"
    )
    items_completed: list[str] = Field(
        description="What was marked as done"
    )
    items_remaining: list[str] = Field(
        description="What still needs to be done"
    )
    failed_updates: list[FailedUpdate] | None = Field(
        default=None,
        description="Updates that couldn't be made"
    )
    notes: str | None = Field(
        default=None,
        description="Observations about progress or issues"
    )


class DoDConfidence(str, Enum):
    """Confidence levels for DoD determination."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DoDSummary(BaseModel):
    """Summary counts for DoD verification."""

    user_stories_total: int | str = Field(
        description="Total number of user stories"
    )
    user_stories_done: int | str = Field(
        description="Number of completed user stories"
    )
    phases_total: int | str = Field(
        description="Total number of implementation phases"
    )
    phases_done: int | str = Field(
        description="Number of completed phases"
    )
    acceptance_criteria_total: int | str = Field(
        description="Total number of acceptance criteria"
    )
    acceptance_criteria_done: int | str = Field(
        description="Number of satisfied acceptance criteria"
    )


class ParsingIssue(BaseModel):
    """Issue encountered while parsing artifacts."""

    file: str = Field(description="Path to the problematic file")
    issue: str = Field(description="Description of the parsing issue")


class DoDOutput(BaseModel):
    """Output schema for execution-dod agent."""

    task_complete: bool = Field(
        description="True only if ALL work is done"
    )
    confidence: DoDConfidence = Field(
        description="How certain of the determination"
    )
    summary: DoDSummary = Field(
        description="Counts of stories, phases, criteria"
    )
    reasoning: str = Field(
        description="Clear explanation of decision"
    )
    remaining_items: list[str] | None = Field(
        default=None,
        description="What still needs to be done"
    )
    parsing_issues: list[ParsingIssue] | None = Field(
        default=None,
        description="Problems encountered reading artifacts"
    )
    recommendation: str | None = Field(
        default=None,
        description="Suggested next steps"
    )


class CodeQualityIssue(BaseModel):
    """Individual code quality issue."""

    file: str = Field(description="Path to the file with the issue")
    line: int = Field(description="Line number of the issue")
    tool: str = Field(description="Tool that found the issue (ruff, ty, complexipy)")
    code: str = Field(description="Issue code (e.g., E501, type-error)")
    message: str = Field(description="Description of the issue")
    severity: str = Field(description="Issue severity (error, warning)")
    is_blocking: bool = Field(description="Whether this issue blocks passage")


class IgnoredIssue(BaseModel):
    """Issue that was filtered/ignored."""

    file: str = Field(description="Path to the file")
    line: int = Field(description="Line number")
    tool: str = Field(description="Tool that found it")
    code: str = Field(description="Issue code")
    reason: str = Field(description="Why it was ignored")


class CodeQualityOutput(BaseModel):
    """Output schema for execution-code-quality agent."""

    quality_passed: bool = Field(
        description="True if no blocking issues"
    )
    files_analyzed: list[str] = Field(
        description="List of files that were checked"
    )
    summary: str = Field(
        description="Brief status summary"
    )
    issues: list[CodeQualityIssue] | None = Field(
        default=None,
        description="All issues found"
    )
    blocking_issues_count: int = Field(
        default=0,
        description="Count of issues that block passage"
    )
    ignored_issues_count: int = Field(
        default=0,
        description="Count of filtered/ignored issues"
    )
    ignored_issues: list[IgnoredIssue] | None = Field(
        default=None,
        description="Details of why issues were ignored"
    )
    tool_failures: list[str] | None = Field(
        default=None,
        description="Tools that couldn't run"
    )
    fix_info: str | None = Field(
        default=None,
        description="Detailed fix instructions (required if failed)"
    )


class TestQualityScore(str, Enum):
    """Test quality grades."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class TestCritiqueIssue(BaseModel):
    """Individual test quality issue."""

    severity: str = Field(description="Issue severity (critical, warning)")
    file: str = Field(description="Path to the test file")
    line: int = Field(description="Line number")
    test_name: str = Field(description="Name of the problematic test")
    pattern: str = Field(
        description="Pattern detected (over_mocking, mocking_sut, placeholder)"
    )
    description: str = Field(description="Description of the issue")
    mocks_count: int | None = Field(
        default=None,
        description="Number of mocks (for over_mocking pattern)"
    )


class TestCritiqueOutput(BaseModel):
    """Output schema for execution-test-critique agent."""

    critique_passed: bool = Field(
        description="True if score A/B/C, False if D/F"
    )
    test_quality_score: TestQualityScore = Field(
        description="Grade A through F"
    )
    tests_analyzed: int = Field(
        description="How many test functions analyzed"
    )
    summary: str = Field(
        description="Brief assessment"
    )
    confidence: str | None = Field(
        default=None,
        description="How certain of the analysis"
    )
    hollow_tests: int | None = Field(
        default=None,
        description="Count of problematic tests"
    )
    issues: list[TestCritiqueIssue] | None = Field(
        default=None,
        description="Specific problems found"
    )
    good_patterns: list[str] | None = Field(
        default=None,
        description="Positive patterns observed"
    )
    fix_info: str | None = Field(
        default=None,
        description="Detailed fix instructions (required if failed)"
    )


# Schema registry for validation
AGENT_OUTPUT_SCHEMAS: dict[str, type[BaseModel]] = {
    "execution-implementer": ImplementationOutput,
    "execution-qa": QAOutput,
    "execution-qa-playwright": QAPlaywrightOutput,
    "execution-manager": ManagerOutput,
    "execution-dod": DoDOutput,
    "execution-code-quality": CodeQualityOutput,
    "execution-test-critique": TestCritiqueOutput,
}


def validate_agent_output(agent_name: str, output: dict[str, Any]) -> BaseModel:
    """Validate agent output against its schema.

    Args:
        agent_name: Name of the agent (e.g., "execution-qa").
        output: The parsed JSON output from the agent.

    Returns:
        Validated Pydantic model instance.

    Raises:
        ValueError: If agent name is unknown.
        pydantic.ValidationError: If output doesn't match schema.
    """
    if agent_name not in AGENT_OUTPUT_SCHEMAS:
        raise ValueError(f"Unknown agent: {agent_name}")

    schema = AGENT_OUTPUT_SCHEMAS[agent_name]
    return schema.model_validate(output)


def get_required_fields(agent_name: str) -> list[str]:
    """Get the required fields for an agent's output schema.

    Args:
        agent_name: Name of the agent.

    Returns:
        List of required field names.
    """
    if agent_name not in AGENT_OUTPUT_SCHEMAS:
        raise ValueError(f"Unknown agent: {agent_name}")

    schema = AGENT_OUTPUT_SCHEMAS[agent_name]
    required = []
    for field_name, field_info in schema.model_fields.items():
        if field_info.is_required():
            required.append(field_name)
    return required
