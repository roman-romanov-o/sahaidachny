---
description: Define code changes — interfaces, classes, and API modifications
argument-hint: [task-path]
allowed-tools: Read, Write, Glob, Grep, AskUserQuestion, Task, mcp__context7__resolve-library-id, mcp__context7__query-docs
---

# Code Changes

Define what needs to change in the codebase: new/modified classes, interfaces, APIs, Pydantic models, protocols, and module boundaries.

**This is where implementation details live.** User stories describe WHAT behavior changes; code-changes describe HOW the codebase changes to deliver that behavior.

## Arguments

- **task-path** (optional): Path to task folder
  - If not provided, auto-detects using:
    1. Current task from `.sahaidachny/current-task` (set via `saha use`)
    2. Most recent task folder in `docs/tasks/`
  - If no context found, asks the user

## Prerequisites

- Task folder must exist
- User stories and design decisions should be defined
- Only available in **full mode**

Check mode in `{task_path}/README.md`. If minimal mode, inform user this step is skipped.

## Execution

### 1. Identify What Changes

Review artifacts to find codebase changes needed:
- `{task_path}/user-stories/*.md` - Features to implement
- `{task_path}/design-decisions/*.md` - Architectural choices
- `{task_path}/research/*.md` - Existing code patterns and structures

Types of changes to document:
- **New classes/models** - Pydantic models, dataclasses, domain objects
- **Modified interfaces** - New methods on existing protocols/ABCs
- **New/modified API endpoints** - REST, GraphQL, gRPC changes
- **Event schemas** - New message types for queues/events
- **Module boundary changes** - New public functions, changed signatures
- **Configuration changes** - New settings, env vars, feature flags

### 2. Gather Context

For each change, determine:
- What existing code is affected? (file paths, classes)
- What's the current interface/signature?
- What fields/methods are added/modified/removed?
- What are the error cases?
- Are there breaking changes?

### 3. Create Code Change Files

Create `{task_path}/code-changes/{name}.md`:

```markdown
# Code Change: [Component/Feature Name]

**Scope:** New Class | Modified Interface | New Endpoint | Event Schema
**Status:** Draft | Review | Approved

## Overview

[What changes and why — link to user stories this serves]

## Affected Files

- `path/to/existing_file.py` - Modified: add new method
- `path/to/new_file.py` - New file

## Changes

### New: [ClassName] (Pydantic Model)

```python
class TaskResult(BaseModel):
    """Result of a task execution."""
    task_id: str
    status: Literal["success", "failure", "timeout"]
    output: str
    duration_seconds: float
    files_changed: list[str] = []
```

### Modified: [ExistingClass]

**Current signature:**
```python
def run(self, prompt: str) -> str: ...
```

**New signature:**
```python
def run(self, prompt: str, timeout: int = 300) -> TaskResult: ...
```

**Breaking change:** Yes — return type changed from `str` to `TaskResult`

### New Endpoint: POST /api/v1/tasks

**Request:**
```json
{
  "prompt": "string (required)",
  "timeout": "number (optional, default: 300)"
}
```

**Response (201):**
```json
{
  "task_id": "string",
  "status": "string"
}
```

**Errors:**

| Status | Code | Description |
|--------|------|-------------|
| 400 | VALIDATION_ERROR | Invalid request |
| 401 | UNAUTHORIZED | Missing auth |

## Data Models

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| task_id | str | Yes | UUID v4 |
| status | Literal | Yes | success/failure/timeout |

## Dependencies

- **Requires:** [Other code changes or external dependencies]
- **Enables:** [What this unblocks]

## Related

- **Stories:** US-XXX, US-YYY
- **Decisions:** DD-XXX
```

### 4. Update Code Changes README

Update `{task_path}/code-changes/README.md`:

```markdown
# Code Changes

Codebase modifications required for this task.

## Contents

| Name | Scope | Status | Stories |
|------|-------|--------|---------|
| [Component] | New Class | Draft | US-001 |
| [API Name] | Modified Endpoint | Draft | US-002 |

## Change Map

### New Code
- [component.md](component.md) - New domain model

### Modified Code
- [api-changes.md](api-changes.md) - Endpoint modifications

### Breaking Changes
- [None / list any breaking changes]
```

## Code Change Guidelines

Good code change specs:
- [ ] Clearly identify which files are affected
- [ ] Show current vs. new signatures for modifications
- [ ] Include complete field definitions with types
- [ ] Document all error cases for APIs
- [ ] Flag breaking changes explicitly
- [ ] Link back to the user stories they serve
- [ ] Match existing code patterns found in research

## 5. Review Artifacts

Launch the reviewer agent to validate code change specs:

```
Task tool:
  subagent_type: general-purpose
  prompt: |
    You are the Sahaidachny Reviewer. Read your instructions from:
    .claude/agents/planning_reviewer.md

    Review mode: contracts
    Task path: {task_path}
    Artifacts to review: {task_path}/code-changes/*.md (exclude README)

    Review the code change specifications and report any issues.
```

If the reviewer finds blockers (🔴), fix before proceeding.

## Example Usage

```
/saha:contracts docs/tasks/task-01-auth
/saha:contracts
```
