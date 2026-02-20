# Integration Test Spec: Authenticated Container Infrastructure

**Related:** US-003, [07-docker-auth-real-runners.md](../../research/07-docker-auth-real-runners.md)
**Priority:** Critical
**Status:** Draft

## Overview

Tests for Docker container fixtures with CLI authentication, enabling E2E tests to run with real Claude Code, Codex, and Gemini CLI runners.

## Dependencies

- Docker daemon running locally
- testcontainers-python library installed
- At least one API key available in environment

## Test Cases

### TC-INT-001: Container Starts with Environment Variables

**Description:** Verify authenticated container fixture passes API keys via environment variables.

**Setup:**
```python
@pytest.fixture
def mock_env_keys(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key-123")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key-456")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key-789")
```

**Input:**
- Host environment variables set

**Expected Output:**
- Container created successfully
- Environment variables injected
- Variables readable inside container

**Assertions:**
```python
container = authenticated_container_fixture()
exec_result = container.exec("env | grep API_KEY")
output = exec_result.output.decode()

assert "ANTHROPIC_API_KEY=test-anthropic-key-123" in output
assert "OPENAI_API_KEY=test-openai-key-456" in output
assert "GEMINI_API_KEY=test-gemini-key-789" in output
```

---

### TC-INT-002: CLI Installation Inside Container

**Description:** Verify all three CLIs can be installed and are available.

**Setup:**
- Start base Debian container
- Install Node.js (required for npm)
- Install Python (required for Claude Code CLI)

**Input:**
```bash
# Commands to run inside container
npm install -g @openai/codex
npm install -g @google/gemini-cli
pip install claude-code-cli
```

**Expected Output:**
- All three CLIs installed successfully
- Commands available in PATH

**Assertions:**
```python
assert container.exec("which claude").exit_code == 0
assert container.exec("which codex").exit_code == 0
assert container.exec("which gemini").exit_code == 0

assert container.exec("claude --version").exit_code == 0
assert container.exec("codex --version").exit_code == 0
assert container.exec("gemini --version").exit_code == 0
```

---

### TC-INT-003: Test Skipped When API Key Missing

**Description:** Verify test is automatically skipped with clear message when API key unavailable.

**Setup:**
```python
@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set"
)
def test_requires_claude_key(authenticated_container):
    ...
```

**Input:**
- `ANTHROPIC_API_KEY` not set in environment

**Expected:**
- Test status: SKIPPED (not FAILED)
- Skip reason: "ANTHROPIC_API_KEY not set"
- No error traceback

**Assertions:**
```python
# Run pytest programmatically
result = pytest.main([
    "tests/integration/runners/test_claude.py",
    "-v"
])

# Check output
assert "SKIPPED" in result.stdout
assert "ANTHROPIC_API_KEY not set" in result.stdout
assert result.returncode == 0  # Skips don't fail test suite
```

---

### TC-INT-004: API Keys Cleared on Container Stop

**Description:** Verify environment variables are cleared when container stops and no keys appear in logs.

**Setup:**
1. Start authenticated container with API keys
2. Verify keys are set
3. Stop container
4. Capture all pytest output and logs

**Expected:**
- Environment variables cleared on stop
- No API keys appear in pytest output
- No API keys appear in Docker logs
- No API keys in pytest capture logs

**Assertions:**
```python
container.start()
# Verify keys present
assert container.exec("echo $ANTHROPIC_API_KEY").output != ""

container.stop()

# Verify keys not in logs
pytest_output = capsys.readouterr()
assert "test-anthropic-key" not in pytest_output.out
assert "test-openai-key" not in pytest_output.out
assert "test-gemini-key" not in pytest_output.out

docker_logs = container.get_logs()
assert "test-anthropic-key" not in docker_logs
```

---

### TC-INT-005: Module-Scoped Container Reuse

**Description:** Verify container is reused for all tests in module but cleanly stopped after last test.

**Setup:**
```python
@pytest.fixture(scope="module")
def authenticated_container():
    container = DockerContainer("debian:bookworm-slim")
    container.start()
    yield container
    container.stop()
```

**Input:**
- Multiple tests in same module using fixture

**Expected:**
- Container started once at module start
- Same container instance used by all tests
- Container stopped after last test in module
- Container stopped even if teardown fails

**Assertions:**
```python
# Track container ID across tests
container_ids = []

def test_1(authenticated_container):
    container_ids.append(authenticated_container.get_container_id())

def test_2(authenticated_container):
    container_ids.append(authenticated_container.get_container_id())

# After module completion
assert len(set(container_ids)) == 1  # Same container
assert not container.is_running()  # Stopped after module
```

---

### TC-INT-006: Multiple API Keys Missing

**Description:** Verify behavior when developer has only some API keys.

**Setup:**
- Set only `ANTHROPIC_API_KEY`
- Leave `OPENAI_API_KEY` and `GEMINI_API_KEY` unset

**Expected:**
- Claude tests run normally
- Codex tests skipped with message "OPENAI_API_KEY not set"
- Gemini tests skipped with message "GEMINI_API_KEY not set"
- Test suite returns success (skips don't fail)

**Assertions:**
```python
result = pytest.main([
    "tests/integration/runners/",
    "-v",
    "--tb=short"
])

assert "test_claude_smoke PASSED" in result.stdout
assert "test_codex_smoke SKIPPED" in result.stdout
assert "test_gemini_smoke SKIPPED" in result.stdout
assert result.returncode == 0
```

---

### TC-INT-007: Container Startup Failure Handling

**Description:** Verify clear error message when container startup fails.

**Trigger:**
- Docker daemon not running
- Insufficient Docker resources

**Expected:**
- Clear error message (not cryptic testcontainers stack trace)
- Error includes helpful diagnostic info
- Test fails fast (doesn't hang)

**Assertions:**
```python
# Mock Docker unavailable
with mock.patch("testcontainers.core.docker_client.DockerClient") as mock_docker:
    mock_docker.side_effect = ConnectionError("Cannot connect to Docker")

    with pytest.raises(Exception) as exc_info:
        authenticated_container_fixture()

    assert "Cannot connect to Docker" in str(exc_info.value)
    assert "Is Docker daemon running?" in str(exc_info.value)
```

---

### TC-INT-008: CLI Installation Failure Handling

**Description:** Verify clear error when CLI installation fails.

**Trigger:**
- NPM registry down
- Package not found

**Expected:**
- Container fails fast with clear error
- Error message indicates which CLI failed
- Test skipped with helpful message

**Assertions:**
```python
# Mock npm install failure
container.exec("npm install -g @openai/nonexistent-package")
# Should fail gracefully with clear message

with pytest.raises(Exception) as exc_info:
    install_codex_cli(container)

assert "npm install failed" in str(exc_info.value).lower()
assert "codex" in str(exc_info.value).lower()
```

---

## Data Fixtures

### Authenticated Container Fixture

```python
@pytest.fixture(scope="module")
def authenticated_container():
    """Container with CLI credentials from host environment."""
    container = (
        DockerContainer("debian:bookworm-slim")
        .with_command("sleep infinity")
        .with_env("ANTHROPIC_API_KEY", os.environ.get("ANTHROPIC_API_KEY", ""))
        .with_env("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
        .with_env("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
        .with_env("HOME", "/root")
    )

    container.start()

    # Install CLIs
    install_node(container)
    install_python(container)
    install_claude_cli(container)
    install_codex_cli(container)
    install_gemini_cli(container)

    yield container

    # Cleanup
    container.stop()
```

### Skip Markers

```python
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

## Security Considerations

### API Key Redaction Filter

```python
@pytest.fixture(autouse=True)
def redact_api_keys(caplog):
    """Automatically redact API keys from logs."""
    yield
    for record in caplog.records:
        record.msg = redact_sensitive_data(record.msg)

def redact_sensitive_data(text: str) -> str:
    """Replace API keys with [REDACTED]."""
    patterns = [
        r"sk-[a-zA-Z0-9]{48}",  # Anthropic
        r"sk-proj-[a-zA-Z0-9-]{64}",  # OpenAI
        r"AIza[a-zA-Z0-9-_]{35}",  # Google
    ]
    for pattern in patterns:
        text = re.sub(pattern, "[REDACTED]", text)
    return text
```

## Test Organization

**File:** `tests/integration/runners/conftest.py` - Fixtures
**File:** `tests/integration/runners/test_authenticated_containers.py` - Tests
**File:** `tests/integration/runners/README.md` - Setup documentation

## Related

- **Story:** [US-003](../../user-stories/US-003-authenticated-container-infrastructure.md)
- **Research:** [07-docker-auth-real-runners.md](../../research/07-docker-auth-real-runners.md)
