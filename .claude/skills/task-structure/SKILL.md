---
name: task-structure
description: |
  Use this skill when working with Sahaidachny task artifacts. Activated when:
  - Working with task planning documents
  - Reading/updating user stories, design decisions, implementation plans
  - Any task folder (task-XX/) operations
version: 0.1.0
---

# Sahaidachny Task Structure

Sahaidachny uses a hierarchical task structure for planning complex features before implementation.

## Task Folder Structure

```
task-XX-short-name/
├── README.md                    # Task status dashboard
├── task-description.md          # Architecture + technical overview
├── user-stories/
│   ├── US-001-feature-name.md   # Detailed requirements
│   └── ...
├── design-decisions/
│   ├── README.md                # Index of decisions
│   ├── DD-001-decision-name.md  # Architecture decisions
│   └── ...
├── api-contracts/
│   └── ...
├── implementation-plan/
│   ├── README.md                # Phase status tracking
│   ├── phase-01-name.md         # Execution phases with steps
│   └── ...
├── test-specs/
│   ├── e2e/                     # End-to-end test specs
│   ├── integration/             # Integration test specs
│   └── unit/                    # Unit test specs
└── research/
    └── ...
```

## Key Artifact Formats

### User Story (US-XXX-name.md)

```markdown
# US-XXX: [Title]

**Status:** Draft | Review | Approved | Done
**Priority:** Critical | High | Medium | Low

## User Story
As a [role], I want [feature] so that [benefit].

## Acceptance Criteria
- [ ] AC1: [Criterion]
- [ ] AC2: [Criterion]

## Edge Cases
- Edge case 1
```

### Implementation Phase (phase-XX-name.md)

```markdown
# Phase XX: [Name]

**Status:** Pending | In Progress | Completed

## Steps
### Step 1: [Name]
- [ ] Action item 1
- [ ] Action item 2

## Success Criteria
- [ ] Criterion 1
```

## Status Markers

| Marker | Meaning |
|--------|---------|
| `[ ]` | Pending / Not started |
| `[~]` | In progress |
| `[x]` | Completed |

## Naming Conventions

| Artifact | Pattern | Example |
|----------|---------|---------|
| Task folder | `task-XX-short-name/` | `task-05-user-auth/` |
| User Story | `US-XXX-short-name.md` | `US-001-login-form.md` |
| Design Decision | `DD-XXX-short-name.md` | `DD-001-jwt-vs-session.md` |
| Phase | `phase-XX-short-name.md` | `phase-01-setup.md` |
