---
description: Show planning progress dashboard for a task
argument-hint: [task-path]
allowed-tools: Read, Glob, Bash
---

# Task Status Dashboard

Display the current planning progress for a Sahaidachny task.

## Arguments

- **task-path** (optional): Path to task folder
  - If not provided, auto-detect from `docs/tasks/` (most recent)

## Execution

### 1. Find Task

If no path provided, resolve using this priority:
1. Read `.sahaidachny/current-task` for the active task ID, then find its folder in `docs/tasks/`
2. Fallback to the most recent task folder: `ls -td docs/tasks/task-*/ 2>/dev/null | head -1`
3. If no tasks exist, inform user to run `/saha:init` first.

### 2. Scan Artifacts

For each planning category, count and list artifacts:

| Category | Pattern | Required Files |
|----------|---------|----------------|
| Research | `research/*.md` (exclude README) | At least 1 |
| Task Description | `task-description.md` | 1 |
| User Stories | `user-stories/US-*.md` | At least 1 |
| Design Decisions | `design-decisions/DD-*.md` | 0+ (full mode) |
| API Contracts | `api-contracts/*.md` (exclude README) | 0+ (full mode) |
| Test Specs | `test-specs/**/*.md` (exclude READMEs) | At least 1 |
| Implementation Plan | `implementation-plan/phase-*.md` | At least 1 |

### 3. Determine Status

For each category:
- **Not Started**: No artifacts exist
- **In Progress**: Some artifacts exist but incomplete
- **Complete**: Required artifacts present and marked as complete

### 4. Display Dashboard

Output format:

```
╔══════════════════════════════════════════════════════════╗
║  TASK-XX: [Title]                                        ║
║  Mode: [Full/Minimal] | Created: YYYY-MM-DD              ║
╠══════════════════════════════════════════════════════════╣
║  Planning Progress                                       ║
╠══════════════════════════════════════════════════════════╣
║  [●] Research              3 reports     ✅ Complete     ║
║  [●] Task Description      1 file        ✅ Complete     ║
║  [○] User Stories          0 files       ⏳ Not Started  ║
║  [◐] Design Decisions      1 file        🔄 In Progress  ║
║  [○] API Contracts         0 files       ⏳ Not Started  ║
║  [○] Test Specs            0 files       ⏳ Not Started  ║
║  [○] Implementation Plan   0 files       ⏳ Not Started  ║
╠══════════════════════════════════════════════════════════╣
║  Overall: 28% Complete                                   ║
╠══════════════════════════════════════════════════════════╣
║  Next Step: /saha:stories                         ║
╚══════════════════════════════════════════════════════════╝
```

### 5. Suggest Next Step

Based on workflow order:
1. Research → `/saha:research`
2. Task Description → `/saha:task`
3. User Stories → `/saha:stories`
4. Design Decisions → `/saha:decide` (full mode only)
5. API Contracts → `/saha:contracts` (full mode only)
6. Test Specs → `/saha:test-specs`
7. Implementation Plan → `/saha:plan`

Suggest the first incomplete step.

## Example Output

```
/saha:status docs/tasks/task-01-auth
```
