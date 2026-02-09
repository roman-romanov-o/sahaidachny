# Sahaidachny Architecture

**Developer Reference for Code Navigation**

This document provides a technical overview of Sahaidachny's architecture, organized into its two main phases with direct code references for easy codebase traversal.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Phase 1: Planning (Claude Code Plugin)](#phase-1-planning-claude-code-plugin)
   - [Plugin Structure](#plugin-structure)
   - [Planning Commands](#planning-commands)
   - [Planning Agents](#planning-agents)
   - [Templates](#templates)
3. [Phase 2: Execution (Agentic Loop)](#phase-2-execution-agentic-loop)
   - [Core Package Structure](#core-package-structure)
   - [Orchestrator](#orchestrator)
   - [Execution Agents](#execution-agents)
   - [Runners](#runners)
   - [State Management](#state-management)
   - [Tools Integration](#tools-integration)
   - [Hooks](#hooks)
4. [Data Flow](#data-flow)
5. [Key Interfaces](#key-interfaces)
6. [Extension Points](#extension-points)

---

## System Overview

Sahaidachny operates in two distinct phases:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PHASE 1: PLANNING                                │
│                   (Claude Code Plugin)                              │
│                                                                     │
│   User ←→ Claude Code ←→ Sahaidachny Commands                       │
│                              │                                      │
│                              ↓                                      │
│                      Task Artifacts                                 │
│           (user-stories/, implementation-plan/, etc.)               │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ Task artifacts ready
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    PHASE 2: EXECUTION                               │
│                   (Agentic Loop via saha CLI)                       │
│                                                                     │
│   saha run → Orchestrator → Runner → Subagents                      │
│                   │                       │                         │
│                   ↓                       ↓                         │
│              State File            Code Changes                     │
│         (.sahaidachny/)                                             │
└─────────────────────────────────────────────────────────────────────┘
```

### Package Structure Overview

```
sahaidachny/
├── saha/                      # Core execution package
│   ├── cli.py                 # CLI entry point (minimal wiring)
│   ├── commands/              # CLI commands organized by function
│   │   ├── execution.py       # Agentic loop commands (run, resume, etc.)
│   │   ├── plugin.py          # Plugin management (plugin, claude)
│   │   └── common.py          # Shared CLI utilities
│   ├── config/                # Configuration management
│   ├── orchestrator/          # Agentic loop orchestration
│   │   ├── loop.py            # Main agentic loop
│   │   ├── state.py           # State persistence
│   │   └── factory.py         # Orchestrator creation
│   ├── runners/               # LLM backend runners
│   ├── models/                # Pydantic models
│   ├── tools/                 # External tool integrations
│   └── hooks/                 # Event hooks
├── claude_plugin/             # Planning phase plugin
│   ├── commands/              # Slash command definitions
│   ├── agents/                # Subagent specifications
│   ├── templates/             # Artifact templates
│   └── scripts/               # Helper scripts
└── task_tracker/              # Task tracking utilities
```

---

## Phase 1: Planning (Claude Code Plugin)

The planning phase operates within Claude Code as a plugin, providing slash commands that guide users through structured task specification.

### Plugin Structure

**Location:** `claude_plugin/`

```
claude_plugin/
├── __init__.py                      # Plugin path helper
├── settings.json                    # Claude Code settings
├── commands/                        # Slash command definitions
│   ├── init.md                      # /saha:init
│   ├── research.md                  # /saha:research
│   ├── task.md                      # /saha:task
│   ├── stories.md                   # /saha:stories
│   ├── decide.md                    # /saha:decide
│   ├── contracts.md                 # /saha:contracts
│   ├── test-specs.md                # /saha:test-specs
│   ├── plan.md                      # /saha:plan
│   ├── verify.md                    # /saha:verify
│   └── status.md                    # /saha:status
├── agents/                          # Planning phase agents
│   ├── planning_research.md         # Research agent
│   ├── planning_reviewer.md         # Artifact reviewer
│   ├── execution_implementer.md     # Implementation agent
│   ├── execution_qa.md              # QA agent
│   ├── execution_manager.md         # Manager agent
│   └── execution_dod.md             # DoD agent
├── templates/                       # Artifact templates
│   ├── task-description.md
│   ├── user-story.md
│   ├── design-decision.md
│   ├── api-contract-rest.md
│   ├── api-contract-event.md
│   ├── test-spec-{e2e,integration,unit}.md
│   ├── implementation-phase.md
│   └── research-report.md
└── scripts/
    ├── init_task.sh                 # Task folder initialization
    ├── welcome.sh                   # Welcome message
    └── help.sh                      # Help display
```

**Plugin Entry:** `claude_plugin/__init__.py:1-12`
- Provides `get_plugin_path()` to locate plugin resources at runtime

### Planning Commands

Each command is a markdown file with YAML frontmatter defining its behavior.

#### Command Frontmatter Format

```yaml
---
description: Human-readable description
argument-hint: <arg> [--option=value]
allowed-tools: Read, Write, Glob, Grep, ...
---
```

#### Command Reference Table

| Command | File | Purpose | Key Tools |
|---------|------|---------|-----------|
| `/saha:init` | `commands/init.md:1-51` | Create task folder structure | Bash |
| `/saha:research` | `commands/research.md` | Deep codebase exploration | Read, Glob, Grep, Task |
| `/saha:task` | `commands/task.md` | Define task description | Read, Write, AskUserQuestion |
| `/saha:stories` | `commands/stories.md:1-199` | Generate user stories | Read, Write, Glob, Task |
| `/saha:decide` | `commands/decide.md` | Record design decisions | Read, Write, AskUserQuestion |
| `/saha:contracts` | `commands/contracts.md` | Define API contracts | Read, Write, Glob |
| `/saha:test-specs` | `commands/test-specs.md` | Create test specifications | Read, Write, Glob |
| `/saha:plan` | `commands/plan.md:1-246` | Generate implementation phases | Read, Write, Glob, Grep, Task |
| `/saha:verify` | `commands/verify.md` | Validate artifacts | Read, Write, Task |
| `/saha:status` | `commands/status.md` | Show planning progress | Read, Glob |

#### Command Execution Flow

```
User types: /saha:stories

    ↓

Claude Code loads: commands/stories.md
    - Parses frontmatter for allowed-tools
    - Injects command content into context

    ↓

Claude executes command instructions:
    1. Reads task-description.md
    2. Identifies user personas
    3. Generates story candidates
    4. Asks user for approval (AskUserQuestion)
    5. Creates user-stories/US-XXX.md files
    6. Launches reviewer agent (Task tool)

    ↓

Output: Multiple user story files created
```

### Planning Agents

Planning uses subagents for specific tasks like research and artifact review.

**Location:** `claude_plugin/agents/`

| Agent | File | Purpose |
|-------|------|---------|
| Planning Research | `agents/planning_research.md` | Deep codebase exploration |
| Planning Reviewer | `agents/planning_reviewer.md` | Validate planning artifacts |

#### Planning Reviewer Agent

**File:** `claude_plugin/agents/planning_reviewer.md`

Reviews artifacts for completeness and correctness:
- User stories: INVEST criteria (Independent, Negotiable, Valuable, Estimable, Small, Testable)
- Design decisions: Complete context, alternatives, consequences
- Implementation plans: Dependencies, phases, acceptance criteria

### Templates

Templates provide consistent structure for all planning artifacts.

**Location:** `claude_plugin/templates/`

| Template | File | Used By |
|----------|------|---------|
| Task Description | `templates/task-description.md` | `/saha:task` |
| User Story | `templates/user-story.md` | `/saha:stories` |
| Design Decision | `templates/design-decision.md` | `/saha:decide` |
| REST API Contract | `templates/api-contract-rest.md` | `/saha:contracts` |
| Event Contract | `templates/api-contract-event.md` | `/saha:contracts` |
| E2E Test Spec | `templates/test-spec-e2e.md` | `/saha:test-specs` |
| Integration Test Spec | `templates/test-spec-integration.md` | `/saha:test-specs` |
| Unit Test Spec | `templates/test-spec-unit.md` | `/saha:test-specs` |
| Implementation Phase | `templates/implementation-phase.md` | `/saha:plan` |
| Research Report | `templates/research-report.md` | `/saha:research` |

---

## Phase 2: Execution (Agentic Loop)

The execution phase runs via the `saha` CLI, orchestrating an autonomous loop that implements, verifies, and iterates until the task is complete.

### Core Package Structure

**Location:** `saha/`

```
saha/
├── __init__.py              # Package version
├── cli.py                   # CLI entry point (minimal wiring)
├── commands/                # CLI commands by function
│   ├── __init__.py          # Package exports
│   ├── execution.py         # run, resume, status, tools, clean, version
│   ├── plugin.py            # plugin, claude
│   └── common.py            # Shared utilities (setup_logging)
├── config/
│   ├── __init__.py
│   └── settings.py          # Pydantic settings models
├── orchestrator/
│   ├── __init__.py
│   ├── loop.py              # Main agentic loop
│   ├── state.py             # State persistence manager
│   └── factory.py           # Orchestrator creation helpers
├── runners/
│   ├── __init__.py
│   ├── base.py              # Runner abstract base class
│   ├── registry.py          # Runner factory registry
│   ├── claude.py            # Claude Code CLI runner
│   ├── codex.py             # Codex CLI runner
│   └── gemini.py            # Gemini CLI runner
├── models/
│   ├── __init__.py
│   ├── state.py             # State Pydantic models
│   └── result.py            # Result Pydantic models
├── tools/
│   ├── __init__.py
│   ├── registry.py          # Tool registry
│   ├── ruff.py              # Ruff linting tool
│   ├── ty.py                # ty type checking tool
│   ├── complexity.py        # Complexipy tool
│   └── pytest_runner.py     # Pytest runner tool
└── hooks/
    ├── __init__.py
    ├── base.py              # Hook abstract base class
    ├── registry.py          # Hook event registry
    └── notification.py      # Logging and ntfy hooks
```

### Orchestrator

The orchestrator manages the agentic loop lifecycle.

#### AgenticLoop Class

**File:** `saha/orchestrator/loop.py:37-534`

```python
class AgenticLoop:
    """Orchestrates the agentic implementation loop.

    The loop follows this flow:
    1. Get next task/phase to implement
    2. Run Implementation Subagent → produces code diff
    3. Run QA Subagent → verifies DoD with tools
    4. If DoD not achieved → back to step 2 with fix info
    5. Run Code Quality Subagent → checks Ruff, ty, complexity
    6. If quality fails → back to step 2 with fix info
    7. Run Manager Subagent → updates task status
    8. Run DoD Subagent → checks if task is complete
    9. If complete → end, else → back to step 1
    """
```

**Key Methods:**

| Method | Line | Purpose |
|--------|------|---------|
| `run()` | `101-127` | Main loop entry point |
| `resume()` | `129-147` | Resume from saved state |
| `_should_continue()` | `149-158` | Check termination conditions |
| `_run_iteration()` | `160-212` | Execute single iteration |
| `_run_implementation()` | `214-253` | Run implementation agent |
| `_run_qa()` | `255-318` | Run QA verification |
| `_run_code_quality()` | `320-391` | Run code quality checks |
| `_run_manager()` | `425-445` | Run status update agent |
| `_run_dod_check()` | `447-472` | Run completion check |

#### LoopConfig

**File:** `saha/orchestrator/loop.py:26-35`

```python
@dataclass
class LoopConfig:
    task_id: str
    task_path: Path
    max_iterations: int = 10
    enabled_tools: list[str] | None = None
    playwright_enabled: bool = False
    verification_scripts: list[Path] | None = None
```

#### Loop Flow Visualization

```
AgenticLoop.run()
    │
    ├── _state_manager.load() or create()
    ├── _hooks.trigger("loop_start")
    │
    └── while _should_continue(state):
            │
            └── _run_iteration()
                    │
                    ├── _run_implementation()
                    │       └── runner.run_agent("execution-implementer", ...)
                    │
                    ├── _run_qa()
                    │       └── runner.run_agent("execution-qa", ...)
                    │       └── If DoD not achieved: set fix_info, return
                    │
                    ├── _run_code_quality()
                    │       └── runner.run_agent("execution-code-quality", ...)
                    │       └── If quality fails: set fix_info, return
                    │
                    ├── _run_manager()
                    │       └── runner.run_agent("execution-manager", ...)
                    │
                    └── _run_dod_check()
                            └── runner.run_agent("execution-dod", ...)
                            └── If complete: mark_completed()
```

### Execution Agents

Execution agents are runner-agnostic agent specs invoked by the orchestrator (Claude Code, Codex, or Gemini).

**Location:** `claude_plugin/agents/` (also symlinked to `.claude/agents/`)

| Agent | File | Invoked By | Purpose |
|-------|------|------------|---------|
| Implementation | `execution_implementer.md:1-118` | `_run_implementation()` | Write code changes |
| QA | `execution_qa.md:1-172` | `_run_qa()` | Verify DoD criteria |
| Code Quality | `.claude/agents/execution-code-quality.md` | `_run_code_quality()` | Run quality checks |
| Manager | `execution_manager.md` | `_run_manager()` | Update task artifacts |
| DoD | `execution_dod.md:1-159` | `_run_dod_check()` | Check task completion |

#### Agent Output Contracts

**Implementation Agent:**
```json
{
  "status": "success|partial|blocked",
  "files_changed": ["path/to/file.py"],
  "files_added": ["path/to/new.py"],
  "summary": "Description of changes",
  "next_steps": "What to verify"
}
```

**QA Agent:**
```json
{
  "dod_achieved": true|false,
  "checks": [{"criterion": "...", "passed": true|false, "details": "..."}],
  "test_results": {"total": 10, "passed": 8, "failed": 2},
  "fix_info": "If failed, what to fix"
}
```

**Code Quality Agent:**
```json
{
  "quality_passed": true|false,
  "issues": [{"file": "...", "line": 42, "message": "..."}],
  "files_analyzed": ["path/to/file.py"],
  "blocking_issues_count": 0,
  "ignored_issues_count": 3,
  "fix_info": "If failed, what to fix"
}
```

**DoD Agent:**
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
  "recommendation": "Ready for delivery"
}
```

### Runners

Runners abstract LLM backends for agent execution.

#### Base Runner Interface

**File:** `saha/runners/base.py`

```python
class Runner(ABC):
    @abstractmethod
    def run_agent(
        self,
        agent_spec_path: Path,
        prompt: str,
        context: dict[str, Any] | None = None,
        timeout: int = 300,
    ) -> RunnerResult: ...

    @abstractmethod
    def run_prompt(
        self,
        prompt: str,
        system_prompt: str | None = None,
        timeout: int = 300,
    ) -> RunnerResult: ...

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def get_name(self) -> str: ...
```

#### Runner Implementations

| Runner | File | Backend |
|--------|------|---------|
| ClaudeRunner | `saha/runners/claude.py:12-206` | Claude Code CLI |
| CodexRunner | `saha/runners/codex.py` | Codex CLI |
| GeminiRunner | `saha/runners/gemini.py` | Gemini CLI |
| MockRunner | `saha/runners/claude.py:209-266` | Testing mock |

#### ClaudeRunner

**File:** `saha/runners/claude.py:12-206`

Key methods:

| Method | Line | Purpose |
|--------|------|---------|
| `run_agent()` | `32-50` | Invoke Claude Code agent |
| `run_prompt()` | `52-60` | Run direct prompt |
| `_build_agent_command()` | `143-160` | Build `claude --agent` command |
| `_try_parse_json()` | `182-206` | Extract JSON from output |

**Command Building:**
```python
cmd = [
    "claude",
    "--print",          # Non-interactive output
    "--agent", agent_name,  # Native agent invocation
    "--prompt", prompt,
]
```

#### CodexRunner

**File:** `saha/runners/codex.py`

Key characteristics:

1. Runs `codex exec` non-interactively and captures the last assistant message via `--output-last-message`.
2. Embeds the agent spec markdown (minus frontmatter) into the prompt as a system prelude.
3. Loads any referenced skills from `.claude/skills` or `claude_plugin/skills` and appends them to the prompt.
4. Tracks file changes by taking a filesystem snapshot before/after the run (since Codex CLI does not emit tool metadata).

#### Runner Registry

**File:** `saha/runners/registry.py`

Manages runner factories and per-agent runner configuration.

```python
class RunnerRegistry:
    def register_factory(self, runner_type: RunnerType, factory, **kwargs): ...
    def get_runner(self, runner_type: RunnerType) -> Runner: ...
    def get_runner_for_agent(self, agent_name: str) -> Runner: ...
    def configure_agent(self, config: AgentConfig): ...
    def set_default_runner(self, runner_type: RunnerType): ...
```

**Usage:** `saha/orchestrator/factory.py` and `saha/commands/execution.py`

### State Management

#### State Models

**File:** `saha/models/state.py:1-119`

```python
class LoopPhase(str, Enum):
    IDLE = "idle"
    IMPLEMENTATION = "implementation"
    QA = "qa"
    CODE_QUALITY = "code_quality"
    MANAGER = "manager"
    DOD_CHECK = "dod_check"
    COMPLETED = "completed"
    FAILED = "failed"

class ExecutionState(BaseModel):
    task_id: str
    task_path: Path
    current_phase: LoopPhase
    current_iteration: int
    max_iterations: int
    started_at: datetime | None
    completed_at: datetime | None
    iterations: list[IterationRecord]
    enabled_tools: list[str]
    context: dict[str, Any]
```

#### StateManager

**File:** `saha/orchestrator/state.py`

```python
class StateManager:
    def __init__(self, state_dir: Path): ...
    def create(self, task_id: str, task_path: Path, ...) -> ExecutionState: ...
    def load(self, task_id: str) -> ExecutionState | None: ...
    def save(self, state: ExecutionState): ...
    def update_phase(self, state: ExecutionState, phase: LoopPhase): ...
    def mark_completed(self, state: ExecutionState): ...
    def mark_failed(self, state: ExecutionState, error: str): ...
    def list_tasks(self) -> list[str]: ...
    def delete(self, task_id: str) -> bool: ...
```

**State File Format:** YAML at `.sahaidachny/{task_id}-execution-state.yaml`

### Tools Integration

Tools run external code quality checks during execution.

#### Tool Registry

**File:** `saha/tools/registry.py`

```python
class ToolRegistry:
    def register(self, name: str, tool: Tool): ...
    def get(self, name: str) -> Tool | None: ...
    def list_all(self) -> list[str]: ...
    def list_available(self) -> list[str]: ...
    def run_tool(self, name: str, path: Path) -> ToolResult: ...

def create_default_registry() -> ToolRegistry:
    """Create registry with all built-in tools."""
```

#### Tool Implementations

| Tool | File | External Command |
|------|------|------------------|
| Ruff | `saha/tools/ruff.py` | `ruff check --output-format json` |
| ty | `saha/tools/ty.py` | `ty check --output-format json` |
| Complexipy | `saha/tools/complexity.py` | `complexipy` |
| Pytest | `saha/tools/pytest_runner.py` | `pytest -v --tb=short` |

### Hooks

Hooks enable event-driven extensions to the loop.

#### Hook Registry

**File:** `saha/hooks/registry.py`

```python
class HookRegistry:
    def register(self, hook: Hook): ...
    def trigger(self, event: str, **kwargs): ...
```

**Events:**
- `loop_start` - Loop begins
- `iteration_start` - Iteration begins
- `implementation_start` - Implementation phase starts
- `qa_start` - QA phase starts
- `qa_failed` - QA verification failed
- `quality_start` - Code quality phase starts
- `quality_failed` - Quality check failed
- `iteration_complete` - Iteration finished
- `loop_complete` - Loop finished successfully
- `loop_error` - Loop failed with error

#### Built-in Hooks

**File:** `saha/hooks/notification.py`

| Hook | Purpose |
|------|---------|
| `LoggingHook` | Log events to Python logger |
| `NtfyHook` | Send push notifications via ntfy.sh |

---

## Data Flow

### Planning Phase Data Flow

```
User Input
    │
    ↓
/saha:init
    │
    └── Creates: task-XX/
            ├── README.md
            └── subdirectories/
    │
    ↓
/saha:research
    │
    └── Creates: task-XX/research/*.md
    │
    ↓
/saha:task
    │
    └── Creates: task-XX/task-description.md
    │
    ↓
/saha:stories
    │
    └── Creates: task-XX/user-stories/US-*.md
    │
    ↓
/saha:plan
    │
    └── Creates: task-XX/implementation-plan/phase-*.md
```

### Execution Phase Data Flow

```
saha run task-01
    │
    ├── Reads: task-01/implementation-plan/phase-*.md
    ├── Reads: task-01/user-stories/US-*.md
    │
    ↓
Implementation Agent
    │
    ├── Reads: Existing source files
    └── Writes: Modified/new source files
    │
    ↓
QA Agent
    │
    ├── Reads: task-01/user-stories/US-*.md (acceptance criteria)
    ├── Runs: pytest
    └── Returns: dod_achieved, fix_info
    │
    ↓
Code Quality Agent
    │
    ├── Runs: ruff, ty, complexipy
    └── Returns: quality_passed, fix_info
    │
    ↓
Manager Agent
    │
    └── Updates: task-01/README.md, user-stories/*.md status
    │
    ↓
DoD Agent
    │
    ├── Reads: All task artifacts
    └── Returns: task_complete decision
```

---

## Key Interfaces

### Configuration Interface

**File:** `saha/config/settings.py:97-164`

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SAHA_",
        env_nested_delimiter="__",
        env_file=".env",
    )

    state_dir: Path = Path(".sahaidachny")
    task_base_path: Path = Path("docs/tasks")
    max_iterations: int = 10
    runner: Literal["claude", "codex", "gemini", "mock"] = "claude"
    claude_model: str = "claude-sonnet-4-20250929"
    codex_model: str | None = None
    codex_sandbox: Literal["read-only", "workspace-write", "danger-full-access"] = "workspace-write"
    claude_dangerously_skip_permissions: bool = False
    codex_dangerously_bypass_sandbox: bool = False
    agents_path: Path = Path(".claude/agents")

    tools: ToolConfig
    hooks: HookConfig
    agents: AgentsConfig

    def get_task_path(self, task_id: str) -> Path: ...
    def get_agent_path(self, agent_name: str, variant: str | None = None) -> Path: ...
    def get_agent_runner_config(self, agent_name: str) -> AgentRunnerConfig: ...
```

### Result Models

**File:** `saha/models/result.py`

```python
class SubagentResult(BaseModel):
    agent_name: str
    status: ResultStatus
    output: str | None = None
    error: str | None = None
    structured_output: dict[str, Any] = {}

class QAResult(BaseModel):
    status: ResultStatus
    dod_achieved: bool
    fix_info: str | None = None
    test_output: str | None = None

class CodeQualityResult(BaseModel):
    status: ResultStatus
    passed: bool
    fix_info: str | None = None
    issues: list[dict[str, Any]] = []
    files_analyzed: list[str] = []
    blocking_issues_count: int = 0
    ignored_issues_count: int = 0
```

---

## Extension Points

### Adding a New Planning Command

1. Create `claude_plugin/commands/{command-name}.md`
2. Add YAML frontmatter with `description`, `argument-hint`, `allowed-tools`
3. Write command instructions in markdown
4. Optionally create a template in `claude_plugin/templates/`

### Adding a New Runner

1. Create `saha/runners/{runner_name}.py`
2. Implement the `Runner` abstract base class
3. Register in `saha/orchestrator/factory.py:create_runner_registry()`
4. Add to `RunnerType` enum in `saha/runners/registry.py`

### Adding a New Tool

1. Create `saha/tools/{tool_name}.py`
2. Implement the `Tool` interface (see existing tools)
3. Register in `saha/tools/registry.py:create_default_registry()`
4. Add configuration in `saha/config/settings.py:ToolConfig`

### Adding a New Hook

1. Create hook class implementing `Hook` base class
2. Register in `saha/orchestrator/factory.py:create_orchestrator()`
3. Handle events in `on_event()` method

### Adding a New Execution Agent

1. Create `claude_plugin/agents/execution_{agent_name}.md`
2. Define agent behavior and output format
3. Add invocation in `saha/orchestrator/loop.py`
4. Add to agent configuration in `saha/config/settings.py:AgentsConfig`

---

## Quick Reference: File Locations

### Core Execution

| Component | Location |
|-----------|----------|
| CLI Entry | `saha/cli.py` (minimal wiring, ~30 lines) |
| Execution Commands | `saha/commands/execution.py` (run, resume, status, tools, clean, version) |
| Plugin Commands | `saha/commands/plugin.py` (plugin, claude) |
| Orchestrator Factory | `saha/orchestrator/factory.py` |
| Main Loop | `saha/orchestrator/loop.py:101-127` |
| State Models | `saha/models/state.py:58-119` |
| Settings | `saha/config/settings.py:97-164` |
| Claude Runner | `saha/runners/claude.py:12-206` |
| Codex Runner | `saha/runners/codex.py` |

### Planning Commands

| Command | Location |
|---------|----------|
| init | `claude_plugin/commands/init.md` |
| stories | `claude_plugin/commands/stories.md` |
| plan | `claude_plugin/commands/plan.md` |

### Execution Agents

| Agent | Location |
|-------|----------|
| Implementation | `claude_plugin/agents/execution_implementer.md` |
| QA | `claude_plugin/agents/execution_qa.md` |
| DoD | `claude_plugin/agents/execution_dod.md` |

### Templates

| Template | Location |
|----------|----------|
| User Story | `claude_plugin/templates/user-story.md` |
| Phase | `claude_plugin/templates/implementation-phase.md` |

---

**Last Updated:** 2026-01-27
