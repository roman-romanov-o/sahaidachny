# US-003: Create Authenticated Container Test Infrastructure

**Priority:** Must Have
**Status:** Draft
**Persona:** Test Engineer
**Estimated Complexity:** M (3-4 hours)

## User Story

As a **Test Engineer**,
I want to **create Docker container fixtures with CLI authentication**,
So that **E2E tests can run with real Claude Code, Codex, and Gemini CLI runners**.

## Acceptance Criteria

1. **Given** API keys are available in host environment
   **When** authenticated container fixture is created
   **Then** API keys are passed to container via environment variables (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`)

2. **Given** authenticated container is started
   **When** CLIs are installed inside container
   **Then** all three CLIs (claude, codex, gemini) are available and configured

3. **Given** API key is missing from host environment
   **When** test requiring that CLI is run
   **Then** test is automatically skipped with clear message (pytest.skip marker)

4. **Given** authenticated container is used in tests
   **When** tests complete
   **Then** container environment variables are cleared on stop and no API keys appear in pytest output or logs

5. **Given** multiple tests use authenticated containers in same module
   **When** running test suite
   **Then** container is reused for all tests in the module, but cleanly stopped after the last test completes or on pytest teardown failure

## Edge Cases

1. **Multiple API keys missing**
   - Trigger: Developer has only Claude Code API key, not Codex/Gemini
   - Expected behavior: Only Claude tests run, others skipped with helpful message

2. **Container startup failure**
   - Trigger: Docker daemon not running or insufficient resources
   - Expected behavior: Clear error message, not cryptic testcontainers stack trace

3. **CLI installation failure**
   - Trigger: NPM registry down or package not found
   - Expected behavior: Container fails fast with clear error, test skipped

## Technical Notes

**From research (07-docker-auth-real-runners.md):**

**Recommended approach: Environment variables**
- Simple, secure, universal across all CLIs
- Native testcontainers support via `.with_env()`
- Automatic cleanup when container stops

**Implementation pattern:**
```python
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
    # Install CLIs...
    yield container
    container.stop()
```

**Skip markers:**
```python
has_anthropic_key = os.environ.get("ANTHROPIC_API_KEY") is not None
skipif_no_claude = pytest.mark.skipif(
    not has_anthropic_key,
    reason="ANTHROPIC_API_KEY not set"
)
```

**Key files to create:**
- `tests/integration/runners/conftest.py` - Authenticated container fixtures
- `tests/integration/runners/README.md` - Setup documentation

**Security considerations:**
- Never log API keys (add redaction filter to pytest)
- Use separate test API keys (not production)
- Clean up credentials after tests
- Add `.env.example` with placeholder keys

## Dependencies

- **Requires:**
  - Docker installed locally
  - testcontainers-python library
  - API keys for at least one CLI
- **Enables:**
  - US-004 (Smoke tests for all runners)
  - US-005 (Full loop E2E tests)

## Questions

- [ ] Should we provide shared test API keys or require each dev to use their own?
- [ ] What's the best base image? (debian:bookworm-slim, ubuntu:22.04, python:3.11-slim)
- [ ] Should fixtures be module-scoped or session-scoped?

## Related

- Task: [task-description.md](../task-description.md)
- Research: [07-docker-auth-real-runners.md](../research/07-docker-auth-real-runners.md)
- Research: [06-e2e-testing-strategy.md](../research/06-e2e-testing-strategy.md)
