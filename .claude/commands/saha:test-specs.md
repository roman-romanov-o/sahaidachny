---
description: Generate test specifications from user stories
argument-hint: [task-path] [--type=e2e|integration|unit]
allowed-tools: Read, Write, Glob, Grep, AskUserQuestion, Task
---

# Test Specifications

Generate test specifications before implementation.

## Arguments

- **task-path** (optional): Path to task folder
  - If not provided, auto-detects using:
    1. Current task from `.sahaidachny/current-task` (set via `saha use`)
    2. Most recent task folder in `docs/tasks/`
  - If no context found, asks the user
- `--type=<type>`: Focus on specific test type (e2e, integration, unit)

## Prerequisites

- User stories must exist with acceptance criteria
- Optionally: API contracts for integration tests

## Execution

### 1. Analyze Test Requirements

Read all user stories and extract:
- Acceptance criteria (Given/When/Then)
- Edge cases
- Error scenarios

From API contracts (if exist):
- Endpoint behaviors
- Error responses
- Data validation rules

### 2. Generate Test Specs by Type

#### E2E Tests (`test-specs/e2e/`)

Test complete user flows through the UI or API.

```markdown
# E2E Test Spec: [Flow Name]

**Related Stories:** US-XXX, US-YYY
**Priority:** Critical | High | Medium | Low
**Status:** Draft | Ready | Implemented

## Overview

[What user flow this tests]

## Preconditions

- [System state before test]
- [Required test data]
- [User authentication state]

## Test Cases

### TC-E2E-001: [Happy Path Name]

**Description:** [What this tests]

**Steps:**
1. [User action]
2. [Another action]
3. [...]

**Expected Results:**
- [Observable outcome]
- [System state change]
- [UI feedback]

**Test Data:**
```json
{
  "input": { ... },
  "expected": { ... }
}
```

---

### TC-E2E-002: [Error Scenario]

**Description:** [What error case this tests]

**Steps:**
1. [Action that triggers error]

**Expected Results:**
- [Error message shown]
- [System remains in valid state]

## Cleanup

- [How to reset state after tests]
```

#### Integration Tests (`test-specs/integration/`)

Test component interactions and API behavior.

```markdown
# Integration Test Spec: [Component/API Name]

**Related:** US-XXX, [api-contract.md]
**Priority:** Critical | High | Medium | Low
**Status:** Draft | Ready | Implemented

## Overview

[What integration this tests]

## Dependencies

- [Database/service this needs]
- [Mock requirements]

## Test Cases

### TC-INT-001: [Scenario Name]

**Description:** [What this tests]

**Setup:**
```python
# Fixture or setup code
```

**Input:**
```json
{ ... }
```

**Expected Output:**
```json
{ ... }
```

**Assertions:**
- [Specific assertion]
- [Database state check]
- [Side effect verification]

---

### TC-INT-002: [Error Handling]

**Description:** [Error case]

**Input:**
```json
{ "invalid": "data" }
```

**Expected:**
- Status: 400
- Error code: VALIDATION_ERROR

## Data Fixtures

```python
@pytest.fixture
def sample_data():
    return { ... }
```
```

#### Unit Tests (`test-specs/unit/`)

Test isolated functions and classes.

```markdown
# Unit Test Spec: [Module/Function Name]

**File:** `src/path/to/module.py`
**Priority:** High | Medium | Low
**Status:** Draft | Ready | Implemented

## Overview

[What logic this tests]

## Test Cases

### TC-UNIT-001: [Function] - [Scenario]

**Input:** `function_name(arg1, arg2)`

**Expected:** `expected_result`

**Notes:** [Edge case or reason for test]

---

### TC-UNIT-002: [Function] - [Edge Case]

**Input:** `function_name(None, "")`

**Expected:** Raises `ValueError`

## Parameterized Cases

| Input | Expected | Description |
|-------|----------|-------------|
| (1, 2) | 3 | Normal case |
| (0, 0) | 0 | Zero case |
| (-1, 1) | 0 | Negative case |

## Mocks Required

- `mock_external_service` - [Why mocked]
```

### 3. Map Stories to Tests

Create coverage matrix:

```markdown
# Test Coverage Matrix

| Story | E2E | Integration | Unit |
|-------|-----|-------------|------|
| US-001 | TC-E2E-001, TC-E2E-002 | TC-INT-001 | TC-UNIT-001 |
| US-002 | TC-E2E-003 | TC-INT-002, TC-INT-003 | - |
```

### 4. Update Test Specs README

Update `{task_path}/test-specs/README.md`:

```markdown
# Test Specifications

Test specs organized by type.

## Coverage Summary

| Type | Specs | Test Cases | Stories Covered |
|------|-------|------------|-----------------|
| E2E | 2 | 8 | US-001, US-002 |
| Integration | 3 | 12 | US-001, US-002, US-003 |
| Unit | 5 | 20 | US-001, US-003 |

## Contents

### E2E Tests
- [user-authentication-flow.md](e2e/user-authentication-flow.md)

### Integration Tests
- [auth-api.md](integration/auth-api.md)

### Unit Tests
- [token-validator.md](unit/token-validator.md)
```

### 5. Update Subdirectory READMEs

Update each type's README with its specific test specs.

## Test Spec Guidelines

Good test specs:
- [ ] Map directly to acceptance criteria
- [ ] Cover happy path AND error cases
- [ ] Include specific test data
- [ ] Define clear expected results
- [ ] Are implementable without ambiguity
- [ ] Don't duplicate coverage unnecessarily

## 6. Review Artifacts

Launch the reviewer agent to validate test specifications:

```
Task tool:
  subagent_type: general-purpose
  prompt: |
    You are the Sahaidachny Reviewer. Read your instructions from:
    .claude/agents/planning_reviewer.md

    Review mode: test-specs
    Task path: {task_path}
    Artifacts to review: {task_path}/test-specs/**/*.md (exclude READMEs)

    Review the test specifications and report any issues.
```

If the reviewer finds blockers (🔴), fix before proceeding.

## Example Usage

```
/saha:test-specs docs/tasks/task-01-auth
/saha:test-specs --type=e2e
```
