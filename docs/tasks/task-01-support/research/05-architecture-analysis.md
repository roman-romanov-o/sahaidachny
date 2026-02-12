# Research: Runner Architecture and Orchestrator Integration

**Date:** 2026-02-12
**Status:** Complete

## Summary

The runner architecture is **well-designed and extensible**. The abstraction layer correctly separates concerns, the registry pattern enables multi-backend support, and the orchestrator integration is clean. No architectural changes are needed - the existing design already supports the requirements.

## Architecture Overview

### Component Hierarchy

```
AgenticLoop (orchestrator)
    ↓ uses
RunnerRegistry (multi-backend manager)
    ↓ creates
Runner implementations (Claude, Codex, Gemini, Mock)
    ↓ execute
LLM CLIs (claude, codex, gemini commands)
```

### Data Flow

```
1. Orchestrator calls: registry.get_runner_for_agent("execution-qa")
2. Registry returns: Configured runner instance (e.g., ClaudeRunner)
3. Orchestrator calls: runner.run_agent(agent_spec_path, prompt, context)
4. Runner executes: Subprocess with CLI-specific commands
5. Runner parses: Output → RunnerResult(output, structured_output, token_usage)
6. Orchestrator receives: Result with success/failure, files changed, token count
7. Orchestrator updates: State, triggers next phase, handles fix_info
```

## Key Architectural Components

### 1. Runner Interface (Abstract Base)

**Location:** `saha/runners/base.py:70-126`

**Contract:**
```python
class Runner(ABC):
    @abstractmethod
    def run_agent(agent_spec_path, prompt, context, timeout) -> RunnerResult

    @abstractmethod
    def run_prompt(prompt, system_prompt, timeout) -> RunnerResult

    @abstractmethod
    def is_available() -> bool

    @abstractmethod
    def get_name() -> str
```

**Why this is good:**
- Minimal interface (4 methods only)
- Clear responsibilities (agent vs simple prompt)
- Availability check enables validation
- Name getter enables logging/debugging

**Assessment:** ✓ Well-designed, no changes needed

### 2. RunnerResult Data Class

**Location:** `saha/runners/base.py:10-51`

**Fields:**
```python
@dataclass
class RunnerResult:
    success: bool                          # Execution succeeded
    output: str                            # Text output from LLM
    structured_output: dict | None = None  # Parsed JSON (files_changed, etc.)
    error: str | None = None               # Error message if failed
    tokens_used: int = 0                   # Total tokens (for cost tracking)
    token_usage: dict[str, int] | None = None  # Detailed usage breakdown
    exit_code: int = 0                     # Process exit code
```

**Why this is good:**
- Distinguishes text output from structured data
- Includes both simple (tokens_used) and detailed (token_usage) metrics
- Error message provides debugging info
- Factory methods (`failure()`, `success_result()`) enforce consistency

**Assessment:** ✓ Comprehensive, covers all use cases

### 3. RunnerRegistry (Multi-Backend Manager)

**Location:** `saha/runners/registry.py:46-206`

**Responsibilities:**
1. Register runner factories with configuration
2. Lazy instantiation of runners (create on first use)
3. Per-agent runner selection
4. Agent variant support (e.g., execution-qa-playwright)
5. Convenience method for running agents

**Key patterns:**

**Factory registration:**
```python
registry.register_factory(
    RunnerType.CODEX,
    CodexRunner,  # Class, not instance
    model="o3-mini",
    working_dir=Path.cwd(),
    sandbox="workspace-write",
)
```

**Per-agent configuration:**
```python
registry.configure_agent(
    AgentConfig(
        agent_name="execution-qa",
        runner_type=RunnerType.GEMINI,  # Use Gemini for QA
        agent_variant="playwright",      # Use playwright variant
        timeout=600,
    )
)
```

**Usage in orchestrator:**
```python
runner = registry.get_runner_for_agent("execution-qa")
result = runner.run_agent(agent_path, prompt, context)
```

**Why this is good:**
- Lazy instantiation avoids creating unused runners
- Factory pattern enables dependency injection
- Per-agent configuration allows mixing runners
- Variant support enables conditional tool sets (e.g., playwright)
- Clean separation from orchestrator logic

**Assessment:** ✓ Excellent design, enables all requirements

### 4. Settings Integration

**Location:** `saha/config/settings.py:40-173`

**Configuration layers:**

**Global defaults:**
```python
class Settings(BaseSettings):
    runner: Literal["claude", "codex", "gemini", "mock"] = "claude"
    claude_model: str = "claude-sonnet-4-5-20250929"
    codex_model: str | None = None
    gemini_model: str = "gemini-2.5-pro"
```

**Per-agent overrides:**
```python
class AgentsConfig(BaseSettings):
    default_runner: Literal[...] = "claude"
    implementer: AgentRunnerConfig = ...  # Can override
    qa: AgentRunnerConfig = ...           # Can override
    code_quality: AgentRunnerConfig = ... # Can override
```

**Environment variable mapping:**
```
SAHA_RUNNER=codex                      # Global default
SAHA_CODEX_MODEL=o3-mini               # Codex-specific
SAHA_AGENT_DEFAULT_RUNNER=gemini       # Agent default
SAHA_AGENT_QA__RUNNER=claude           # QA-specific override
SAHA_AGENT_QA__VARIANT=playwright      # QA variant
```

**Why this is good:**
- Hierarchical: global → agent default → per-agent override
- Environment variables enable easy CI/CD configuration
- Pydantic validation ensures type safety
- Nested delimiter (`__`) enables deep configuration

**Assessment:** ✓ Flexible, supports all use cases

### 5. Orchestrator Integration

**Location:** `saha/orchestrator/loop.py:87-115`

**Runner selection logic:**
```python
def _get_runner_for_agent(self, agent_name: str) -> Runner:
    """Get the appropriate runner for an agent."""
    if self._runner_registry:
        return self._runner_registry.get_runner_for_agent(agent_name)
    return self._runner  # Fallback to default runner

def _get_agent_path(self, agent_name: str) -> Path:
    """Get the path to an agent spec, considering variants."""
    config = self._settings.get_agent_runner_config(agent_name)
    return self._settings.get_agent_path(agent_name, variant=config.variant)
```

**Usage in execution:**
```python
# In _run_implementation()
runner = self._get_runner_for_agent("execution-implementer")
agent_path = self._get_agent_path("execution-implementer")
result = runner.run_agent(agent_path, prompt, context)

# Result handling
if result.success:
    structured = result.structured_output or {}
    files_changed = structured.get("files_changed", [])
    files_added = structured.get("files_added", [])
    # ... update state, proceed to next phase
else:
    # ... handle error, retry or fail
```

**Why this is good:**
- Orchestrator doesn't know which runner is used (loose coupling)
- Variant support is transparent to orchestrator
- Result handling is uniform across all runners
- Fallback to default runner ensures backwards compatibility

**Assessment:** ✓ Clean integration, no leaky abstractions

### 6. Factory Function

**Location:** `saha/orchestrator/factory.py:20-216`

**Initialization flow:**
```python
def create_orchestrator(settings: Settings) -> AgenticLoop:
    # 1. Create runner registry
    runner_registry = create_runner_registry(settings)

    # 2. Validate all configured runners are available
    validate_configured_runners(runner_registry, settings)

    # 3. Create default runner (backwards compatibility)
    runner = _create_default_runner(settings)

    # 4. Create other components
    tools = create_default_registry()
    hooks = _create_hook_registry(settings)
    state_manager = StateManager(settings.state_dir)

    # 5. Assemble orchestrator
    return AgenticLoop(
        runner=runner,
        tool_registry=tools,
        hook_registry=hooks,
        state_manager=state_manager,
        settings=settings,
        runner_registry=runner_registry,
    )
```

**Validation logic:**
```python
def validate_configured_runners(registry, settings):
    """Fail fast if configured runners aren't available."""
    configured_types = {RunnerType(settings.agents.default_runner)}
    for config in [settings.agents.qa, settings.agents.implementer, ...]:
        configured_types.add(RunnerType(config.runner))

    unavailable = []
    for runner_type in configured_types:
        runner = registry.get_runner(runner_type)
        if not runner.is_available():
            unavailable.append(runner.get_name())

    if unavailable:
        raise typer.Exit(1)  # Fail fast with clear error
```

**Why this is good:**
- Single entry point for orchestrator creation
- Validation happens at startup (fail fast principle)
- Clear error messages if CLIs are missing
- All dependencies assembled in one place

**Assessment:** ✓ Robust initialization, good error handling

## Design Patterns Used

### 1. Abstract Factory Pattern
- **Where:** `RunnerRegistry` with `register_factory()`
- **Benefit:** Defers runner creation until needed, enables dependency injection
- **Assessment:** ✓ Correct use of pattern

### 2. Registry Pattern
- **Where:** `RunnerRegistry` with type-based lookup
- **Benefit:** Centralized management, easy to add new runners
- **Assessment:** ✓ Correct use of pattern

### 3. Strategy Pattern
- **Where:** Different `Runner` implementations for different backends
- **Benefit:** Interchangeable algorithms (CLI execution strategies)
- **Assessment:** ✓ Correct use of pattern

### 4. Dependency Injection
- **Where:** Factory creates and injects runners into orchestrator
- **Benefit:** Testability, flexibility, loose coupling
- **Assessment:** ✓ Correct use of pattern

## Extensibility Analysis

### How to Add a New Runner (e.g., Aider CLI)

**Step 1:** Implement Runner interface
```python
class AiderRunner(Runner):
    def run_agent(self, agent_spec_path, prompt, context, timeout):
        # Build aider command
        # Execute subprocess
        # Parse output
        # Return RunnerResult

    def run_prompt(self, prompt, system_prompt, timeout):
        # Similar implementation

    def is_available(self) -> bool:
        return shutil.which("aider") is not None

    def get_name(self) -> str:
        return "aider-cli"
```

**Step 2:** Register in factory
```python
# In saha/orchestrator/factory.py
from saha.runners.aider import AiderRunner

def create_runner_registry(settings):
    registry = RunnerRegistry()
    # ... existing runners ...
    registry.register_factory(
        RunnerType.AIDER,
        AiderRunner,
        working_dir=Path.cwd(),
    )
```

**Step 3:** Add to configuration
```python
# In saha/config/settings.py
class RunnerType(str, Enum):
    CLAUDE = "claude"
    CODEX = "codex"
    GEMINI = "gemini"
    AIDER = "aider"  # Add here
    MOCK = "mock"
```

**Step 4:** Use in configuration
```bash
export SAHA_RUNNER=aider
export SAHA_AGENT_QA__RUNNER=aider
```

**Assessment:** ✓ Clear extension path, minimal changes needed

## Comparison with Alternative Architectures

### What We Have (Registry + Factory)
```
Pros:
- Per-agent runner selection
- Lazy instantiation
- Centralized configuration
- Easy to add new runners
- Clean separation of concerns

Cons:
- Slightly more complex than direct instantiation
- Registry is a global singleton (shared state)
```

### Alternative 1: Direct Instantiation
```python
# In orchestrator
if agent_name == "execution-qa":
    runner = GeminiRunner()
elif agent_name == "execution-implementer":
    runner = ClaudeRunner()
else:
    runner = CodexRunner()

Pros:
- Simpler, no registry needed

Cons:
- Orchestrator knows about all runners (tight coupling)
- Hard to configure via environment variables
- No lazy instantiation
- Violates Open/Closed Principle
```

### Alternative 2: Strategy with Context
```python
class RunnerContext:
    def set_strategy(self, runner: Runner):
        self._runner = runner

    def execute(self, agent_spec, prompt):
        return self._runner.run_agent(agent_spec, prompt)

Pros:
- Classic Strategy pattern

Cons:
- Manual strategy selection
- No per-agent configuration
- Less flexible than registry
```

### Alternative 3: Plugin System
```python
# Auto-discover runners in plugins/ directory
for plugin in discover_plugins("saha.runners"):
    registry.register(plugin)

Pros:
- Even more extensible
- Third-party runners possible

Cons:
- Overkill for current needs
- Harder to configure
- Implicit dependencies
```

**Assessment:** Current architecture (Registry + Factory) is **optimal** for the use case. Not too simple (wouldn't support requirements), not too complex (easy to understand and maintain).

## What Makes This Architecture Work

### 1. Clear Abstraction Boundaries

**Good:** Orchestrator knows about `Runner` interface, not specific implementations
```python
# Orchestrator code
runner = self._get_runner_for_agent(agent_name)  # Type: Runner
result = runner.run_agent(...)  # Uses interface only
```

**Bad (example of what we avoided):**
```python
# Anti-pattern: Orchestrator knowing implementation details
if isinstance(runner, ClaudeRunner):
    result = runner._execute_with_streaming(...)
elif isinstance(runner, CodexRunner):
    result = runner._run(...)
```

### 2. Consistent Result Format

**All runners return same structure:**
```python
RunnerResult(
    success=bool,
    output=str,
    structured_output={"files_changed": [...], "files_added": [...]},
    token_usage={"input_tokens": 100, "output_tokens": 50},
)
```

**Why this matters:** Orchestrator can process results uniformly, no special cases

### 3. Fail-Fast Validation

**Startup validation:**
```python
validate_configured_runners(registry, settings)
# If codex runner configured but CLI not installed → Exit immediately
```

**Why this matters:** Better to fail at startup with clear message than during execution

### 4. Hierarchical Configuration

**Precedence:** Per-agent > Agent default > Global default

**Example:**
```bash
# Global: Use Claude by default
SAHA_RUNNER=claude

# Agent default: Use Gemini for all agents
SAHA_AGENT_DEFAULT_RUNNER=gemini

# Per-agent: Use Codex specifically for QA
SAHA_AGENT_QA__RUNNER=codex
```

**Result:**
- implementer → Gemini (agent default)
- qa → Codex (per-agent override)
- code_quality → Gemini (agent default)
- manager → Gemini (agent default)
- dod → Gemini (agent default)

**Why this matters:** Flexibility without complexity

## Integration Points

### 1. State Management

**State tracks runner usage:**
```python
# In ExecutionState
current_phase: LoopPhase
current_iteration: int
files_changed: list[str]  # From runner's structured_output
files_added: list[str]    # From runner's structured_output
```

**Runner updates state indirectly:**
```python
result = runner.run_agent(...)
if result.success:
    structured = result.structured_output or {}
    state.record_step(
        phase=LoopPhase.IMPLEMENTATION,
        files_changed=structured.get("files_changed", []),
        files_added=structured.get("files_added", []),
    )
```

**Assessment:** ✓ Clean separation, state doesn't know about runners

### 2. Tool Registry

**Tools are runner-independent:**
```python
# Tools run in separate processes
tool_registry.run_tool("ruff", ["check", "src/"])

# Not run through LLM runner
```

**Why this matters:** Tools (ruff, ty, pytest) don't care which LLM runner is used

**Assessment:** ✓ Good separation of concerns

### 3. Hook System

**Hooks observe runner execution:**
```python
hooks.trigger("agent_start", agent_name="execution-qa", runner=runner.get_name())
hooks.trigger("agent_complete", agent_name="execution-qa", result=result)
```

**Hooks can track metrics:**
```python
class TokenTrackingHook(Hook):
    def on_event(self, event: str, **data):
        if event == "agent_complete":
            result = data.get("result")
            if result and result.token_usage:
                self.total_tokens += result.token_usage.get("total_tokens", 0)
```

**Assessment:** ✓ Extensibility without modifying core

## Critical Assessment

### Strengths

1. **Well-factored abstractions** - Interface is minimal yet sufficient
2. **Extensibility** - Adding new runners is straightforward
3. **Flexibility** - Per-agent configuration enables advanced scenarios
4. **Fail-fast validation** - Errors at startup, not during execution
5. **Backwards compatibility** - Default runner fallback preserves old behavior
6. **Separation of concerns** - Orchestrator doesn't know runner details
7. **Configuration hierarchy** - Simple defaults, granular overrides when needed

### Weaknesses

1. **Registry is singleton** - Shared state, harder to test in isolation
   - Mitigation: Factory function creates fresh registry per orchestrator
   - Impact: Low - acceptable trade-off for simplicity

2. **No async support** - Runners use synchronous subprocess
   - Mitigation: Not needed - execution is inherently sequential
   - Impact: None currently

3. **No runner pooling** - Creates new instance per agent
   - Mitigation: Registry caches instances by type
   - Impact: Low - runners are lightweight

4. **Token usage normalization is duplicated** - Each runner implements it
   - Mitigation: Shared `normalize_token_usage()` utility
   - Impact: Low - already extracted to common function

### Missing Features (Future Enhancements)

1. **Runner health checks** - Periodic validation that CLIs still work
2. **Fallback chains** - Try Codex, if fails use Claude
3. **Cost tracking** - Aggregate token usage across runners
4. **Performance metrics** - Track execution time per runner
5. **Concurrent runner support** - Run multiple agents in parallel (future optimization)

**Assessment:** Current design can support all these without refactoring

## Recommendations

### No Changes Needed to Architecture

The existing architecture **already supports** all task requirements:

✓ Multiple LLM backends (Claude, Codex, Gemini)
✓ Per-agent runner selection
✓ Agent variants (e.g., playwright)
✓ Configuration via environment variables
✓ Extensibility for new runners
✓ Backwards compatibility
✓ Fail-fast validation

**What needs work is implementation quality, not architecture.**

### Focus Areas for Task

1. **Fix Gemini runner implementation** - Add missing features (file tracking, skill loading)
2. **Validate Codex runner** - Test with actual CLI, fix any discovered issues
3. **Add integration tests** - Verify runners work with orchestrator
4. **Document setup** - How to install and configure each CLI
5. **Add validation scripts** - Quick health checks for each runner

**None of these require architectural changes.**

### Anti-Recommendations

**Do NOT:**
- Refactor registry to use async/await (not needed)
- Add complex fallback logic (YAGNI)
- Implement runner pooling (premature optimization)
- Create plugin system (overkill)
- Add circuit breakers (not needed for local CLIs)

**Why:** Current design is appropriate for the problem. More complexity would be detrimental.

## Conclusion

The runner architecture is **well-designed and production-ready**. It demonstrates good software engineering principles:

- **Single Responsibility** - Each component has one clear job
- **Open/Closed** - Open for extension (new runners), closed for modification
- **Liskov Substitution** - All runners interchangeable via interface
- **Dependency Inversion** - Orchestrator depends on abstraction, not concrete runners

**No architectural changes are needed.** The task should focus on:
1. Fixing implementation bugs (Gemini)
2. Validating assumptions (Codex)
3. Adding tests
4. Improving documentation

The foundation is solid. Build on it, don't rebuild it.
