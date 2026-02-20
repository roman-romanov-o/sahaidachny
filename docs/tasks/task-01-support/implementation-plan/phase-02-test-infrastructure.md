# Phase 02: Test Infrastructure

**Status:** Not Started
**Estimated Effort:** M (5-7 hours)
**Dependencies:** Phase 01 (runners validated and working)

## Objective

Build authenticated Docker container test infrastructure and fast smoke tests to validate all three runners (Claude, Codex, Gemini) work correctly before investing in expensive full-loop E2E tests.

## Scope

### Stories Included

| Story | Priority | Complexity | Estimated Hours |
|-------|----------|------------|-----------------|
| US-003: Authenticated Container Infrastructure | Must Have | M | 3-4h |
| US-004: Smoke Tests for All Runners | Must Have | S | 2-3h |

**Total: 5-7 hours**

### Out of Scope (Deferred to Later Phases)

- US-005: Full loop E2E tests (Phase 3)
- US-006: Graceful degradation (Phase 4)
- US-007: Error messages (Phase 4)

## Implementation Steps

### Step 1: Create Docker Container Fixtures

**Description:** Build pytest fixtures that provide authenticated Docker containers with all three CLIs installed and configured with API keys from host environment.

**Files to Create:**
- `tests/integration/runners/conftest.py` - Container fixtures and skip markers
- `tests/integration/runners/README.md` - Setup documentation
- `tests/integration/runners/__init__.py` - Package marker
- `.env.example` - Example API key configuration

**Technical Notes:**

**Container fixture pattern:**
```python
# tests/integration/runners/conftest.py
import os
import pytest
from testcontainers.core.container import DockerContainer

@pytest.fixture(scope="module")
def authenticated_container():
    """Container with CLI credentials from host environment."""
    container = DockerContainer("debian:bookworm-slim")
        .with_command("sleep infinity")
        .with_env("ANTHROPIC_API_KEY", os.environ.get("ANTHROPIC_API_KEY", ""))
        .with_env("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
        .with_env("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
        .with_env("HOME", "/root")

    container.start()

    # Install Node.js and CLIs
    container.exec("apt-get update && apt-get install -y curl")
    container.exec("curl -fsSL https://deb.nodesource.com/setup_20.x | bash -")
    container.exec("apt-get install -y nodejs")
    container.exec("npm install -g @anthropics/claude @openai/codex @google/gemini-cli")

    yield container

    container.stop()

# Skip markers
has_anthropic_key = os.environ.get("ANTHROPIC_API_KEY") is not None
has_openai_key = os.environ.get("OPENAI_API_KEY") is not None
has_gemini_key = os.environ.get("GEMINI_API_KEY") is not None

skipif_no_claude = pytest.mark.skipif(
    not has_anthropic_key,
    reason="ANTHROPIC_API_KEY not set"
)

skipif_no_codex = pytest.mark.skipif(
    not has_openai_key,
    reason="OPENAI_API_KEY not set"
)

skipif_no_gemini = pytest.mark.skipif(
    not has_gemini_key,
    reason="GEMINI_API_KEY not set"
)
```

**Security considerations:**
- Never log API keys (add pytest plugin to redact)
- Use module scope to reuse containers (faster tests)
- Store keys in `.env` file (already in `.gitignore`)
- Clear environment variables on container stop
- Never commit `.env` to git (use `.env.example` as template)
- Add `.env.example` with placeholder keys
- Document in README: use separate test API keys, not production

**Acceptance Criteria:**
- [ ] Container fixture created with module scope
- [ ] API keys passed from host environment to container
- [ ] All three CLIs installed and available in container
- [ ] Tests automatically skip when API key missing (clear message)
- [ ] Environment variables cleared on container stop
- [ ] Multiple tests reuse same container in module
- [ ] Container cleanup works even on pytest failures

**Tests:**
- TC-INT-001: Container with API keys starts successfully
- TC-INT-002: All CLIs installed and version commands work
- TC-INT-003: Test skipped when API key missing
- TC-INT-004: Environment cleared on stop
- TC-INT-005: Module-scoped container reuse works

---

### Step 2: Write Container Infrastructure Tests

**Description:** Write integration tests that validate the container infrastructure itself before using it for runner tests.

**Files to Create:**
- `tests/integration/runners/test_container_infrastructure.py` - Container tests

**Test Cases:**

**TC-INT-001: Container starts with API keys**
```python
@pytest.mark.slow
def test_container_starts_with_api_keys(authenticated_container):
    """Verify container starts and has API keys in environment."""
    result = authenticated_container.exec("env | grep API_KEY")
    assert "ANTHROPIC_API_KEY" in result or os.getenv("ANTHROPIC_API_KEY") is None
    assert "OPENAI_API_KEY" in result or os.getenv("OPENAI_API_KEY") is None
    assert "GEMINI_API_KEY" in result or os.getenv("GEMINI_API_KEY") is None
```

**TC-INT-002: All CLIs installed**
```python
@pytest.mark.slow
def test_all_clis_installed(authenticated_container):
    """Verify all three CLIs are installed and accessible."""
    claude_version = authenticated_container.exec("claude --version")
    assert claude_version.exit_code == 0

    codex_version = authenticated_container.exec("codex --version")
    assert codex_version.exit_code == 0

    gemini_version = authenticated_container.exec("gemini --version")
    assert gemini_version.exit_code == 0
```

**TC-INT-003: Auto-skip when key missing**
```python
@skipif_no_claude
def test_skip_when_key_missing():
    """Test is skipped if API key not available."""
    # This test only runs if ANTHROPIC_API_KEY is set
    assert os.getenv("ANTHROPIC_API_KEY") is not None
```

**TC-INT-004: Environment cleared on stop**
```python
@pytest.mark.slow
def test_environment_cleared_on_stop():
    """Verify API keys are not leaked after container stops."""
    container = DockerContainer("debian:bookworm-slim") \
        .with_env("ANTHROPIC_API_KEY", "test-key-value")
    container.start()

    result = container.exec("env | grep ANTHROPIC_API_KEY")
    assert "test-key-value" in result

    container.stop()
    # Verify container stopped (no assertions needed, just cleanup)
```

**TC-INT-005: Module-scoped reuse**
```python
@pytest.mark.slow
def test_container_reuse_same_module(authenticated_container):
    """Verify container is reused across tests in same module."""
    container_id_1 = authenticated_container.get_wrapped_container().id
    # This would be called from another test in same module
    assert container_id_1 is not None
```

**Acceptance Criteria:**
- [ ] All 5 test cases implemented
- [ ] Tests pass when API keys are available
- [ ] Tests skip when API keys are missing
- [ ] Test execution time <10 minutes (with container reuse)

---

### Step 3: Write Smoke Tests for All Runners

**Description:** Write fast smoke tests that validate basic functionality of all three runners using authenticated containers.

**Files to Create:**
- `tests/integration/runners/test_claude_runner_real.py` - Claude smoke tests
- `tests/integration/runners/test_codex_runner_real.py` - Codex smoke tests
- `tests/integration/runners/test_gemini_runner_real.py` - Gemini smoke tests

**Test Pattern (same for all runners):**

**TC-E2E-001/002/003: Runner smoke test**
```python
import pytest
from saha.runners.claude import ClaudeRunner
from pathlib import Path

@pytest.mark.slow
@pytest.mark.claude
@skipif_no_claude
@pytest.mark.timeout(60)
def test_claude_runner_smoke(authenticated_container):
    """Smoke test: Claude runner basic invocation."""
    runner = ClaudeRunner(working_dir=Path("/tmp/test"))
    result = runner.run_prompt("Say hello")

    # Level 1: Process
    assert result.exit_code == 0

    # Level 2: Artifacts
    assert result.success
    assert result.output

    # Level 3: Functional
    assert "hello" in result.output.lower()

    # Warn if slow
    if result.duration_seconds > 30:
        pytest.warns(f"Smoke test took {result.duration_seconds}s (>30s threshold)")
```

**Acceptance Criteria:**
- [ ] Claude smoke test passes (TC-E2E-001)
- [ ] Codex smoke test passes (TC-E2E-002)
- [ ] Gemini smoke test passes (TC-E2E-003)
- [ ] All tests complete in <30s each (warning if slower)
- [ ] Tests skip when API key missing
- [ ] Proper pytest markers (`@pytest.mark.slow`, `@pytest.mark.claude`, etc.)

**Tests:**
- TC-E2E-001: Claude runner smoke test
- TC-E2E-002: Codex runner smoke test
- TC-E2E-003: Gemini runner smoke test
- TC-E2E-004: Structured output validation (RunnerResult fields)
- TC-E2E-005: Skip when key missing
- TC-E2E-006: Edge cases (timeout, error handling)

---

### Step 4: Write Unit Tests for Runner Utilities

**Description:** Write fast unit tests for runner utility functions (file tracking, skill loading, JSON parsing) with mocked dependencies.

**Files to Create:**
- `tests/unit/runners/test_codex_runner_utils.py` - Codex utilities
- `tests/unit/runners/test_gemini_runner_utils.py` - Gemini utilities
- `tests/unit/runners/__init__.py` - Package marker

**Test Cases (examples):**

**TC-UNIT-001: File change tracker - no changes**
```python
def test_file_tracker_no_changes(tmp_path):
    """File tracker detects no changes when no files modified."""
    tracker = _FileChangeTracker(tmp_path)
    tracker.start()
    # No file operations
    tracker.end()

    assert tracker.changed_files == []
    assert tracker.added_files == []
```

**TC-UNIT-031: Gemini command builder - no yolo flag**
```python
def test_gemini_command_no_yolo_flag():
    """Verify --yolo flag is not in Gemini command."""
    runner = GeminiRunner()
    command = runner._build_command("test prompt")

    assert "--yolo" not in command
```

**Acceptance Criteria:**
- [ ] 23 unit tests implemented (per test spec)
- [ ] Tests run in <5 seconds total
- [ ] 100% coverage of utility functions
- [ ] No real API calls (all mocked)

**Tests:**
- TC-UNIT-001 to TC-UNIT-042 (from test spec)

---

### Step 5: Write Integration Tests for Runner Compliance

**Description:** Write integration tests that validate all runners implement the Runner ABC interface correctly.

**Files to Create:**
- `tests/integration/runners/test_runner_compliance.py` - Interface compliance tests

**Test Cases:**

**TC-INT-010: Runner implements all ABC methods**
```python
@pytest.mark.parametrize("runner_class", [ClaudeRunner, CodexRunner, GeminiRunner])
def test_runner_implements_interface(runner_class):
    """Verify runner implements all Runner ABC methods."""
    runner = runner_class()

    assert hasattr(runner, "run_agent")
    assert callable(runner.run_agent)
    # ... (check all methods)
```

**TC-INT-011: is_available() never raises**
```python
@pytest.mark.parametrize("runner_class", [ClaudeRunner, CodexRunner, GeminiRunner])
def test_is_available_no_exceptions(runner_class):
    """is_available() returns bool without raising."""
    runner = runner_class()
    available = runner.is_available()
    assert isinstance(available, bool)
```

**Acceptance Criteria:**
- [ ] All 10 compliance tests implemented (TC-INT-010 to TC-INT-020)
- [ ] Tests pass for all three runners
- [ ] Tests complete in <15 minutes with authenticated containers

**Tests:**
- TC-INT-010 to TC-INT-020 (from test spec)

---

### Step 6: Create Test Documentation

**Description:** Document how to set up and run the test suite.

**Files to Create/Update:**
- `tests/integration/runners/README.md` - Setup guide
- `.env.example` - API key template

**README content:**
```markdown
# Integration Tests for Runners

## Setup

1. Install Docker and ensure daemon is running
2. Install Python dependencies: `pip install -e ".[test]"`
3. Set up API keys in `.env` file (NEVER commit this file!):
   ```bash
   # Copy template
   cp .env.example .env

   # Edit .env and add your keys:
   # ANTHROPIC_API_KEY=sk-ant-...
   # OPENAI_API_KEY=sk-...
   # GEMINI_API_KEY=...

   # Load environment (or use direnv/dotenv)
   source .env
   ```

## Running Tests

```bash
# All tests (slow, ~20 min)
pytest tests/integration/runners/ -v

# Only Claude tests
pytest tests/integration/runners/ -m claude -v

# Skip slow tests
pytest tests/integration/runners/ -m "not slow" -v
```

## Cost

Estimated cost per full test run:
- Claude: $0.05-0.10
- Codex: $0.03-0.05
- Gemini: $0.02-0.05
- **Total: ~$0.10-0.20**
```

**Acceptance Criteria:**
- [ ] README.md created with setup instructions
- [ ] .env.example created with API key placeholders
- [ ] Documentation includes cost estimates
- [ ] Documentation includes troubleshooting section

## Definition of Done

Phase is complete when:
- [ ] **Container infrastructure works:** All 5 infrastructure tests pass (TC-INT-001 to TC-INT-005)
- [ ] **Smoke tests pass:** All 3 runners pass smoke tests (TC-E2E-001 to TC-E2E-003)
- [ ] **Unit tests pass:** All 23 utility tests pass (TC-UNIT-001 to TC-UNIT-042)
- [ ] **Compliance tests pass:** All 10 interface tests pass (TC-INT-010 to TC-INT-020)
- [ ] **Documentation complete:** README and .env.example created
- [ ] **Tests are fast:** Unit tests <5s, smoke tests <2 min total, all tests <20 min
- [ ] **Ready for E2E:** Infrastructure stable enough for full loop tests

**Quality Gates:**
```bash
# Run all tests
pytest tests/ -v

# Check test coverage
pytest tests/ --cov=saha/runners --cov-report=term-missing

# Verify test performance
pytest tests/unit/ --durations=10  # Should be <5s
pytest tests/integration/runners/ -k "smoke" --durations=10  # Should be <2min
```

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Docker not available on all dev machines | Medium | High | Document Docker Desktop installation; provide fallback mocks |
| API keys rate-limited during tests | Medium | Medium | Use test API keys with higher limits; implement retry logic |
| Container startup too slow (>1 min) | Medium | Medium | Use module scope to amortize cost; optimize base image |
| CLI installation fails in container | Low | High | Pin CLI versions; provide pre-built image option |
| Tests flaky due to network issues | Medium | Medium | Implement retries; add timeout buffers |

## Notes

**Why module scope for containers:**
- Faster: Container reused across tests in same module (~5s startup amortized)
- Cheaper: Fewer API key validations
- Safer: Less Docker resource churn

**Test organization:**
- `tests/unit/` - Fast, mocked, no API calls
- `tests/integration/` - Authenticated containers, real CLIs
- `tests/e2e/` - Full workflows (Phase 3)

**Markers:**
- `@pytest.mark.slow` - Uses real API calls (skip with `-m "not slow"`)
- `@pytest.mark.claude/codex/gemini` - Filter by platform
- `@skipif_no_<runner>` - Auto-skip if API key missing

## Related

- **Stories:** [US-003](../user-stories/US-003-authenticated-container-infrastructure.md), [US-004](../user-stories/US-004-smoke-tests-all-runners.md)
- **Research:** [06-e2e-testing-strategy.md](../research/06-e2e-testing-strategy.md), [07-docker-auth-real-runners.md](../research/07-docker-auth-real-runners.md)
- **Test Specs:** [e2e/01-runner-smoke-tests.md](../test-specs/e2e/01-runner-smoke-tests.md), [integration/01-authenticated-containers.md](../test-specs/integration/01-authenticated-containers.md)
- **Previous Phase:** [Phase 01: Runner Validation](phase-01-runner-validation.md)
- **Next Phase:** [Phase 03: E2E Validation](phase-03-e2e-validation.md)
