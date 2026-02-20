# Integration Test Spec: Runner Interface Compliance

**Related:** US-001, US-002, [01-runner-interface.md](../../api-contracts/01-runner-interface.md)
**Priority:** Critical
**Status:** Draft

## Overview

Tests validating that all runners (Claude, Codex, Gemini) correctly implement the Runner ABC interface and return properly formatted RunnerResult objects.

## Dependencies

- Authenticated container fixture
- Runner implementations (ClaudeRunner, CodexRunner, GeminiRunner)
- Real CLIs installed in container

## Test Cases

### TC-INT-010: Runner Implements All ABC Methods

**Description:** Verify all runners implement required abstract methods from Runner ABC.

**Input:**
```python
runners = [
    ClaudeRunner(),
    CodexRunner(),
    GeminiRunner(),
]
```

**Expected:**
- All runners have `run_agent()` method
- All runners have `run_prompt()` method
- All runners have `is_available()` method
- All runners have `get_name()` method
- All methods have correct signatures

**Assertions:**
```python
@pytest.mark.parametrize("runner_class", [ClaudeRunner, CodexRunner, GeminiRunner])
def test_runner_implements_interface(runner_class):
    runner = runner_class()

    assert hasattr(runner, "run_agent")
    assert callable(runner.run_agent)

    assert hasattr(runner, "run_prompt")
    assert callable(runner.run_prompt)

    assert hasattr(runner, "is_available")
    assert callable(runner.is_available)

    assert hasattr(runner, "get_name")
    assert callable(runner.get_name)

    # Verify signatures
    import inspect
    sig = inspect.signature(runner.run_agent)
    assert "agent_spec_path" in sig.parameters
    assert "prompt" in sig.parameters
    assert "context" in sig.parameters
    assert "timeout" in sig.parameters
```

---

### TC-INT-011: is_available() Never Raises Exceptions

**Description:** Verify `is_available()` returns boolean without raising exceptions, even when CLI unavailable.

**Input:**
- Call `is_available()` with CLI not installed
- Call `is_available()` with CLI installed

**Expected:**
- Returns `False` when CLI unavailable
- Returns `True` when CLI available
- Never raises exceptions
- Logs debug message when unavailable

**Assertions:**
```python
@pytest.mark.parametrize("runner_class", [ClaudeRunner, CodexRunner, GeminiRunner])
def test_is_available_no_exceptions(runner_class, caplog):
    runner = runner_class()

    # Should not raise even if CLI missing
    try:
        available = runner.is_available()
        assert isinstance(available, bool)
    except Exception as e:
        pytest.fail(f"is_available() raised exception: {e}")

    # If unavailable, should log debug message
    if not available:
        assert "not found" in caplog.text.lower() or "not available" in caplog.text.lower()
```

---

### TC-INT-012: get_name() Returns Non-Empty String

**Description:** Verify `get_name()` returns descriptive runner name.

**Expected:**
- Returns string
- String is non-empty
- String identifies runner and model

**Assertions:**
```python
@pytest.mark.parametrize("runner_class,expected_substring", [
    (ClaudeRunner, "claude"),
    (CodexRunner, "codex"),
    (GeminiRunner, "gemini"),
])
def test_get_name(runner_class, expected_substring):
    runner = runner_class()
    name = runner.get_name()

    assert isinstance(name, str)
    assert len(name) > 0
    assert expected_substring.lower() in name.lower()
```

---

### TC-INT-013: Codex Runner with Agent Spec

**Description:** Validate Codex runner works with real agent spec file.

**Setup:**
- Agent spec: `claude_plugin/agents/execution_implementer.md`
- Authenticated container with Codex CLI

**Input:**
```python
agent_spec = Path("claude_plugin/agents/execution_implementer.md")
prompt = "Implement a simple hello() function that returns 'Hello, World!'"
context = {"task_path": "/tmp/test-task"}
```

**Expected:**
- Runner executes successfully
- Returns RunnerResult with `success: True`
- Output is non-empty
- Agent spec content embedded in prompt sent to CLI

**Assertions:**
```python
runner = CodexRunner(working_dir=Path("/tmp/test"))
result = runner.run_agent(
    agent_spec_path=agent_spec,
    prompt=prompt,
    context=context,
    timeout=120
)

assert result.success
assert result.output
assert result.exit_code == 0
assert isinstance(result.structured_output, dict) or result.structured_output is None
```

---

### TC-INT-014: Codex Skill Loading

**Description:** Verify Codex runner loads and injects skills from `.claude/skills/`.

**Setup:**
- Create test skill file: `.claude/skills/test-skill.md`
- Agent spec that references the skill

**Input:**
```python
# .claude/skills/test-skill.md content
"""
# Test Skill
This is a test skill for validation.
"""

prompt = "Use the test-skill to do something"
```

**Expected:**
- Skill file loaded from `.claude/skills/`
- Skill content injected into prompt sent to Codex
- Runner executes without error

**Assertions:**
```python
runner = CodexRunner(working_dir=Path("/tmp/test"))

# Mock or spy on _build_command to verify skill injection
with mock.patch.object(runner, "_build_command") as mock_build:
    runner.run_agent(agent_spec, prompt)

    # Verify skills were embedded in the command
    called_prompt = mock_build.call_args[0][0]
    assert "# Test Skill" in called_prompt
    assert "test skill for validation" in called_prompt
```

---

### TC-INT-015: Codex File Change Tracking

**Description:** Verify Codex runner correctly identifies changed and added files.

**Setup:**
- Test project with existing file: `src/existing.py`
- Agent task: Modify `existing.py` and create `src/new.py`

**Input:**
```python
# Before execution
project_dir = Path("/tmp/test-project")
(project_dir / "src").mkdir(parents=True)
(project_dir / "src" / "existing.py").write_text("# Old content")

prompt = "Modify src/existing.py and create src/new.py"
```

**Expected:**
- File tracking identifies `src/existing.py` as changed
- File tracking identifies `src/new.py` as added
- RunnerResult or structured_output contains file lists

**Assertions:**
```python
runner = CodexRunner(working_dir=project_dir)
result = runner.run_agent(agent_spec, prompt)

# File tracking via structured output or separate mechanism
if result.structured_output:
    files_changed = result.structured_output.get("files_changed", [])
    files_added = result.structured_output.get("files_added", [])
else:
    # Use filesystem snapshot diff
    files_changed, files_added = runner._detect_file_changes()

assert "src/existing.py" in files_changed
assert "src/new.py" in files_added
```

---

### TC-INT-016: Codex CLI Not Installed

**Description:** Verify Codex runner handles missing CLI gracefully.

**Setup:**
- Container without Codex CLI installed
- `which codex` returns non-zero

**Expected:**
- `is_available()` returns `False`
- Debug message logged: "Codex CLI not found in PATH"
- No exception raised

**Assertions:**
```python
runner = CodexRunner()

# Ensure CLI not available
assert subprocess.run(["which", "codex"]).returncode != 0

# Verify is_available() behavior
available = runner.is_available()
assert available is False

# Attempting to run should return error result
result = runner.run_prompt("test")
assert not result.success
assert "not found" in result.error.lower() or "not available" in result.error.lower()
```

---

### TC-INT-017: Codex API Key Invalid

**Description:** Verify clear error message when Codex API key is invalid or expired.

**Setup:**
- Set `OPENAI_API_KEY` to invalid value
- Attempt to run agent

**Expected:**
- RunnerResult with `success: False`
- Error message mentions authentication failure
- Error message is actionable

**Assertions:**
```python
import os
os.environ["OPENAI_API_KEY"] = "invalid-key-12345"

runner = CodexRunner(working_dir=Path("/tmp/test"))
result = runner.run_prompt("Say hello")

assert not result.success
assert result.error
assert any(keyword in result.error.lower() for keyword in [
    "auth", "authentication", "api key", "invalid", "unauthorized"
])
```

---

### TC-INT-018: Gemini --yolo Flag Removed

**Description:** Verify Gemini runner no longer uses non-existent `--yolo` flag.

**Setup:**
- Gemini runner instance
- Spy on command building

**Expected:**
- `--yolo` NOT present in CLI command
- Command uses correct Gemini flags

**Assertions:**
```python
runner = GeminiRunner(working_dir=Path("/tmp/test"))

# Spy on subprocess.run to capture actual command
with mock.patch("subprocess.run") as mock_run:
    mock_run.return_value = mock.Mock(returncode=0, stdout="Test output")

    runner.run_prompt("test prompt")

    # Verify command doesn't include --yolo
    called_command = mock_run.call_args[0][0]
    assert "--yolo" not in called_command
```

---

### TC-INT-019: Gemini File Change Tracking

**Description:** Verify Gemini runner now has file change tracking (bug fixed).

**Setup:**
- Test project with files
- Agent task modifies files

**Expected:**
- File tracking class exists
- Changed files detected correctly
- Added files detected correctly

**Assertions:**
```python
runner = GeminiRunner(working_dir=Path("/tmp/test-project"))

# Verify file tracker exists
assert hasattr(runner, "_file_tracker") or hasattr(runner, "_FileChangeTracker")

# Run agent that modifies files
result = runner.run_agent(agent_spec, "Modify src/file.py")

# Verify file changes tracked
assert result.structured_output or hasattr(runner, "_detect_file_changes")
```

---

### TC-INT-020: Gemini Skill Loading

**Description:** Verify Gemini runner now loads skills (bug fixed).

**Setup:**
- Skill files in `.claude/skills/`
- Agent spec references skills

**Expected:**
- Skills loaded from directory
- Skills embedded in prompt
- Runner doesn't crash

**Assertions:**
```python
runner = GeminiRunner(working_dir=Path("/tmp/test"))

# Verify skill loading methods exist
assert hasattr(runner, "_load_skills") or hasattr(runner, "_embed_skills")

# Verify skills are actually loaded
with mock.patch.object(runner, "_build_command") as mock_build:
    runner.run_agent(agent_spec, prompt)

    called_prompt = mock_build.call_args[0][0]
    # Should contain skill content
    assert len(called_prompt) > len(agent_spec.read_text())
```

---

## Parameterized Test Coverage

```python
@pytest.mark.parametrize("runner_class,cli_name", [
    pytest.param(ClaudeRunner, "claude", marks=pytest.mark.claude),
    pytest.param(CodexRunner, "codex", marks=pytest.mark.codex),
    pytest.param(GeminiRunner, "gemini", marks=pytest.mark.gemini),
])
class TestRunnerCompliance:
    """Compliance tests for all runners."""

    def test_implements_interface(self, runner_class):
        ...

    def test_is_available_behavior(self, runner_class, cli_name):
        ...

    def test_run_prompt_returns_runner_result(self, runner_class):
        ...

    def test_run_agent_returns_runner_result(self, runner_class):
        ...
```

## Test Organization

**File:** `tests/integration/runners/test_runner_compliance.py`

**Markers:**
- `@pytest.mark.integration`
- `@pytest.mark.claude` / `@pytest.mark.codex` / `@pytest.mark.gemini`
- `@skipif_no_<runner>`

## Related

- **Stories:** [US-001](../../user-stories/US-001-validate-codex-runner.md), [US-002](../../user-stories/US-002-fix-gemini-runner.md)
- **Contracts:** [01-runner-interface.md](../../api-contracts/01-runner-interface.md)
- **Research:** [01-codex-runner-analysis.md](../../research/01-codex-runner-analysis.md), [02-gemini-runner-analysis.md](../../research/02-gemini-runner-analysis.md)
