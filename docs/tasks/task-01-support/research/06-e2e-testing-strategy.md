# Research: E2E Testing Strategy with Real Runners

**Date:** 2026-02-12
**Status:** Complete
**Focus:** Validating multi-platform support with real Claude Code, Codex, and Gemini CLI runners

## Summary

The user's proposal to use an "eval" approach with real runners is **fundamentally sound but needs significant refinement**. The existing test infrastructure provides a strong foundation, but critical gaps exist: no tests use real runners, verification strategies are too simple, and CI integration requirements are underspecified.

**Key Finding:** The codebase has excellent integration test patterns (IntelligentMockRunner, testcontainers, sample projects) but **zero tests with real CLI runners**. This is the validation gap that must be closed.

## User's Proposal: Critical Analysis

### What Works

1. **"Eval" approach is correct** - Small test project + feature implementation + automated verification is exactly right
2. **Test both planning modes** - Good scope, validates full system
3. **Local-first strategy** - Smart: validate locally before CI complexity
4. **Simple feature scope** - 5-10 min task is appropriate complexity

### What Needs Refinement

1. **"From scratch" is too ambitious** - Better: minimal pre-existing project with basic structure
2. **"Automated eval" is underspecified** - Need clear verification criteria, not just "does it work"
3. **No failure scenarios** - Tests should cover both success AND expected failure modes
4. **Missing runner isolation** - How to ensure tests don't interfere with each other
5. **No comparison strategy** - Should outputs be identical across runners? How to verify equivalence?

## Current Testing Landscape

### Existing Test Infrastructure (Evidence: `tests/integration/`)

**What We Have:**

1. **IntelligentMockRunner** (`saha/runners/intelligent_mock.py:1-404`)
   - Simulates LLM behavior by reading task artifacts
   - Makes actual code changes when configured
   - Produces correct structured outputs
   - Tracks call history for assertions
   - **Used in:** `test_agentic_loop_e2e.py`, `test_agentic_loop_local.py`

2. **Testcontainers Integration** (`tests/integration/conftest.py:1-241`)
   - Spins up Debian containers for isolated testing
   - Bootstraps full Sahaidachny environment
   - Copies project files into container
   - Runs Python code in isolated environment
   - **Used in:** `test_e2e.py`, `test_agentic_loop_e2e.py`

3. **Sample Project Fixtures** (`tests/integration/conftest.py:141-241`)
   - `sample_python_project`: Project with intentional issues for tool testing
   - `clean_python_project`: Passing project for happy path testing
   - Inline task definitions in test files (SAMPLE_TASK_FILES pattern)
   - **Pattern:** Dict of `{path: content}` for easy project construction

4. **Test Scenarios Covered** (`test_agentic_loop_e2e.py:153-733`)
   - Full loop execution (implementation → qa → quality → manager → dod)
   - QA failure and recovery (retries with fix_info)
   - Code quality failure recovery
   - State persistence and resumption
   - Max iterations limit
   - Context passing to agents
   - Hook triggering at correct points

**What We DON'T Have:**

1. **Zero tests with real runners** - All tests use MockRunner or IntelligentMockRunner
2. **No runner availability checks** - Tests don't skip if CLI not installed
3. **No runner comparison tests** - No verification that Codex/Gemini produce equivalent outputs to Claude
4. **No credential management** - No patterns for API keys, auth tokens
5. **No test project templates** - Sample projects are inline, not reusable fixtures

### Test Organization Patterns

```
tests/
├── integration/
│   ├── conftest.py                    # Fixtures: containers, sample projects
│   ├── test_agentic_loop_e2e.py       # Full loop with testcontainers
│   ├── test_agentic_loop_local.py     # Full loop without containers
│   ├── test_e2e.py                    # End-to-end scenarios
│   ├── test_codex_runner.py           # Unit tests for Codex runner
│   ├── test_orchestrator.py           # Orchestrator tests
│   ├── test_hooks.py                  # Hook system tests
│   ├── test_state.py                  # State persistence tests
│   └── test_tools.py                  # Tool integration tests
└── [No unit/ directory exists]
```

**Pattern:** Integration tests preferred over unit tests (matches user's philosophy in CLAUDE.md)

## Validation Questions: Answers

### 1. Existing Testing Patterns

**Q: What e2e/integration tests already exist?**

**A:** Extensive integration tests exist (`tests/integration/`):
- 15 test files covering orchestrator, state, hooks, tools, runners
- Full agentic loop tests with testcontainers
- Local loop tests without Docker
- Tool integration tests (ruff, pytest, complexity)

**Q: How are they structured?**

**A:** Two-tier structure:
- **Containerized tests** (`test_e2e.py`, `test_agentic_loop_e2e.py`): Use testcontainers + tarball deployment
- **Local tests** (`test_agentic_loop_local.py`): Use temp directories + IntelligentMockRunner

**Q: Do any tests use real runners?**

**A:** **No.** All tests use MockRunner or IntelligentMockRunner. This is the critical validation gap.

**Q: What testing frameworks/fixtures are used?**

**A:**
- pytest (with fixtures, parametrization)
- testcontainers (for Debian container isolation)
- IntelligentMockRunner (for simulating LLM behavior)
- Inline sample projects (dict-based fixtures)

### 2. Eval Approach Validation

**Q: Is the "eval" approach sound?**

**A:** **Yes, but needs refinement.**

**Sound aspects:**
- Small test project + feature implementation + verification is proven pattern
- Matches existing test structure (SAMPLE_TASK_FILES + SAMPLE_PROJECT_FILES)
- Automated verification via pytest is correct approach

**Needs refinement:**
- "From scratch" → Use minimal pre-existing project (avoids bootstrap complexity)
- "Automated eval" → Need specific verification criteria (not just "does it pass")
- Add failure scenarios (not just happy path)

**Q: What makes a good test project?**

**A:** Based on existing patterns (`test_agentic_loop_e2e.py:22-150`):

**Good characteristics:**
- **Minimal but realistic:** Basic Python package with `__init__.py`, one module, tests
- **Clear target file:** Explicit file path in task description (e.g., `sample_project/utils.py`)
- **Verifiable changes:** Code changes can be verified programmatically
- **Existing tests:** Can run pytest to verify feature works
- **Pre-existing structure:** Don't create from scratch, extend existing project

**Example (from existing tests):**
```
sample_project/
├── __init__.py
├── main.py              # Existing code
└── utils.py             # Target for new feature
tests/
├── __init__.py
└── test_utils.py        # Tests for new feature
pyproject.toml           # Pytest config
```

**Q: What's a good simple feature?**

**A:** Based on existing patterns:

**Good feature characteristics:**
- **2-3 functions:** Not too small (trivial) or large (takes too long)
- **Type hints required:** Forces code quality checks
- **Testable:** Can verify with pytest
- **Clear acceptance criteria:** Unambiguous success conditions

**Example from existing tests:**
```markdown
# Task: Add String Utilities

## Requirements
- Add `reverse_string(s: str) -> str` function
- Add `capitalize_words(s: str) -> str` function
- Add type hints and docstrings
- Add tests with 80%+ coverage

## Target File
`sample_project/utils.py`

## Acceptance Criteria
- [ ] reverse_string("hello") returns "olleh"
- [ ] capitalize_words("hello world") returns "Hello World"
- [ ] All tests pass
- [ ] Ruff check passes
- [ ] Type checking passes
```

**Time estimate:** 5-10 minutes for Claude Code (matches user's target)

**Q: How to verify success?**

**A:** Multi-level verification (learned from existing tests):

**Level 1: Process success**
- Runner returns `success=True`
- Exit code is 0
- No error messages

**Level 2: Artifact verification**
- Target file exists
- Target file contains expected functions
- Functions have type hints
- Functions have docstrings

**Level 3: Functional verification**
- Tests pass (`pytest`)
- Code quality passes (`ruff check`)
- Type checking passes (if applicable)
- Complexity acceptable (`complexipy`)

**Level 4: Structured output verification**
- `files_changed` or `files_added` contains target file
- `dod_achieved` is True (for QA agent)
- `quality_passed` is True (for code quality agent)
- `task_complete` is True (for DoD agent)

**Example assertion pattern:**
```python
# Process success
assert result.success
assert result.exit_code == 0

# Artifact verification
target = Path("sample_project/utils.py")
assert target.exists()
content = target.read_text()
assert "def reverse_string(s: str) -> str:" in content
assert '"""' in content  # Has docstring

# Functional verification
pytest_result = subprocess.run(["pytest", "tests/"], capture_output=True)
assert pytest_result.returncode == 0

ruff_result = subprocess.run(["ruff", "check", "sample_project/"], capture_output=True)
assert ruff_result.returncode == 0

# Structured output verification
assert "utils.py" in result.structured_output.get("files_changed", [])
```

### 3. Test Scenarios

**Q: Planning phase - what to test?**

**A:** Planning phase is **out of scope** for this e2e testing strategy. Reasons:

1. **Task description states:** "Codex and Gemini CLI... don't work" in execution phase
2. **Planning is Claude plugin dependent:** Planning commands (`/saha:init`, `/saha:stories`) are Claude Code skills
3. **Execution is the priority:** Multi-platform support for agentic loop is the real requirement
4. **Complexity explosion:** Planning tests would require testing skill loading across platforms

**Recommendation:** Focus on **execution phase only**. Planning validation is separate task.

**Q: Execution phase - what to test?**

**A:** Based on agentic loop flow (`saha/orchestrator/loop.py:55-69`):

**Phase 1: Implementation** (`execution-implementer` agent)
- Runner can invoke agent with agent spec + prompt + context
- Files are created/modified correctly
- Structured output includes `files_changed` and `files_added`
- Token usage is tracked (or gracefully fails)

**Phase 2: Test Critique** (`execution-test-critique` agent)
- Optional: Only if test-critique enabled
- Can identify hollow tests
- Produces `critique_passed` and `test_quality_score`

**Phase 3: QA** (`execution-qa` agent)
- Can run pytest and verify tests pass
- Produces `dod_achieved` (True/False)
- Produces `fix_info` on failure
- Correctly handles retry loop (implementation → qa → implementation)

**Phase 4: Code Quality** (`execution-code-quality` agent)
- Can run ruff, ty, complexipy tools
- Produces `quality_passed` (True/False)
- Produces `fix_info` with specific issues
- Correctly handles retry loop

**Phase 5: Manager** (`execution-manager` agent)
- Updates task status in user-stories/*.md
- Produces `status: success`
- Actually modifies files (mark acceptance criteria as done)

**Phase 6: DoD** (`execution-dod` agent)
- Checks task completion based on artifacts
- Produces `task_complete` (True/False)
- Produces summary statistics

**Q: What edge cases matter?**

**A:**

**Critical edge cases:**
1. **QA failure loop:** Implementation → QA (fail) → Implementation (with fix_info) → QA (pass)
2. **Quality failure loop:** Same pattern but for code quality
3. **Max iterations:** Loop terminates at max_iterations even if incomplete
4. **Timeout:** Runner times out gracefully (returns error, doesn't hang)
5. **CLI not installed:** Runner.is_available() returns False, test skips
6. **Malformed output:** Runner handles non-JSON output without crashing

**Ignore for now:**
- Planning phase failures (out of scope)
- Network errors (too flaky for local tests)
- Credential expiration (manual test only)

### 4. Local Runner Setup

**Q: How to ensure CLIs are available locally?**

**A:** Use pytest skip patterns (standard approach):

```python
import pytest
import shutil

# Skip marker for Codex tests
codex_available = shutil.which("codex") is not None
skipif_no_codex = pytest.mark.skipif(
    not codex_available,
    reason="Codex CLI not installed. Install: npm install -g @openai/codex"
)

# Skip marker for Gemini tests
gemini_available = shutil.which("gemini") is not None
skipif_no_gemini = pytest.mark.skipif(
    not gemini_available,
    reason="Gemini CLI not installed. Install: npm install -g @google/gemini-cli"
)

# Usage
@skipif_no_codex
def test_codex_implementation():
    runner = CodexRunner()
    assert runner.is_available()
    # ... test logic
```

**Installation check script:**
```bash
# scripts/check-runner-clis.sh
#!/bin/bash

echo "Checking runner CLI availability..."

if command -v claude &> /dev/null; then
    echo "✓ Claude Code CLI: $(claude --version)"
else
    echo "✗ Claude Code CLI: Not installed"
fi

if command -v codex &> /dev/null; then
    echo "✓ Codex CLI: $(codex --version)"
else
    echo "✗ Codex CLI: Not installed (npm install -g @openai/codex)"
fi

if command -v gemini &> /dev/null; then
    echo "✓ Gemini CLI: $(gemini --version)"
else
    echo "✗ Gemini CLI: Not installed (npm install -g @google/gemini-cli)"
fi
```

**Q: How to isolate test projects?**

**A:** Use existing temp directory pattern from `test_agentic_loop_local.py:156-165`:

```python
import tempfile
import shutil

@pytest.fixture
def temp_project():
    """Create isolated temporary project directory."""
    temp_dir = Path(tempfile.mkdtemp())

    # Create project structure
    create_sample_project(temp_dir)
    create_sample_task(temp_dir)

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)
```

**Key isolation patterns:**
- Fresh temp directory per test
- No shared state between tests
- Cleanup in fixture teardown
- Working directory isolation (each runner gets its own dir)

**Q: How to clean up after tests?**

**A:** Multi-level cleanup strategy:

**Level 1: Fixture cleanup (Python)**
```python
@pytest.fixture
def temp_project():
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)  # Always cleanup
```

**Level 2: Runner cleanup (Per-runner)**
```python
# CodexRunner: Clean session logs
def cleanup_codex_session(session_id: str):
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    session_dir = codex_home / "sessions" / session_id
    if session_dir.exists():
        shutil.rmtree(session_dir)

# ClaudeRunner: Clean .claude state (if created)
def cleanup_claude_state(working_dir: Path):
    claude_dir = working_dir / ".claude"
    if claude_dir.exists():
        shutil.rmtree(claude_dir)
```

**Level 3: Test artifacts cleanup (Post-test hook)**
```python
@pytest.fixture(autouse=True)
def cleanup_test_artifacts():
    """Auto-cleanup for all tests."""
    yield
    # Clean up any leftover files
    for pattern in ["*.tmp", "*.log", ".test_*"]:
        for file in Path.cwd().glob(pattern):
            file.unlink(missing_ok=True)
```

### 5. Verification Strategy

**Q: How to verify planning artifacts are correct?**

**A:** **Out of scope** (planning not tested in this strategy, only execution)

**Q: How to verify implementation worked?**

**A:** Three-tier verification (from most specific to most general):

**Tier 1: File-level verification**
```python
def verify_implementation(target_file: Path, expected_functions: list[str]):
    """Verify specific implementation details."""
    assert target_file.exists(), f"Target file not created: {target_file}"

    content = target_file.read_text()

    for func in expected_functions:
        assert f"def {func}" in content, f"Function {func} not found"

    # Check type hints present
    assert ": " in content and "->" in content, "Type hints missing"

    # Check docstrings present
    assert '"""' in content, "Docstrings missing"
```

**Tier 2: Test-based verification**
```python
def verify_tests_pass(project_dir: Path):
    """Verify pytest passes."""
    result = subprocess.run(
        ["pytest", str(project_dir / "tests"), "-q"],
        capture_output=True,
        timeout=60,
        cwd=project_dir,
    )
    assert result.returncode == 0, f"Tests failed: {result.stdout.decode()}"
```

**Tier 3: Quality-based verification**
```python
def verify_code_quality(project_dir: Path):
    """Verify code quality tools pass."""
    # Ruff
    ruff_result = subprocess.run(
        ["ruff", "check", str(project_dir)],
        capture_output=True,
    )
    assert ruff_result.returncode == 0, f"Ruff failed: {ruff_result.stdout.decode()}"

    # Type checking (optional, may not be available)
    if shutil.which("mypy"):
        mypy_result = subprocess.run(
            ["mypy", str(project_dir / "sample_project")],
            capture_output=True,
        )
        # Note: Don't assert, just log (mypy config may vary)
        if mypy_result.returncode != 0:
            logger.warning(f"Mypy issues: {mypy_result.stdout.decode()}")
```

**Q: How to compare outputs across runners?**

**A:** **Outputs should NOT be identical** (different LLMs write different code). Instead, verify **equivalence**:

**What should be equivalent:**
- File structure (same files created/modified)
- Function signatures (same names, same type hints)
- Test outcomes (all tests pass)
- Code quality (all tools pass)
- Task completion (DoD achieved)

**What will differ:**
- Implementation details (algorithm choice, variable names)
- Output text (different explanation styles)
- Token usage (different models, different costs)
- Execution time (different performance)

**Equivalence verification pattern:**
```python
def verify_equivalence(result_claude, result_codex, result_gemini):
    """Verify outputs are functionally equivalent."""
    # File changes should be similar (not necessarily identical)
    claude_files = set(result_claude.structured_output.get("files_changed", []))
    codex_files = set(result_codex.structured_output.get("files_changed", []))
    gemini_files = set(result_gemini.structured_output.get("files_changed", []))

    # All runners should touch the same target file
    assert len(claude_files & codex_files & gemini_files) > 0, "No common files modified"

    # All should achieve DoD (this is the critical equivalence)
    assert result_claude.structured_output.get("task_complete") == True
    assert result_codex.structured_output.get("task_complete") == True
    assert result_gemini.structured_output.get("task_complete") == True

    # All should pass tests (functional equivalence)
    for result, name in [(result_claude, "Claude"), (result_codex, "Codex"), (result_gemini, "Gemini")]:
        assert result.success, f"{name}: Process failed"
        assert "tests pass" in result.output.lower(), f"{name}: Tests didn't pass"
```

**Note:** Don't compare outputs directly (text, code structure) - only verify functional equivalence.

### 6. Test Infrastructure Needs

**Q: What pytest fixtures would be needed?**

**A:** Based on existing patterns + new requirements:

**Fixture 1: Real runner instances**
```python
@pytest.fixture
def claude_runner(temp_project):
    """Claude Code runner with test configuration."""
    return ClaudeRunner(
        working_dir=temp_project,
        skip_permissions=True,  # Avoid permission prompts
        stream_output=False,    # Capture output, don't stream
    )

@pytest.fixture
def codex_runner(temp_project):
    """Codex runner with test configuration."""
    return CodexRunner(
        working_dir=temp_project,
        dangerously_bypass=True,  # Skip approvals in tests
    )

@pytest.fixture
def gemini_runner(temp_project):
    """Gemini runner with test configuration."""
    return GeminiRunner(
        working_dir=temp_project,
        yolo=True,  # Auto-accept tool calls (if flag exists)
    )
```

**Fixture 2: Test project templates**
```python
@pytest.fixture
def sample_python_project_with_task(temp_project):
    """Create complete project with task artifacts."""
    # Copy sample project
    create_sample_project(temp_project)

    # Copy task artifacts
    create_sample_task(temp_project)

    return temp_project
```

**Fixture 3: Agent specs (reusable)**
```python
@pytest.fixture
def agent_specs():
    """Paths to agent specification files."""
    agents_path = Path("claude_plugin/agents")
    return {
        "implementer": agents_path / "execution-implementer.md",
        "qa": agents_path / "execution-qa.md",
        "code_quality": agents_path / "execution-code-quality.md",
        "manager": agents_path / "execution-manager.md",
        "dod": agents_path / "execution-dod.md",
    }
```

**Fixture 4: Orchestrator factory**
```python
@pytest.fixture
def create_orchestrator():
    """Factory for creating configured orchestrators."""
    def _create(runner: Runner, working_dir: Path):
        settings = Settings(runner="custom")
        tools = create_default_registry()
        hooks = HookRegistry()
        state_manager = StateManager(working_dir / ".sahaidachny")

        return AgenticLoop(
            runner=runner,
            tool_registry=tools,
            hook_registry=hooks,
            state_manager=state_manager,
            settings=settings,
        )
    return _create
```

**Q: How to parameterize tests across runners?**

**A:** Use pytest parametrization with conditional skip:

```python
@pytest.mark.parametrize("runner_name,runner_factory", [
    pytest.param("claude", lambda: ClaudeRunner(), marks=skipif_no_claude),
    pytest.param("codex", lambda: CodexRunner(), marks=skipif_no_codex),
    pytest.param("gemini", lambda: GeminiRunner(), marks=skipif_no_gemini),
])
def test_implementation_agent(runner_name, runner_factory, temp_project, agent_specs):
    """Test implementation agent works across all runners."""
    runner = runner_factory()
    runner._working_dir = temp_project

    result = runner.run_agent(
        agent_spec_path=agent_specs["implementer"],
        prompt="Implement the string utilities as described in the task",
        context={"task_id": "test-task", "task_path": "docs/tasks/test-task"},
    )

    assert result.success, f"{runner_name}: Implementation failed"
    assert result.structured_output is not None, f"{runner_name}: No structured output"
    assert "files_changed" in result.structured_output or "files_added" in result.structured_output
```

**Q: How to make tests fast enough?**

**A:** Tests with real runners will be **slow by nature** (LLM calls take 30-60s each). Strategies:

**Strategy 1: Mark slow tests explicitly**
```python
@pytest.mark.slow
@pytest.mark.skipif_no_codex
def test_full_agentic_loop_codex():
    """Full loop test - slow, requires real Codex CLI."""
    # ... 5-10 minute test
```

**Strategy 2: Run only in CI or manually**
```bash
# Fast tests only (default)
pytest tests/

# Include slow tests
pytest tests/ -m slow

# Include real runner tests
pytest tests/ -m "real_runner"

# Specific runner
pytest tests/ -m codex
```

**Strategy 3: Timeout aggressively**
```python
@pytest.mark.timeout(300)  # 5 minute max
def test_implementation_codex():
    # If runner hangs, timeout kills it
```

**Strategy 4: Cache results for debugging**
```python
# Don't re-run slow tests if code unchanged
@pytest.mark.slow
@pytest.mark.flaky(reruns=0)  # Don't auto-retry on failure
def test_expensive_operation():
    # ... slow test
```

**Reality check:** Full loop tests with real runners will take **5-10 minutes each**. This is acceptable for:
- Manual validation runs
- Pre-merge CI checks
- Nightly CI runs

Not acceptable for:
- Fast feedback during development (use IntelligentMockRunner for that)
- Every commit (too slow)

**Q: Where should test projects live?**

**A:** Multiple locations for different purposes:

**Location 1: Inline definitions (for simple cases)**
```python
# tests/integration/test_runners_real.py
SIMPLE_TASK_FILES = {
    "docs/tasks/test-task/task-description.md": """...""",
    "sample_project/main.py": """...""",
}

def test_simple_feature(temp_project):
    for path, content in SIMPLE_TASK_FILES.items():
        (temp_project / path).write_text(content)
    # ... test logic
```

**Location 2: Fixtures directory (for reusable templates)**
```
tests/
├── fixtures/
│   ├── projects/
│   │   ├── simple-python/           # Minimal Python project
│   │   │   ├── project_files.py     # Dict of files
│   │   │   └── task_files.py        # Dict of task artifacts
│   │   ├── web-app/                 # More complex example
│   │   │   └── ...
│   │   └── README.md                # Documentation
│   └── conftest.py                  # Fixture loaders
```

```python
# tests/fixtures/conftest.py
def load_fixture_project(name: str) -> dict[str, str]:
    """Load a fixture project by name."""
    module = importlib.import_module(f"tests.fixtures.projects.{name}.project_files")
    return module.PROJECT_FILES
```

**Location 3: Temp directory generation (for isolation)**
```python
@pytest.fixture
def isolated_project(temp_project, request):
    """Create isolated project from fixture name."""
    fixture_name = request.param  # From parametrize
    files = load_fixture_project(fixture_name)

    for path, content in files.items():
        full_path = temp_project / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)

    return temp_project
```

**Recommendation:** Start with inline definitions (simpler), migrate to fixtures if reused across 3+ tests.

### 7. CI Considerations (Future)

**Q: What would it take to run these in CI later?**

**A:** Significant complexity, but achievable:

**Challenge 1: CLI installation**
```yaml
# .github/workflows/test-runners.yml
name: Test Real Runners

jobs:
  test-claude:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Claude Code CLI
        run: |
          # Claude Code installation (if public)
          # May require authentication
          curl -sSL https://claude.ai/cli/install.sh | bash

      - name: Run Claude tests
        run: pytest tests/ -m claude
```

**Challenge 2: Credential management**
```yaml
env:
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
```

**Challenge 3: Cost management**
- Real LLM calls cost money
- Need limits to avoid runaway costs
- Consider using smaller models for CI (e.g., claude-haiku instead of sonnet)

**Challenge 4: Flakiness**
- LLM outputs are non-deterministic
- Network failures happen
- Rate limits hit unexpectedly

**Mitigation strategies:**
- Run nightly instead of per-commit
- Use retry logic (pytest-rerunfailures)
- Skip on CI if secrets not available
- Use cost limits (e.g., OpenAI usage limits)

**Q: Mocking strategy for unavailable CLIs?**

**A:** **Already exists** - IntelligentMockRunner is the mock strategy.

**Current pattern:**
```python
# Local development: Mock runner (fast feedback)
if not runner.is_available():
    runner = IntelligentMockRunner(working_dir=project_dir)

# CI with secrets: Real runner (validation)
if has_credentials():
    runner = ClaudeRunner()
else:
    pytest.skip("Credentials not available")
```

**Don't mock the CLI** - either use real CLI or skip test. Mocking CLI outputs defeats the purpose of these tests.

**Q: Credential management for API access?**

**A:** Multi-level approach:

**Level 1: Environment variables**
```python
# tests/conftest.py
def get_runner_credentials():
    """Get credentials from environment."""
    return {
        "anthropic": os.environ.get("ANTHROPIC_API_KEY"),
        "openai": os.environ.get("OPENAI_API_KEY"),
        "google": os.environ.get("GOOGLE_API_KEY"),
    }

@pytest.fixture
def has_claude_credentials():
    """Check if Claude credentials available."""
    return get_runner_credentials()["anthropic"] is not None
```

**Level 2: CI secrets**
```yaml
# .github/workflows/test-runners.yml
env:
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

**Level 3: Skip if unavailable**
```python
@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set"
)
def test_claude_runner():
    # ... test
```

**Security:**
- Never log API keys
- Never commit credentials
- Use GitHub secrets for CI
- Consider using 1Password CLI for local dev

## Recommended Test Architecture

### Test Structure

```
tests/
├── integration/
│   ├── conftest.py                           # Shared fixtures
│   │
│   ├── runners/                              # NEW: Real runner tests
│   │   ├── conftest.py                       # Runner-specific fixtures
│   │   ├── test_claude_runner_real.py        # Claude CLI integration
│   │   ├── test_codex_runner_real.py         # Codex CLI integration
│   │   ├── test_gemini_runner_real.py        # Gemini CLI integration
│   │   └── test_runner_equivalence.py        # Cross-runner comparison
│   │
│   ├── test_agentic_loop_e2e.py              # EXISTING: Mock runner tests
│   ├── test_agentic_loop_local.py            # EXISTING: Local mock tests
│   └── ...
│
└── fixtures/                                 # NEW: Reusable test projects
    ├── projects/
    │   ├── simple-python/
    │   │   ├── project_files.py
    │   │   └── task_files.py
    │   └── README.md
    └── conftest.py
```

### Test Hierarchy (Priority Order)

**Tier 1: Smoke tests (per runner, ~2 min each)**
- Single agent invocation
- Verify basic functionality
- Check structured output format

**Tier 2: Loop tests (per runner, ~5-10 min each)**
- Full agentic loop execution
- Single iteration (implementation → qa → quality → manager → dod)
- Happy path only

**Tier 3: Retry tests (per runner, ~10-15 min each)**
- QA failure and recovery
- Code quality failure and recovery
- Verify fix_info passes correctly

**Tier 4: Equivalence tests (all runners, ~30-45 min)**
- Run same task on all three runners
- Verify functional equivalence (not code equivalence)
- Compare token usage, execution time

### Sample Test Implementation

```python
# tests/integration/runners/test_codex_runner_real.py

import pytest
import shutil
from pathlib import Path

from saha.runners.codex import CodexRunner
from saha.orchestrator.loop import AgenticLoop, LoopConfig
from saha.tools import create_default_registry
from saha.hooks import HookRegistry
from saha.orchestrator.state import StateManager
from saha.config.settings import Settings

# Skip markers
codex_available = shutil.which("codex") is not None
skipif_no_codex = pytest.mark.skipif(
    not codex_available,
    reason="Codex CLI not installed. Install: npm install -g @openai/codex"
)


@pytest.fixture
def codex_runner(temp_project):
    """Codex runner configured for testing."""
    return CodexRunner(
        working_dir=temp_project,
        dangerously_bypass=True,  # Skip approval prompts
    )


@pytest.fixture
def sample_task_files():
    """Simple feature implementation task."""
    return {
        "docs/tasks/string-utils/task-description.md": """# Add String Utilities

## Requirements
- Add `reverse_string(s: str) -> str` to `sample_project/utils.py`
- Add comprehensive tests to `tests/test_utils.py`
- Ensure all tests pass and code quality checks pass

## Target File
`sample_project/utils.py`

## Acceptance Criteria
- [ ] reverse_string("hello") returns "olleh"
- [ ] Empty strings handled correctly
- [ ] Type hints present
- [ ] Tests pass
- [ ] Ruff check passes
""",
        "docs/tasks/string-utils/README.md": "# String Utils Task",
        "docs/tasks/string-utils/user-stories/US-001.md": """# US-001: String Reversal

## Acceptance Criteria
- [ ] `reverse_string(s: str) -> str` function exists
- [ ] Function has docstring and type hints
- [ ] Tests pass
""",
    }


@pytest.fixture
def sample_project_files():
    """Minimal Python project structure."""
    return {
        "sample_project/__init__.py": "",
        "sample_project/main.py": """def add(a: int, b: int) -> int:
    return a + b
""",
        "tests/__init__.py": "",
        "tests/test_main.py": """from sample_project.main import add

def test_add():
    assert add(2, 3) == 5
""",
        "pyproject.toml": """[project]
name = "sample-project"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]
""",
    }


def create_project_files(base_dir: Path, files: dict[str, str]):
    """Create files in base directory from dict."""
    for path, content in files.items():
        full_path = base_dir / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)


@pytest.mark.slow
@skipif_no_codex
@pytest.mark.timeout(300)  # 5 minute timeout
class TestCodexRunnerReal:
    """Integration tests with real Codex CLI."""

    def test_codex_cli_available(self, codex_runner):
        """Verify Codex CLI is installed and available."""
        assert codex_runner.is_available(), "Codex CLI not available"
        assert "codex" in codex_runner.get_name().lower()

    def test_implementation_agent_basic(
        self, codex_runner, temp_project, sample_project_files, sample_task_files, agent_specs
    ):
        """Test implementation agent can be invoked and produces output."""
        # Setup project
        create_project_files(temp_project, sample_project_files)
        create_project_files(temp_project, sample_task_files)

        # Run implementation agent
        result = codex_runner.run_agent(
            agent_spec_path=agent_specs["implementer"],
            prompt="Implement the reverse_string function as described in the task",
            context={
                "task_id": "string-utils",
                "task_path": "docs/tasks/string-utils",
                "iteration": 1,
            },
        )

        # Verify process success
        assert result.success, f"Implementation failed: {result.error}"
        assert result.exit_code == 0

        # Verify structured output
        assert result.structured_output is not None
        assert "files_changed" in result.structured_output or "files_added" in result.structured_output

        # Verify artifact created
        target = temp_project / "sample_project" / "utils.py"
        assert target.exists(), "Target file not created"

        content = target.read_text()
        assert "def reverse_string" in content, "Function not found"
        assert "-> str" in content, "Type hint missing"

    def test_full_agentic_loop(
        self, codex_runner, temp_project, sample_project_files, sample_task_files
    ):
        """Test full agentic loop execution with Codex runner."""
        # Setup
        create_project_files(temp_project, sample_project_files)
        create_project_files(temp_project, sample_task_files)

        settings = Settings(runner="codex")
        tools = create_default_registry()
        hooks = HookRegistry()
        state_manager = StateManager(temp_project / ".sahaidachny")

        orchestrator = AgenticLoop(
            runner=codex_runner,
            tool_registry=tools,
            hook_registry=hooks,
            state_manager=state_manager,
            settings=settings,
        )

        config = LoopConfig(
            task_id="string-utils",
            task_path=temp_project / "docs/tasks/string-utils",
            max_iterations=3,
            enabled_tools=["ruff", "pytest"],
        )

        # Execute
        state = orchestrator.run(config)

        # Verify completion
        assert state.current_phase.value == "completed", f"Loop didn't complete: {state.current_phase.value}"
        assert state.current_iteration >= 1, "No iterations executed"

        # Verify target file
        target = temp_project / "sample_project" / "utils.py"
        assert target.exists(), "Implementation file not created"

        # Verify tests pass
        import subprocess
        test_result = subprocess.run(
            ["pytest", str(temp_project / "tests"), "-q"],
            capture_output=True,
            timeout=60,
        )
        assert test_result.returncode == 0, f"Tests failed: {test_result.stdout.decode()}"

        # Verify code quality
        ruff_result = subprocess.run(
            ["ruff", "check", str(temp_project / "sample_project")],
            capture_output=True,
        )
        assert ruff_result.returncode == 0, f"Ruff failed: {ruff_result.stdout.decode()}"
```

### Specific Test Scenarios

**Scenario 1: Single Agent Invocation (smoke test)**
```python
@pytest.mark.smoke
@skipif_no_codex
def test_codex_implementation_agent_smoke(codex_runner, minimal_project):
    """Smoke test: Can Codex runner invoke implementation agent?"""
    result = codex_runner.run_agent(
        agent_spec_path=Path("claude_plugin/agents/execution-implementer.md"),
        prompt="Add a simple hello() function to main.py",
        context={"task_id": "test"},
    )

    assert result.success
    assert result.structured_output is not None
```

**Scenario 2: QA Failure and Retry**
```python
@pytest.mark.slow
@skipif_no_codex
def test_codex_qa_failure_recovery(codex_runner, temp_project, broken_implementation):
    """Test QA failure triggers fix loop."""
    # Setup: Create intentionally broken implementation
    create_broken_code(temp_project)

    # Run QA agent (should fail)
    qa_result = codex_runner.run_agent(
        agent_spec_path=agent_specs["qa"],
        prompt="Verify the implementation meets acceptance criteria",
        context={"task_path": "docs/tasks/test-task"},
    )

    assert qa_result.structured_output["dod_achieved"] == False
    assert "fix_info" in qa_result.structured_output

    # Run implementation with fix_info (should fix issues)
    impl_result = codex_runner.run_agent(
        agent_spec_path=agent_specs["implementer"],
        prompt="Fix the issues identified by QA",
        context={
            "task_path": "docs/tasks/test-task",
            "fix_info": qa_result.structured_output["fix_info"],
            "iteration": 2,
        },
    )

    assert impl_result.success
    assert "files_changed" in impl_result.structured_output

    # Run QA again (should pass now)
    qa_result_2 = codex_runner.run_agent(
        agent_spec_path=agent_specs["qa"],
        prompt="Verify the implementation meets acceptance criteria",
        context={"task_path": "docs/tasks/test-task"},
    )

    assert qa_result_2.structured_output["dod_achieved"] == True
```

**Scenario 3: Runner Equivalence**
```python
@pytest.mark.slow
@pytest.mark.parametrize("runner_name,runner_factory", [
    pytest.param("claude", lambda: ClaudeRunner(), marks=skipif_no_claude),
    pytest.param("codex", lambda: CodexRunner(), marks=skipif_no_codex),
    pytest.param("gemini", lambda: GeminiRunner(), marks=skipif_no_gemini),
])
def test_runner_equivalence(runner_name, runner_factory, temp_project):
    """Verify all runners produce functionally equivalent results."""
    runner = runner_factory()
    runner._working_dir = temp_project

    # Run same task with each runner
    result = run_full_loop(runner, temp_project, "simple-task")

    # Verify all achieve same outcome
    assert result["task_complete"] == True, f"{runner_name} didn't complete"
    assert result["tests_pass"] == True, f"{runner_name} tests failed"
    assert result["quality_pass"] == True, f"{runner_name} quality failed"

    # Store results for comparison
    results[runner_name] = result

# After all runners complete, verify equivalence
def test_results_are_equivalent(results):
    """Compare results across runners."""
    # All should modify same files
    common_files = set(results["claude"]["files_changed"]) & \
                   set(results["codex"]["files_changed"]) & \
                   set(results["gemini"]["files_changed"])
    assert len(common_files) > 0, "No common files modified"

    # All should have similar token usage (within 2x)
    tokens = [r["token_usage"]["total_tokens"] for r in results.values()]
    assert max(tokens) <= 2 * min(tokens), "Token usage too different"
```

## Infrastructure Requirements

### Pytest Configuration

```ini
# pytest.ini (or add to pyproject.toml)
[tool.pytest.ini_options]
markers =
    slow: Slow tests (>1 minute)
    real_runner: Tests requiring real CLI runners
    claude: Tests requiring Claude Code CLI
    codex: Tests requiring Codex CLI
    gemini: Tests requiring Gemini CLI
    smoke: Quick smoke tests
    equivalence: Cross-runner comparison tests
```

### Directory Structure

```
tests/
├── fixtures/
│   ├── projects/
│   │   ├── simple-python/
│   │   │   ├── __init__.py
│   │   │   ├── project_files.py      # Dict[str, str] of file paths → content
│   │   │   └── task_files.py         # Dict[str, str] of task artifacts
│   │   └── README.md
│   └── conftest.py
│
├── integration/
│   ├── runners/                       # NEW
│   │   ├── conftest.py                # Runner fixtures
│   │   ├── test_claude_runner_real.py
│   │   ├── test_codex_runner_real.py
│   │   ├── test_gemini_runner_real.py
│   │   └── test_runner_equivalence.py
│   │
│   ├── conftest.py                    # Existing fixtures
│   ├── test_agentic_loop_e2e.py       # Existing (mock tests)
│   └── ...
│
└── README.md                          # Test documentation
```

### Sample Project Template

```python
# tests/fixtures/projects/simple-python/project_files.py

PROJECT_FILES = {
    "sample_project/__init__.py": '"""Sample project package."""\n',

    "sample_project/main.py": '''"""Main module with basic functions."""


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b
''',

    "tests/__init__.py": "",

    "tests/test_main.py": '''"""Tests for main module."""

from sample_project.main import add, multiply


def test_add():
    """Test addition."""
    assert add(2, 3) == 5
    assert add(-1, 1) == 0


def test_multiply():
    """Test multiplication."""
    assert multiply(2, 3) == 6
    assert multiply(0, 5) == 0
''',

    "pyproject.toml": """[project]
name = "sample-project"
version = "0.1.0"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
""",
}
```

```python
# tests/fixtures/projects/simple-python/task_files.py

TASK_FILES = {
    "docs/tasks/string-utils/task-description.md": """# Task: Add String Utilities

## Overview
Add utility functions for string manipulation to the sample project.

## Requirements
1. Create `sample_project/utils.py` with the following functions:
   - `reverse_string(s: str) -> str`: Return reversed string
   - `capitalize_words(s: str) -> str`: Capitalize first letter of each word
2. Add type hints and docstrings to all functions
3. Create comprehensive tests in `tests/test_utils.py`
4. Ensure all tests pass and code quality checks pass

## Target File
`sample_project/utils.py`

## Success Criteria
- All functions have proper type hints
- All functions have docstrings
- All tests pass (pytest)
- Code quality passes (ruff)
""",

    "docs/tasks/string-utils/README.md": """# String Utilities Task

Add string manipulation functions to the project.
""",

    "docs/tasks/string-utils/user-stories/US-001.md": """# US-001: String Reversal Function

## Description
As a developer, I want a function to reverse strings.

## Status
In Progress

## Acceptance Criteria
- [ ] `reverse_string(s: str) -> str` function exists
- [ ] Function returns reversed string
- [ ] Empty strings handled correctly
- [ ] Type hints present
- [ ] Docstring present
- [ ] Tests pass
""",

    "docs/tasks/string-utils/user-stories/US-002.md": """# US-002: Capitalize Words Function

## Description
As a developer, I want a function to capitalize each word in a string.

## Status
In Progress

## Acceptance Criteria
- [ ] `capitalize_words(s: str) -> str` function exists
- [ ] Function capitalizes first letter of each word
- [ ] Empty strings return empty strings
- [ ] Type hints present
- [ ] Docstring present
- [ ] Tests pass
""",

    "docs/tasks/string-utils/implementation-plan/phase-01.md": """# Phase 1: Core Implementation

## Status
Pending

## Objectives
1. Create `sample_project/utils.py` with both utility functions
2. Add proper type hints and docstrings
3. Create test file `tests/test_utils.py`

## Acceptance Criteria
- Both functions implemented
- All tests pass
- Code quality checks pass
""",
}
```

### Verification Helper Functions

```python
# tests/integration/runners/helpers.py

import subprocess
from pathlib import Path


def verify_target_file_created(project_dir: Path, target_file: str, expected_functions: list[str]):
    """Verify implementation file was created with expected functions."""
    target = project_dir / target_file
    assert target.exists(), f"Target file not created: {target_file}"

    content = target.read_text()

    for func in expected_functions:
        assert f"def {func}" in content, f"Function {func} not found"

    # Check type hints
    assert ": " in content and "->" in content, "Type hints missing"

    # Check docstrings
    assert '"""' in content, "Docstrings missing"


def verify_tests_pass(project_dir: Path):
    """Verify pytest passes in project directory."""
    result = subprocess.run(
        ["pytest", str(project_dir / "tests"), "-q", "--tb=short"],
        capture_output=True,
        timeout=60,
        cwd=project_dir,
    )

    assert result.returncode == 0, \
        f"Tests failed:\nSTDOUT:\n{result.stdout.decode()}\nSTDERR:\n{result.stderr.decode()}"


def verify_code_quality(project_dir: Path):
    """Verify code quality tools pass."""
    # Ruff check
    ruff_result = subprocess.run(
        ["ruff", "check", str(project_dir)],
        capture_output=True,
        timeout=30,
    )

    assert ruff_result.returncode == 0, \
        f"Ruff check failed:\n{ruff_result.stdout.decode()}"


def verify_structured_output(result, required_keys: list[str]):
    """Verify runner result has required structured output keys."""
    assert result.success, f"Runner failed: {result.error}"
    assert result.structured_output is not None, "No structured output"

    for key in required_keys:
        assert key in result.structured_output, f"Missing key: {key}"


def verify_functional_equivalence(results: dict[str, dict]):
    """Verify results from different runners are functionally equivalent."""
    # All should achieve task completion
    for runner_name, result in results.items():
        assert result["task_complete"], f"{runner_name}: Task not complete"
        assert result["tests_pass"], f"{runner_name}: Tests failed"
        assert result["quality_pass"], f"{runner_name}: Quality failed"

    # All should modify similar files (intersection > 0)
    file_sets = [set(r.get("files_changed", [])) for r in results.values()]
    common_files = set.intersection(*file_sets)
    assert len(common_files) > 0, "No common files modified across runners"

    # Token usage should be within reasonable range (max ≤ 3x min)
    token_counts = [r.get("token_usage", {}).get("total_tokens", 0) for r in results.values()]
    if all(t > 0 for t in token_counts):  # If all tracked tokens
        assert max(token_counts) <= 3 * min(token_counts), \
            f"Token usage too different: {token_counts}"
```

## Roadmap: Local Testing → CI Integration

### Phase 1: Local Validation (Week 1)

**Goals:**
- Validate CLIs work locally
- Create smoke tests for each runner
- Document setup process

**Tasks:**
1. Install CLIs locally (Claude, Codex, Gemini)
2. Create `tests/integration/runners/` directory
3. Write smoke tests (single agent invocation)
4. Add pytest markers and skip conditions
5. Document CLI installation in README

**Deliverables:**
- Working smoke tests for each runner
- `tests/integration/runners/README.md` with setup instructions
- `scripts/check-runner-clis.sh` availability checker

**Acceptance:**
- All three smoke tests pass locally
- Tests skip gracefully if CLI not installed
- <5 minutes to run all smoke tests

### Phase 2: Full Loop Tests (Week 2)

**Goals:**
- Test complete agentic loop with real runners
- Verify all agents work correctly
- Handle failure scenarios (QA, quality)

**Tasks:**
1. Create full loop test for each runner
2. Add QA failure/recovery test
3. Add code quality failure/recovery test
4. Create test fixtures for sample projects
5. Add timeout and retry logic

**Deliverables:**
- `test_claude_runner_real.py` with 3-5 scenarios
- `test_codex_runner_real.py` with 3-5 scenarios
- `test_gemini_runner_real.py` with 3-5 scenarios
- `tests/fixtures/projects/simple-python/` template

**Acceptance:**
- Full loop completes successfully for each runner
- Retry scenarios work correctly
- <15 minutes to run all full loop tests

### Phase 3: Equivalence Testing (Week 3)

**Goals:**
- Compare outputs across runners
- Verify functional equivalence
- Document platform differences

**Tasks:**
1. Create equivalence test framework
2. Run same task on all three runners
3. Compare artifacts, test results, code quality
4. Document differences (expected vs. bugs)
5. Create equivalence report

**Deliverables:**
- `test_runner_equivalence.py` with comparison logic
- `docs/runner-comparison.md` documenting findings
- Helper functions for verification

**Acceptance:**
- All runners produce functionally equivalent outputs
- Differences documented and understood
- Equivalence test runs in <30 minutes

### Phase 4: CI Integration (Week 4)

**Goals:**
- Run tests in GitHub Actions
- Manage credentials securely
- Handle cost and flakiness

**Tasks:**
1. Create `.github/workflows/test-runners.yml`
2. Add secrets for API keys
3. Configure conditional execution (skip if no secrets)
4. Add retry logic for flaky tests
5. Set up nightly runs (not per-commit)

**Deliverables:**
- Working CI workflow
- Secrets configured in GitHub
- Nightly test schedule

**Acceptance:**
- Tests run successfully in CI
- Failures don't block unrelated PRs
- Cost stays under budget (<$10/month)

### Future Enhancements

**Post-v1.0:**
- Planning phase tests (Claude plugin dependent)
- Performance benchmarking across runners
- Cost analysis and optimization
- Multi-language support (TypeScript, Go, etc.)
- Parallel execution (run all runners simultaneously)

## Risks and Mitigations

### High-Priority Risks

**Risk 1: CLIs don't work as expected**
- **Mitigation:** Validate manually first, document issues early
- **Fallback:** Focus on runners that work, document others as "experimental"

**Risk 2: Tests are too slow for regular use**
- **Mitigation:** Mark as slow, run in nightly CI only
- **Fallback:** Keep IntelligentMockRunner for fast feedback

**Risk 3: Outputs are too different to compare**
- **Mitigation:** Verify functional equivalence, not code equivalence
- **Fallback:** Document acceptable differences, relax assertions

### Medium-Priority Risks

**Risk 4: API costs get out of control**
- **Mitigation:** Use usage limits, monitor spending, use smaller models
- **Fallback:** Reduce test frequency, run only on main branch

**Risk 5: Flaky tests due to LLM non-determinism**
- **Mitigation:** Use retries, generous timeouts, functional verification
- **Fallback:** Mark as flaky, don't block on failures

**Risk 6: Credentials leak or expire**
- **Mitigation:** Use GitHub secrets, rotate regularly, monitor access
- **Fallback:** Disable tests until credentials fixed

### Low-Priority Risks

**Risk 7: Test projects become stale**
- **Mitigation:** Keep minimal, document dependencies clearly
- **Fallback:** Update fixtures when breaking changes occur

**Risk 8: CI runs take too long**
- **Mitigation:** Parallelize runners, use caching, optimize fixtures
- **Fallback:** Run subset of tests per commit, full suite nightly

## Recommendations

### Critical Changes to User's Proposal

**1. Don't create project "from scratch"**
- ❌ Original: "small project from scratch"
- ✅ Better: Minimal pre-existing project with basic structure
- **Reason:** Avoids bootstrap complexity, focuses on feature implementation

**2. Make "automated eval" more specific**
- ❌ Original: "automated eval to verify feature built correctly"
- ✅ Better: Three-tier verification (file-level, test-level, quality-level)
- **Reason:** Clear success criteria, not just "does it work"

**3. Add failure scenarios**
- ❌ Original: Only happy path testing
- ✅ Better: Test QA failures, quality failures, retries
- **Reason:** Real world has failures, need to verify recovery

**4. Define equivalence strategy**
- ❌ Original: Unclear how to compare runners
- ✅ Better: Functional equivalence (same outcome, different code OK)
- **Reason:** Different LLMs write different code, that's expected

**5. Local-first is correct, but needs phases**
- ✅ Original: "run locally first"
- ✅ Better: Phased approach (smoke → loop → equivalence → CI)
- **Reason:** Incremental validation reduces risk

### Implementation Priority

**High Priority (Do First):**
1. ✅ Install CLIs and validate they work at all
2. ✅ Create smoke test for one runner (Claude, since it works)
3. ✅ Create full loop test for Claude runner
4. ✅ Replicate for Codex and Gemini

**Medium Priority (Do Second):**
1. ✅ Add failure/retry scenarios
2. ✅ Create equivalence tests
3. ✅ Document differences
4. ✅ Create helper functions for verification

**Low Priority (Do Later):**
1. ⏸ CI integration
2. ⏸ Cost optimization
3. ⏸ Performance benchmarking
4. ⏸ Planning phase tests

### Success Metrics

**Week 1:**
- [ ] All three CLIs installed locally
- [ ] Smoke tests pass for all runners
- [ ] Tests skip if CLI not installed
- [ ] Documentation complete

**Week 2:**
- [ ] Full loop tests pass for all runners
- [ ] QA failure/retry works
- [ ] Quality failure/retry works
- [ ] Test fixtures created

**Week 3:**
- [ ] Equivalence test runs successfully
- [ ] All runners produce equivalent outcomes
- [ ] Differences documented
- [ ] Verification helpers complete

**Week 4:**
- [ ] CI workflow created
- [ ] Tests run in GitHub Actions
- [ ] Credentials secured
- [ ] Cost under control

## Conclusion

The user's "eval" approach is **sound but needs significant refinement**. The key insights:

1. **Existing infrastructure is excellent** - IntelligentMockRunner, testcontainers, sample projects
2. **Critical gap: zero tests with real runners** - This is what must be filled
3. **Verification must be specific** - Not "does it work" but "files created, tests pass, quality passes"
4. **Equivalence is functional, not literal** - Different code, same outcome
5. **Phased approach reduces risk** - Smoke → Loop → Equivalence → CI

**Recommended approach:**
1. Start with Claude runner (known to work)
2. Create smoke + full loop tests
3. Replicate for Codex and Gemini
4. Add equivalence testing
5. Defer CI until local tests stable

**Timeline:** 4 weeks for full implementation, 1 week for smoke tests

**Effort:** ~40-60 hours total (10-15 hours per week)

**Risk level:** Medium (CLIs may not work as expected, tests may be flaky)

**Payoff:** High (validates multi-platform support, unblocks production use)

---

**Research Complete:** 2026-02-12

**Next Actions:**
1. Install CLIs locally (claude, codex, gemini)
2. Create `tests/integration/runners/` directory
3. Write first smoke test for Claude runner
4. Document setup process in README

**Questions for User:**
1. Do you have access to all three CLIs already installed?
2. Are API credentials available for testing?
3. What's your time budget for this work (hours per week)?
4. Should we prioritize one runner over others (e.g., Codex first)?
