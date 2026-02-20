<p align="center">
  <img src="assets/logo.png" alt="Sahaidachny" width="180">
</p>

<h1 align="center">Sahaidachny</h1>

<p align="center">
  <strong>Autonomous AI agent orchestrator for hierarchical task execution in Claude Code and Codex</strong>
</p>

<p align="center">
  <a href="https://github.com/roman-romanov-o/sahaidachny/actions/workflows/ci.yml"><img src="https://github.com/roman-romanov-o/sahaidachny/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/sahaidachny/"><img src="https://img.shields.io/pypi/v/sahaidachny.svg" alt="PyPI"></a>
  <a href="https://pypi.org/project/sahaidachny/"><img src="https://img.shields.io/pypi/pyversions/sahaidachny.svg" alt="Python Versions"></a>
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

It's a Claude Code plugin for planning plus a runner-agnostic execution loop that enables:

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

### Complete Installation Guide (From Scratch)

Don't have Python or any tools installed? No problem! Follow these steps:

#### Step 1: Install Python 3.11+

**macOS:**
```bash
# Using Homebrew (recommended)
brew install python@3.11
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip
```

**Windows:**
Download from [python.org](https://www.python.org/downloads/) (version 3.11 or higher)

#### Step 2: Install uv (Fast Python Package Manager)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Restart your terminal after installation.

#### Step 3: Install Sahaidachny

```bash
uv tool install sahaidachny
```

**Alternative options:**

Using pipx (recommended for CLI tools):
```bash
pipx install sahaidachny
```

Using pip:
```bash
pip install sahaidachny
```

#### Step 4: Install a CLI for Planning

Claude Code is recommended for `/saha:*` slash-command planning:

```bash
# macOS/Linux
curl -fsSL https://install.claude.ai | sh

# Verify installation
claude --version
```

For Windows or detailed instructions, see: https://docs.anthropic.com/en/docs/claude-code

Optional CLIs:

```bash
# Codex CLI
codex --version

# Gemini CLI
gemini --version
```

#### Step 5: Verify Everything Works

```bash
# Check Sahaidachny
saha version
saha tools

# Check Claude Code
claude --version
```

You should see version information for both tools. You're ready to go! 🚀

### Optional: Install Quality Tools

For the execution loop to run code quality checks, install these tools:

```bash
uv tool install ruff          # Linting and formatting
uv tool install ty            # Type checking
uv tool install complexipy    # Complexity analysis
uv pip install pytest         # Testing
```

### Install from Source (For Development)

```bash
git clone https://github.com/roman-romanov-o/sahaidachny.git
cd sahaidachny
uv tool install .
```

## Quick Start

### 1. Sync Artifacts to Local CLI Directories

```bash
# Sync .claude, .codex, and .gemini in current project
saha sync --target all
```

### 2. Launch Your Preferred Planning CLI

```bash
saha claude
# or
saha codex
# or
saha gemini
```

`/saha:*` slash commands are Claude Code features. For Codex/Gemini, use synced artifacts in `.codex/` or `.gemini/` as local planning resources.

### 3. Initialize a Task

```bash
# In Claude Code:
/saha:init user-authentication --mode=full
```

### 4. Plan the Task

```bash
/saha:research      # Explore codebase (for existing projects)
/saha:task          # Define what to build
/saha:stories       # Generate user stories
/saha:verify        # Approve artifacts
/saha:plan          # Create implementation phases
```

### 5. Execute Autonomously

```bash
# Back in terminal:
saha run task-01
```

To run execution agents with Codex instead of Claude Code, set:

```bash
export SAHA_AGENTS__DEFAULT_RUNNER=codex
```

Or run a single task with Codex:

```bash
saha run task-01 --runner codex
```

### 6. Monitor Progress

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
| `saha sync [--target ...]` | Sync local CLI artifacts |
| `saha claude` | Launch Claude Code with plugin |
| `saha codex` | Launch Codex CLI with synced artifacts |
| `saha gemini` | Launch Gemini CLI with synced artifacts |

To stop a running loop, press `Ctrl+C`. Sahaidachny will stop the current agent, run the Manager to update task artifacts, and mark the task as stopped so you can resume later.

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

# Use Codex for execution agents
# SAHA_AGENTS__DEFAULT_RUNNER=codex
# SAHA_CODEX_MODEL=o3
# SAHA_CODEX_DANGEROUSLY_BYPASS_SANDBOX=false
# SAHA_CLAUDE_DANGEROUSLY_SKIP_PERMISSIONS=false
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
  <sub>Built for <a href="https://claude.ai/code">Claude Code</a> planning and multi-runner execution (Claude Code, Codex, Gemini)</sub>
</p>
