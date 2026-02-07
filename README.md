<p align="center">
  <img src="assets/logo.png" alt="Sahaidachny" width="180">
</p>

<h1 align="center">Sahaidachny</h1>

<p align="center">
  <strong>Autonomous AI agent orchestrator for hierarchical task execution in Claude Code</strong>
</p>

<p align="center">
  <a href="#installation">Installation</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#how-it-works">How It Works</a> •
  <a href="#documentation">Documentation</a>
</p>

---

> Named after [Petro Sahaidachny](https://en.wikipedia.org/wiki/Petro_Konashevych-Sahaidachny), the legendary Ukrainian Cossack hetman known for strategic planning and decisive execution.

## What is Sahaidachny?

Sahaidachny solves a fundamental problem in AI-assisted coding: **how to reliably implement complex features that span multiple files, require architectural decisions, and need verification**.

It's a Claude Code plugin that enables:

- **Structured Planning** — Build hierarchical task specifications with user stories, design decisions, API contracts, and test specs
- **Autonomous Execution** — Run agentic loops across multiple context windows that implement, verify, and iterate
- **State Persistence** — Maintain learnings and progress between iterations, enabling resume after interruption

### Why Not Just Prompt Claude?

| Aspect | Simple Prompting | Sahaidachny |
|--------|------------------|-------------|
| Task structure | Single prompt | Hierarchical artifacts |
| Planning | Ad-hoc | Guided workflow |
| Implementation | One-shot | Iterative with feedback |
| Verification | Manual | Automated DoD checks |
| Code quality | Hope for the best | Ruff, ty, complexity checks |
| State | Lost on context switch | Persisted to disk |

## Installation

### Prerequisites

- Python 3.11+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and configured

### Install via pipx (Recommended)

```bash
pipx install sahaidachny
```

### Install via uv

```bash
uv tool install sahaidachny
```

### Verify Installation

```bash
saha version
saha tools
```

## Quick Start

### 1. Launch Claude Code with Sahaidachny

```bash
saha claude
```

### 2. Initialize a Task

```bash
# In Claude Code:
/saha:init user-authentication --mode=full
```

### 3. Plan the Task

```bash
/saha:research      # Explore codebase (for existing projects)
/saha:task          # Define what to build
/saha:stories       # Generate user stories
/saha:verify        # Approve artifacts
/saha:plan          # Create implementation phases
```

### 4. Execute Autonomously

```bash
# Back in terminal:
saha run task-01
```

### 5. Monitor Progress

```bash
saha status task-01 --verbose
```

## How It Works

Sahaidachny operates in two phases:

### Phase 1: Planning (Interactive)

You work with Claude Code using slash commands to create structured task artifacts:

```
/saha:init → /saha:research → /saha:task → /saha:stories → /saha:plan
```

This produces a task folder with:
```
task-01/
├── task-description.md       # What to build
├── user-stories/             # Requirements with acceptance criteria
├── design-decisions/         # Architecture decisions
├── implementation-plan/      # Phased execution steps
└── test-specs/               # Test specifications
```

### Phase 2: Execution (Autonomous)

The agentic loop runs without intervention:

```
┌─────────────────┐
│ Implementation  │ ← Write code according to plan
└────────┬────────┘
         ▼
┌─────────────────┐
│       QA        │ ← Verify acceptance criteria
└────────┬────────┘
         │
    DoD achieved? ──No──┐
         │              │
        Yes             │
         ▼              │
┌─────────────────┐     │
│  Code Quality   │     │
└────────┬────────┘     │
         │              │
   Quality passed? ─No──┤
         │              │
        Yes             │
         ▼              ▼
┌─────────────────┐  ┌──────────┐
│    Manager      │  │ fix_info │
└────────┬────────┘  └────┬─────┘
         ▼                │
┌─────────────────┐       │
│   DoD Check     │       │
└────────┬────────┘       │
         │                │
   Task complete? ──No────┘
         │
        Yes
         ▼
      DONE
```

Each iteration learns from previous failures via `fix_info`, enabling targeted fixes.

## Planning Commands

| Command | Purpose |
|---------|---------|
| `/saha:init` | Create task folder structure |
| `/saha:research` | Explore codebase patterns |
| `/saha:task` | Define task description |
| `/saha:stories` | Generate user stories |
| `/saha:decide` | Record design decisions |
| `/saha:contracts` | Define API contracts |
| `/saha:test-specs` | Write test specifications |
| `/saha:plan` | Create implementation phases |
| `/saha:verify` | Approve artifacts |
| `/saha:status` | Show planning progress |

## Execution Commands

| Command | Purpose |
|---------|---------|
| `saha run <task-id>` | Execute task autonomously |
| `saha resume <task-id>` | Resume interrupted execution |
| `saha status [task-id]` | Check execution status |
| `saha tools` | List available quality tools |
| `saha clean [task-id]` | Remove execution state |
| `saha claude` | Launch Claude Code with plugin |

## Code Quality Tools

The execution loop integrates with:

- **[Ruff](https://github.com/astral-sh/ruff)** — Fast Python linter
- **[ty](https://github.com/astral-sh/ty)** — Fast Python type checker
- **[complexipy](https://github.com/rohaquinern/complexipy)** — Cognitive complexity analyzer
- **[pytest](https://pytest.org)** — Test runner

## Configuration

Configure via environment variables (prefix: `SAHA_`) or `.env` file:

```bash
SAHA_MAX_ITERATIONS=15
SAHA_RUNNER=claude
SAHA_TOOL_COMPLEXITY_THRESHOLD=20
SAHA_HOOK_NTFY_ENABLED=true
```

## Documentation

- **[User Guide](docs/user-guide.md)** — Complete usage guide
- **[Architecture](docs/architecture.md)** — Developer reference

## Status

**Alpha** — Actively developed. API may change.

## License

[MIT](LICENSE)

---

<p align="center">
  <sub>Built for <a href="https://claude.ai/code">Claude Code</a></sub>
</p>
