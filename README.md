# Sahaidachny

**An autonomous AI agent loop for hierarchical task execution in Claude Code.**

> Named after [Petro Sahaidachny](https://en.wikipedia.org/wiki/Petro_Konashevych-Sahaidachny), the legendary Ukrainian Cossack hetman known for strategic planning and decisive execution.

---

## What is Sahaidachny?

A Claude Code plugin that enables:

1. **Structured Planning** — Build hierarchical task specifications (not flat PRDs)
2. **Autonomous Execution** — Run agentic loops across multiple context windows
3. **State Persistence** — Maintain learnings and progress between iterations

## Why Not Just Use Ralph?

[Ralph](https://github.com/snarktank/ralph) is great for simple linear task execution. Sahaidachny extends this with:

| Feature | Ralph | Sahaidachny |
|---------|-------|-------------|
| Task structure | Flat JSON | Hierarchical markdown |
| Planning phase | Manual PRD | Guided skill-based |
| User stories | Inline | Separate files with templates |
| Design decisions | None | Tracked and linked |
| Test specs | "Run tests" | E2E/Integration/Unit specs |
| Implementation | Priority-based | Phased with dependencies |

## Installation

```bash
# Install globally via pipx (recommended)
cd /path/to/sahaidachny
pipx install .

# Or via uv
uv tool install .

# Verify installation
saha version
```

## Quick Start

```bash
# Launch Claude Code with Sahaidachny plugin
saha claude

# Initialize a new task (full mode for existing codebase)
/saha:init my-feature --mode=full

# Or minimal mode for greenfield
/saha:init my-feature --mode=minimal

# Check planning progress
/saha:status

# Run autonomous execution
saha run task-01
```

## Planning Flow

```
/saha:research    → Explore codebase
/saha:task        → Define task description
/saha:stories     → Generate user stories
/saha:verify      → Approve artifacts
/saha:contracts   → Define API contracts
/saha:test-specs  → Write test specifications
/saha:plan        → Create implementation phases
```

## Task Structure

```
task-XX/
├── README.md                 # Status dashboard
├── task-description.md       # Technical overview
├── user-stories/             # Requirements
├── design-decisions/         # Architecture decisions
├── api-contracts/            # Interface definitions
├── implementation-plan/      # Execution phases
├── test-specs/               # Test specifications
└── research/                 # Supporting research
```

## Documentation

- [User Guide](docs/user-guide.md) — Complete usage guide for planning and execution
- [Architecture](docs/architecture.md) — Developer reference with code navigation
- [Planning Document](PLANNING.md) — Detailed design and flow diagrams

## Status

🚧 **In Development** — Currently in design phase.

---

## License

MIT
