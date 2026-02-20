# API Contract: Agent Output Formats

**Type:** JSON Schema
**Used By:** Execution agents (implementer, qa, code-quality, manager, dod)
**Status:** Existing (Documenting for compliance)

## Overview

Execution agents return structured JSON output that the orchestrator parses to make decisions (continue loop, retry with fix_info, mark complete, etc.). All agents must follow these contracts for the orchestrator to function correctly.

## Pydantic Models

All agent outputs should be validated using these Pydantic models for type safety:

```python
from pydantic import BaseModel, Field
from typing import Literal

class BaseAgentOutput(BaseModel):
    """Base output for all agents."""
    status: Literal["success", "partial", "blocked"]
    summary: str

class ImplementerOutput(BaseAgentOutput):
    """Output from execution-implementer agent."""
    files_changed: list[str] = Field(default_factory=list)
    files_added: list[str] = Field(default_factory=list)
    next_steps: str | None = None

class QACheck(BaseModel):
    """Single DoD criterion check."""
    criterion: str
    passed: bool
    details: str | None = None

class TestResults(BaseModel):
    """Pytest execution summary."""
    total: int
    passed: int
    failed: int

class QAOutput(BaseModel):
    """Output from execution-qa agent."""
    dod_achieved: bool
    checks: list[QACheck]
    test_results: TestResults | None = None
    fix_info: str | None = None

class QualityIssue(BaseModel):
    """Single code quality issue."""
    file: str
    line: int | None = None
    code: str
    message: str
    severity: Literal["error", "warning"]

class CodeQualityOutput(BaseModel):
    """Output from execution-code-quality agent."""
    quality_passed: bool
    issues: list[QualityIssue] = Field(default_factory=list)
    files_analyzed: list[str]
    blocking_issues_count: int
    ignored_issues_count: int
    fix_info: str | None = None

class ManagerOutput(BaseModel):
    """Output from execution-manager agent."""
    updated: bool
    artifacts_modified: list[str]
    summary: str

class TaskSummary(BaseModel):
    """Aggregate task completion stats."""
    user_stories_total: int
    user_stories_done: int
    phases_total: int
    phases_done: int

class DoDOutput(BaseModel):
    """Output from execution-dod agent."""
    task_complete: bool
    confidence: Literal["high", "medium", "low"]
    summary: TaskSummary
    remaining_items: list[str] = Field(default_factory=list)
    recommendation: str
```

**Usage:**
```python
# Parse and validate agent output
raw_json = runner_result.structured_output
implementer_output = ImplementerOutput.model_validate(raw_json)

# Type-safe access
for file in implementer_output.files_changed:
    print(f"Modified: {file}")
```

## Base Agent Output

All agents MUST return JSON in this format:

```json
{
  "status": "success|partial|blocked",
  "summary": "Brief description of what was done"
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| status | enum | Yes | success, partial (some work done), or blocked (can't proceed) |
| summary | string | Yes | Human-readable summary of agent's actions |

## Implementation Agent Output

**Agent:** `execution-implementer`
**Purpose:** Write code changes according to plan

```json
{
  "status": "success|partial|blocked",
  "summary": "Implemented string utility functions",
  "files_changed": ["src/utils.py"],
  "files_added": ["tests/test_utils.py"],
  "next_steps": "Run tests to verify implementation"
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| status | enum | Yes | success, partial, or blocked |
| summary | string | Yes | What was implemented |
| files_changed | string[] | Yes | Paths of modified files (relative to project root) |
| files_added | string[] | Yes | Paths of created files |
| next_steps | string | No | What to verify next |

### Example (Success)

```json
{
  "status": "success",
  "summary": "Implemented reverse_string and capitalize_words functions with type hints and docstrings",
  "files_changed": ["src/utils.py"],
  "files_added": ["tests/test_utils.py"],
  "next_steps": "Verify tests pass and type hints are correct"
}
```

### Example (Partial)

```json
{
  "status": "partial",
  "summary": "Implemented reverse_string but could not implement capitalize_words due to unclear requirements",
  "files_changed": ["src/utils.py"],
  "files_added": [],
  "next_steps": "Clarify capitalization rules for hyphenated words before continuing"
}
```

### Example (Blocked)

```json
{
  "status": "blocked",
  "summary": "Cannot proceed - missing dependency on database models",
  "files_changed": [],
  "files_added": [],
  "next_steps": "Complete Phase 1 (database setup) before implementing this feature"
}
```

## QA Agent Output

**Agent:** `execution-qa`
**Purpose:** Verify Definition of Done criteria

```json
{
  "dod_achieved": true|false,
  "checks": [
    {
      "criterion": "Tests pass",
      "passed": true,
      "details": "10/10 tests passed"
    }
  ],
  "test_results": {
    "total": 10,
    "passed": 10,
    "failed": 0
  },
  "fix_info": "If dod_achieved=false, what needs fixing"
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| dod_achieved | boolean | Yes | Whether all acceptance criteria are met |
| checks | array | Yes | List of criterion checks performed |
| checks[].criterion | string | Yes | What was checked |
| checks[].passed | boolean | Yes | Whether check passed |
| checks[].details | string | No | Additional context |
| test_results | object | No | Pytest execution summary |
| fix_info | string | Conditional | Required if dod_achieved=false. Specific guidance for fixes |

### Example (Success)

```json
{
  "dod_achieved": true,
  "checks": [
    {
      "criterion": "reverse_string function exists with type hints",
      "passed": true,
      "details": "Function found in src/utils.py with proper signature"
    },
    {
      "criterion": "All tests pass",
      "passed": true,
      "details": "pytest: 10 passed in 0.23s"
    }
  ],
  "test_results": {
    "total": 10,
    "passed": 10,
    "failed": 0
  }
}
```

### Example (Failure with fix_info)

```json
{
  "dod_achieved": false,
  "checks": [
    {
      "criterion": "All tests pass",
      "passed": false,
      "details": "2 tests failed: test_reverse_empty_string, test_capitalize_special_chars"
    }
  ],
  "test_results": {
    "total": 10,
    "passed": 8,
    "failed": 2
  },
  "fix_info": "Fix failing tests:\n1. reverse_string('') raises TypeError - should return ''\n2. capitalize_words('hello-world') returns 'Hello-world' - should be 'Hello-World'"
}
```

### Example (Cannot Run Tests)

```json
{
  "dod_achieved": false,
  "checks": [
    {
      "criterion": "Tests executable",
      "passed": false,
      "details": "pytest command failed with exit code 5 (no tests collected)"
    }
  ],
  "test_results": {
    "total": 0,
    "passed": 0,
    "failed": 0
  },
  "fix_info": "No test files found. Expected test file at tests/test_utils.py does not exist."
}
```

## Code Quality Agent Output

**Agent:** `execution-code-quality`
**Purpose:** Run code quality checks (ruff, ty, complexity)

```json
{
  "quality_passed": true|false,
  "issues": [
    {
      "file": "src/utils.py",
      "line": 42,
      "code": "F401",
      "message": "Unused import",
      "severity": "error|warning"
    }
  ],
  "files_analyzed": ["src/utils.py"],
  "blocking_issues_count": 0,
  "ignored_issues_count": 3,
  "fix_info": "If quality_passed=false, what to fix"
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| quality_passed | boolean | Yes | Whether all quality checks passed |
| issues | array | Yes | List of quality issues found (empty if passed) |
| issues[].file | string | Yes | File path with issue |
| issues[].line | number | No | Line number |
| issues[].code | string | Yes | Tool-specific error code (e.g., F401, E501) |
| issues[].message | string | Yes | Human-readable message |
| issues[].severity | enum | Yes | error or warning |
| files_analyzed | string[] | Yes | Files that were checked |
| blocking_issues_count | number | Yes | Count of errors that block merge |
| ignored_issues_count | number | Yes | Count of false positives filtered out |
| fix_info | string | Conditional | Required if quality_passed=false |

### Example (Failure)

```json
{
  "quality_passed": false,
  "issues": [
    {
      "file": "src/utils.py",
      "line": 15,
      "code": "ANN001",
      "message": "Missing type annotation for function parameter",
      "severity": "error"
    }
  ],
  "files_analyzed": ["src/utils.py", "tests/test_utils.py"],
  "blocking_issues_count": 1,
  "ignored_issues_count": 0,
  "fix_info": "Add type annotation to 'capitalize_words' parameter 's'"
}
```

## Manager Agent Output

**Agent:** `execution-manager`
**Purpose:** Update task artifacts after successful iteration

```json
{
  "updated": true,
  "artifacts_modified": [
    "user-stories/US-001.md",
    "README.md"
  ],
  "summary": "Marked US-001 acceptance criteria as complete"
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| updated | boolean | Yes | Whether artifacts were successfully updated |
| artifacts_modified | string[] | Yes | List of modified artifact files |
| summary | string | Yes | What was updated |

## DoD Agent Output

**Agent:** `execution-dod`
**Purpose:** Check if entire task is complete

```json
{
  "task_complete": true|false,
  "confidence": "high|medium|low",
  "summary": {
    "user_stories_total": 5,
    "user_stories_done": 5,
    "phases_total": 3,
    "phases_done": 3
  },
  "remaining_items": [],
  "recommendation": "Task complete - ready for delivery"
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| task_complete | boolean | Yes | Whether all work is done |
| confidence | enum | Yes | high, medium, or low confidence in assessment |
| summary | object | Yes | Aggregate completion stats |
| summary.user_stories_total | number | Yes | Total story count |
| summary.user_stories_done | number | Yes | Completed story count |
| summary.phases_total | number | Yes | Total phase count |
| summary.phases_done | number | Yes | Completed phase count |
| remaining_items | string[] | Yes | List of incomplete items (empty if task_complete=true) |
| recommendation | string | Yes | Next action recommendation |

### Example (Complete)

```json
{
  "task_complete": true,
  "confidence": "high",
  "summary": {
    "user_stories_total": 7,
    "user_stories_done": 7,
    "phases_total": 4,
    "phases_done": 4
  },
  "remaining_items": [],
  "recommendation": "All user stories complete. All tests passing. Code quality passed. Ready for production deployment."
}
```

### Example (Incomplete)

```json
{
  "task_complete": false,
  "confidence": "high",
  "summary": {
    "user_stories_total": 7,
    "user_stories_done": 5,
    "phases_total": 4,
    "phases_done": 3
  },
  "remaining_items": [
    "US-006: Graceful degradation - Status: In Progress",
    "US-007: Error messages - Status: Pending"
  ],
  "recommendation": "Continue with US-006. Phase 4 remaining."
}
```

## Parsing Contract

Runners MUST extract JSON from agent output even if:
- JSON is wrapped in markdown code blocks (```json ... ```)
- Output contains text before/after JSON
- JSON is indented or formatted

Parsing strategies:
1. Look for `{` and `}` boundaries
2. Extract content between code fence markers
3. Try parsing incrementally until valid JSON found
4. Fall back to regex patterns if needed

If no valid JSON found, return empty `structured_output` dict.

### Validation with Pydantic

After parsing, orchestrator should validate the output using the appropriate Pydantic model:

```python
from pydantic import ValidationError

# Parse JSON from runner output
runner_result = runner.run_agent(...)
if not runner_result.structured_output:
    # Handle missing output
    return

# Validate against expected schema
try:
    output = ImplementerOutput.model_validate(runner_result.structured_output)
    # Type-safe access to fields
    process_files(output.files_changed)
except ValidationError as e:
    # Handle schema mismatch
    logger.error(f"Invalid agent output: {e}")
```

Benefits:
- **Type safety**: Catch schema mismatches early
- **Autocomplete**: IDEs know field types
- **Documentation**: Schema is self-documenting
- **Validation**: Pydantic validates types and constraints

## Implementation Files

### Pydantic Models
- `saha/agents/contracts.py` - All Pydantic models defined in this document
  - `BaseAgentOutput`
  - `ImplementerOutput`
  - `QAOutput`, `QACheck`, `TestResults`
  - `CodeQualityOutput`, `QualityIssue`
  - `ManagerOutput`
  - `DoDOutput`, `TaskSummary`

### Agent Specifications
- `claude_plugin/agents/execution_implementer.md` - Implementation agent spec
- `claude_plugin/agents/execution_qa.md` - QA agent spec
- `claude_plugin/agents/execution_code_quality.md` - Code quality agent spec
- `claude_plugin/agents/execution_manager.md` - Manager agent spec
- `claude_plugin/agents/execution_dod.md` - DoD agent spec

## Related

- **Stories:** US-001 (Codex), US-002 (Gemini), US-005 (E2E tests)
- **Contracts:** [01-runner-interface.md](01-runner-interface.md)
- **Research:** [02-gemini-runner-analysis.md](../research/02-gemini-runner-analysis.md) - JSON parsing issues
