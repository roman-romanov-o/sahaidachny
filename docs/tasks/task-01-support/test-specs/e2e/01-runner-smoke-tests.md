# E2E Test Spec: Runner Smoke Tests

**Related Stories:** US-004
**Priority:** Critical
**Status:** Draft

## Overview

Fast smoke tests that validate basic functionality of all three runners (Claude Code, Codex, Gemini) before running expensive full loop tests. Each test uses real CLIs in authenticated Docker containers.

## Preconditions

- Docker daemon running
- API keys available in environment (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`)
- Authenticated container fixture available (from US-003)

## Test Cases

### TC-E2E-001: Claude Code Runner Smoke Test

**Description:** Validate Claude Code runner can execute a simple prompt and return valid output.

**Steps:**
1. Start authenticated container with Claude Code CLI
2. Create ClaudeRunner instance
3. Execute `runner.run_prompt("Say hello")`
4. Validate response

**Expected Results:**
- Exit code: 0
- `result.success`: True
- `result.output`: Contains "hello" (case-insensitive)
- `result.exit_code`: 0
- Response time: <30s (warning if >30s)
- Pytest timeout: 60s

**Test Data:**
```python
prompt = "Say hello"
expected_keywords = ["hello"]
max_duration_warning = 30  # seconds
pytest_timeout = 60
```

**Assertions:**
```python
assert result.success
assert result.output
assert any(kw in result.output.lower() for kw in expected_keywords)
assert result.exit_code == 0
```

**Markers:**
- `@pytest.mark.slow`
- `@pytest.mark.claude`
- `@skipif_no_claude`

---

### TC-E2E-002: Codex Runner Smoke Test

**Description:** Validate Codex runner can execute a simple prompt and return valid output.

**Steps:**
1. Start authenticated container with Codex CLI
2. Create CodexRunner instance
3. Execute `runner.run_prompt("Say hello")`
4. Validate response

**Expected Results:**
- Exit code: 0
- `result.success`: True
- `result.output`: Contains "hello" (case-insensitive)
- `result.exit_code`: 0
- Response time: <30s (warning if >30s)
- Pytest timeout: 60s

**Test Data:**
```python
prompt = "Say hello"
expected_keywords = ["hello"]
```

**Assertions:**
```python
assert result.success
assert result.output
assert "hello" in result.output.lower()
assert result.exit_code == 0
```

**Markers:**
- `@pytest.mark.slow`
- `@pytest.mark.codex`
- `@skipif_no_codex`

---

### TC-E2E-003: Gemini Runner Smoke Test

**Description:** Validate Gemini runner can execute a simple prompt and return valid output.

**Steps:**
1. Start authenticated container with Gemini CLI
2. Create GeminiRunner instance
3. Execute `runner.run_prompt("Say hello")`
4. Validate response

**Expected Results:**
- Exit code: 0
- `result.success`: True
- `result.output`: Contains "hello" (case-insensitive)
- `result.exit_code`: 0
- Response time: <30s (warning if >30s)
- Pytest timeout: 60s

**Test Data:**
```python
prompt = "Say hello"
expected_keywords = ["hello"]
```

**Assertions:**
```python
assert result.success
assert result.output
assert "hello" in result.output.lower()
assert result.exit_code == 0
```

**Markers:**
- `@pytest.mark.slow`
- `@pytest.mark.gemini`
- `@skipif_no_gemini`

---

### TC-E2E-004: RunnerResult Schema Validation

**Description:** Verify all runners return RunnerResult with expected fields.

**Steps:**
1. For each runner (Claude, Codex, Gemini)
2. Execute simple prompt
3. Validate RunnerResult fields

**Expected Results:**
All runners return RunnerResult with:
- `success`: bool (True for successful execution)
- `output`: str (non-empty)
- `exit_code`: int (0 for success)
- `structured_output`: dict or None
- `error`: None (for successful execution)
- `tokens_used`: int >= 0
- `token_usage`: dict or None

**Assertions:**
```python
assert isinstance(result.success, bool)
assert isinstance(result.output, str)
assert len(result.output) > 0
assert isinstance(result.exit_code, int)
assert result.structured_output is None or isinstance(result.structured_output, dict)
assert result.error is None
assert isinstance(result.tokens_used, int)
assert result.tokens_used >= 0
assert result.token_usage is None or isinstance(result.token_usage, dict)
```

---

### TC-E2E-005: Skip Test When API Key Missing

**Description:** Verify test is skipped (not failed) when API key is unavailable.

**Steps:**
1. Unset API key for specific runner
2. Run smoke test for that runner
3. Verify test is skipped with clear message

**Expected Results:**
- Test marked as SKIPPED (not FAILED)
- Skip reason: "ANTHROPIC_API_KEY not set" (or OPENAI/GEMINI)
- No error traceback shown

**Test Implementation:**
```python
@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set"
)
def test_codex_smoke(authenticated_container):
    ...
```

---

### TC-E2E-006: Network Timeout Handling

**Description:** Verify runner handles timeout gracefully and returns proper RunnerResult.

**Steps:**
1. Set aggressive timeout (e.g., 5s)
2. Execute runner with complex prompt (likely to exceed timeout)
3. Validate RunnerResult

**Expected Results:**
- RunnerResult with `success: False`
- `error` field contains "timeout" or "exceeded"
- Exit code: non-zero (typically 124 for timeout)
- No exception propagated (timeout caught and wrapped)

**Test Data:**
```python
timeout = 5  # seconds
complex_prompt = "Write a detailed analysis of quantum computing" * 10
```

**Assertions:**
```python
result = runner.run_prompt(complex_prompt, timeout=5)
assert not result.success
assert result.error is not None
assert "timeout" in result.error.lower() or "exceeded" in result.error.lower()
assert result.exit_code != 0
```

---

## Edge Cases

### 1. CLI Not Installed

**Trigger:** Docker container doesn't have CLI installed

**Expected Behavior:**
- Test skipped with message "Claude CLI not available"
- `runner.is_available()` returns False

### 2. API Rate Limiting

**Trigger:** Too many requests hit rate limit (429 error)

**Expected Behavior:**
- Test retries with exponential backoff (max 3 retries)
- Final failure shows rate limit error clearly

### 3. Concurrent Test Execution

**Trigger:** Multiple smoke tests run in parallel

**Expected Behavior:**
- Each test uses isolated container or container state
- No shared state pollution

## Cleanup

After each test:
- Container remains running (module-scoped fixture)
- Temporary files created during test are cleaned up

After all module tests:
- Container stopped and removed
- API keys cleared from memory

## Test Organization

**File:** `tests/integration/runners/test_runner_smoke.py`

**Markers:**
- `@pytest.mark.slow` - All smoke tests
- `@pytest.mark.claude` / `@pytest.mark.codex` / `@pytest.mark.gemini` - Platform-specific
- `@skipif_no_<runner>` - Auto-skip if API key missing

## Performance Targets

| Runner | Target Time | Warning Threshold | Timeout |
|--------|-------------|-------------------|---------|
| Claude | <20s | 30s | 60s |
| Codex | <20s | 30s | 60s |
| Gemini | <15s | 30s | 60s |
| **All** | <60s total | - | 180s |

## Related

- **Story:** [US-004](../../user-stories/US-004-smoke-tests-all-runners.md)
- **Research:** [06-e2e-testing-strategy.md](../../research/06-e2e-testing-strategy.md)
- **Contracts:** [01-runner-interface.md](../../api-contracts/01-runner-interface.md)
