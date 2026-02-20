# API Contract: Runner Interface

**Type:** Python Interface (ABC)
**Module:** `saha.runners.base`
**Status:** Existing (Validating compliance)

## Overview

The Runner interface is the core abstraction that enables multi-platform support. All LLM backend runners (Claude Code, Codex CLI, Gemini CLI) must implement this interface to be compatible with the orchestrator.

This contract ensures consistent behavior across platforms while allowing platform-specific implementations.

## Interface Definition

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from pydantic import BaseModel

class RunnerContext(BaseModel):
    """Context passed to agent execution.

    This structured context is serialized and passed to the agent
    (typically injected into the prompt or agent spec).
    """
    task_path: Path | None = None
    """Path to task directory containing artifacts"""

    iteration: int | None = None
    """Current iteration number in execution loop"""

    files_changed: list[str] | None = None
    """Files modified in previous iteration (for context)"""

    fix_info: str | None = None
    """Specific guidance from QA agent on what to fix"""

    phase: str | None = None
    """Current phase name from implementation plan"""

    def to_prompt_context(self) -> str:
        """Convert to human-readable context for injection into prompts."""
        parts = []
        if self.task_path:
            parts.append(f"Task: {self.task_path}")
        if self.iteration is not None:
            parts.append(f"Iteration: {self.iteration}")
        if self.phase:
            parts.append(f"Phase: {self.phase}")
        if self.files_changed:
            parts.append(f"Files changed: {', '.join(self.files_changed)}")
        if self.fix_info:
            parts.append(f"Fix needed:\n{self.fix_info}")
        return "\n".join(parts)

class Runner(ABC):
    """Abstract base class for LLM backend runners."""

    @abstractmethod
    def run_agent(
        self,
        agent_spec_path: Path,
        prompt: str,
        context: RunnerContext | None = None,
        timeout: int = 300,
    ) -> RunnerResult:
        """Run an agent-style prompt with agent spec.

        Args:
            agent_spec_path: Path to agent specification markdown file
                            (contains system prompt and behavior instructions)
            prompt: The user prompt to send to the agent
            context: Structured context to pass to agent
                    (task path, iteration number, changed files, etc.)
            timeout: Maximum execution time in seconds

        Returns:
            RunnerResult with success status, output, and structured_output

        Raises:
            RunnerError: If execution fails in non-recoverable way
            TimeoutError: If execution exceeds timeout
        """
        pass

    @abstractmethod
    def run_prompt(
        self,
        prompt: str,
        system_prompt: str | None = None,
        timeout: int = 300,
    ) -> RunnerResult:
        """Run a simple prompt without agent spec.

        Args:
            prompt: The user prompt to send
            system_prompt: Optional system instructions
            timeout: Maximum execution time in seconds

        Returns:
            RunnerResult with success status and output

        Raises:
            RunnerError: If execution fails
            TimeoutError: If execution exceeds timeout
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this runner is available on the system.

        Returns:
            True if CLI is installed and accessible, False otherwise

        Note:
            Should NOT raise exceptions - return False if unavailable
            Should log debug message if CLI not found
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get human-readable name of this runner.

        Returns:
            Runner name (e.g., "claude-code (sonnet)", "codex (o3)")
        """
        pass
```

## Usage Examples

### Creating Typed Context

```python
from pathlib import Path

# Type-safe context creation
context = RunnerContext(
    task_path=Path("docs/tasks/task-01-support"),
    iteration=2,
    files_changed=["saha/runners/codex.py"],
    fix_info="Fix timeout handling in run_agent method"
)

# Use in runner call
result = runner.run_agent(
    agent_spec_path=Path("agents/execution_implementer.md"),
    prompt="Implement the fix",
    context=context,
)
```

### Type-Safe Token Usage

```python
# Runners return typed token usage
result = runner.run_agent(...)

if result.token_usage:
    # IDE knows these fields exist
    print(f"Input tokens: {result.token_usage.input_tokens}")
    print(f"Output tokens: {result.token_usage.output_tokens}")
    print(f"Total: {result.token_usage.total_tokens}")

# Create token usage from CLI output
token_usage = TokenUsage(
    input_tokens=1500,
    output_tokens=800,
    total_tokens=2300
)
```

### Validating Agent Output

```python
from saha.agents.contracts import ImplementerOutput

result = runner.run_agent(...)

if result.structured_output:
    # Parse and validate
    output = ImplementerOutput.model_validate(result.structured_output)

    # Type-safe access
    for file in output.files_changed:
        update_file_tracker(file)

    if output.status == "success":
        proceed_to_qa()
```

## Return Type: RunnerResult

```python
from dataclasses import dataclass
from typing import Any
from pydantic import BaseModel

class TokenUsage(BaseModel):
    """Token usage statistics from LLM API."""
    input_tokens: int
    output_tokens: int
    total_tokens: int

@dataclass
class RunnerResult:
    """Result from runner execution."""

    success: bool
    """Whether execution succeeded"""

    output: str
    """Raw text output from runner"""

    structured_output: dict[str, Any] | None = None
    """Parsed JSON output from agent (if any)

    NOTE: For typed access, use the Pydantic models defined in
    02-agent-output-contracts.md (AgentOutput, ImplementerOutput, etc.)
    """

    error: str | None = None
    """Error message if execution failed"""

    tokens_used: int = 0
    """Total token count (simple count, inferred from token_usage if not provided)"""

    token_usage: TokenUsage | None = None
    """Detailed token usage stats (if available from CLI)"""

    exit_code: int = 0
    """Process exit code (0 = success)"""

    @classmethod
    def success_result(
        cls,
        output: str,
        structured_output: dict[str, Any] | None = None,
        tokens_used: int | None = None,
        token_usage: TokenUsage | None = None,
    ) -> "RunnerResult":
        """Create successful result."""
        if tokens_used is None and token_usage:
            tokens_used = token_usage.total_tokens
        if tokens_used is None:
            tokens_used = 0
        return cls(
            success=True,
            output=output,
            structured_output=structured_output,
            tokens_used=tokens_used,
            token_usage=token_usage,
        )

    @classmethod
    def failure(cls, error: str, exit_code: int = 1) -> "RunnerResult":
        """Create failed result."""
        return cls(
            success=False,
            output="",
            error=error,
            exit_code=exit_code,
        )
```

## Implementation Requirements

### Must Have

All runners MUST implement:
1. **run_agent()** - Execute agent with spec file
2. **run_prompt()** - Execute simple prompt
3. **is_available()** - Check CLI availability (no exceptions)
4. **get_name()** - Return descriptive name

### Should Have

Runners SHOULD provide:
1. **structured_output** - Parse JSON from output (enables orchestrator to read agent results)
2. **token_usage** / **tokens_used** - Track API usage (if CLI provides it)

**Note:** File tracking (`files_changed`, `files_added`) is NOT part of `RunnerResult`. It's handled separately:
- Via `structured_output` (agents return file lists in JSON)
- Via filesystem snapshots (Codex/Gemini) - see [CLI Integration Patterns](03-cli-integration-patterns.md#file-change-tracking-strategies)

### Platform-Specific Behavior

Runners MAY differ in:
- **Agent spec handling**: Native (Claude) vs embedded in prompt (Codex/Gemini)
- **Tool tracking**: Built-in metadata (Claude) vs filesystem snapshots (Codex/Gemini)
- **Skill loading**: Native (Claude) vs manual injection (Codex/Gemini)
- **Interactive mode**: Different flags for non-interactive execution

## Compliance Validation

To validate runner compliance with this contract:

```python
def test_runner_interface_compliance(runner: Runner):
    """Verify runner implements interface correctly."""
    # Must implement all methods
    assert hasattr(runner, "run_agent")
    assert hasattr(runner, "run_prompt")
    assert hasattr(runner, "is_available")
    assert hasattr(runner, "get_name")

    # is_available() must not raise
    try:
        available = runner.is_available()
        assert isinstance(available, bool)
    except Exception as e:
        pytest.fail(f"is_available() raised exception: {e}")

    # get_name() must return string
    name = runner.get_name()
    assert isinstance(name, str)
    assert len(name) > 0
```

## Error Handling Contract

### Recoverable Errors

Return `RunnerResult(success=False, error="...")` for:
- CLI not found (is_available() returns False)
- Invalid API key / authentication failure
- Agent execution timeout
- Invalid agent spec format
- Parse errors in output

### Non-Recoverable Errors

Raise exceptions for:
- Programming errors (invalid arguments)
- System failures (out of memory, disk full)
- Unexpected state (should never happen)

## Implementation Files

### Core Models
- `saha/runners/base.py` - `Runner` ABC, `RunnerResult`, `RunnerContext`, `TokenUsage`
- `saha/agents/contracts.py` - All agent output Pydantic models (see [02-agent-output-contracts.md](02-agent-output-contracts.md))

### Runner Implementations
- `saha/runners/claude.py` - Reference implementation (already compliant)
- `saha/runners/codex.py` - To validate against this contract (US-001)
- `saha/runners/gemini.py` - To fix and validate (US-002)

## Related

- **Stories:** US-001 (Codex validation), US-002 (Gemini fixes)
- **Research:** [01-codex-runner-analysis.md](../research/01-codex-runner-analysis.md)
- **Contracts:** [02-agent-output-contracts.md](02-agent-output-contracts.md)
