# US-004: Write Smoke Tests for All Runners

**Priority:** Must Have
**Status:** Draft
**Persona:** Test Engineer
**Estimated Complexity:** S (2-3 hours)

## User Story

As a **Test Engineer**,
I want to **write smoke tests that validate basic functionality of all three runners**,
So that **we can quickly detect if any runner is broken before running expensive full loop tests**.

## Acceptance Criteria

1. **Given** Claude Code runner and authenticated container
   **When** smoke test runs a simple agent invocation (e.g., "echo hello")
   **Then** runner succeeds, returns output, completes successfully (pytest timeout: 60s, warning logged if >30s)

2. **Given** Codex runner and authenticated container
   **When** smoke test runs a simple agent invocation
   **Then** runner succeeds, returns output, completes successfully (pytest timeout: 60s, warning logged if >30s)

3. **Given** Gemini runner and authenticated container
   **When** smoke test runs a simple agent invocation
   **Then** runner succeeds, returns output, completes successfully (pytest timeout: 60s, warning logged if >30s)

4. **Given** any runner smoke test
   **When** test completes successfully
   **Then** structured output includes expected fields (success, output, exit_code)

5. **Given** API key is missing for a runner
   **When** smoke test for that runner is run
   **Then** test is skipped (not failed) with clear message

## Edge Cases

1. **CLI not installed**
   - Trigger: Docker container doesn't have CLI installed
   - Expected behavior: Test skipped with message "CLI not available"

2. **API rate limiting**
   - Trigger: Too many requests hit rate limit
   - Expected behavior: Test retries with exponential backoff (max 3 retries)

3. **Network timeout**
   - Trigger: Network connection slow or unavailable
   - Expected behavior: Test fails with clear timeout message (not generic error)

## Technical Notes

**From research (06-e2e-testing-strategy.md):**

**Smoke test characteristics:**
- Fast: <30 seconds per runner
- Simple: Minimal agent invocation (no complex tasks)
- Independent: Each runner tested separately
- Frequent: Run on every code change

**Test structure:**
```python
@pytest.mark.slow
@pytest.mark.claude
@skipif_no_claude
def test_claude_runner_smoke(authenticated_container):
    """Smoke test: Claude runner basic invocation."""
    runner = ClaudeRunner(working_dir=Path("/root/test"))
    result = runner.run_prompt("Say hello")

    assert result.success
    assert result.output
    assert "hello" in result.output.lower()
```

**Test organization:**
- `tests/integration/runners/test_claude_runner_real.py`
- `tests/integration/runners/test_codex_runner_real.py`
- `tests/integration/runners/test_gemini_runner_real.py`

**Pytest markers:**
- `@pytest.mark.slow` - Indicate test uses real API calls
- `@pytest.mark.claude` / `@pytest.mark.codex` / `@pytest.mark.gemini` - Filter by platform
- `@skipif_no_<runner>` - Auto-skip if API key missing

**Verification levels (from research):**
1. Process: Exit code 0, no errors
2. Artifacts: Output exists and non-empty
3. Functional: Response contains expected keywords
4. Structured: RunnerResult fields populated correctly

## Dependencies

- **Requires:**
  - US-003 completed (Authenticated container infrastructure)
  - US-001 completed (Codex validation)
  - US-002 completed (Gemini fixes)
- **Enables:**
  - US-005 (Full loop E2E tests)
  - US-006 (Error handling validation)

## Questions

- [ ] Should smoke tests use real agent specs or just simple prompts?
- [ ] What's the acceptable timeout for smoke tests? (30s? 60s?)
- [ ] Should we test all models or just default ones?

## Related

- Task: [task-description.md](../task-description.md)
- Research: [06-e2e-testing-strategy.md](../research/06-e2e-testing-strategy.md)
- User Story: [US-003](US-003-authenticated-container-infrastructure.md)
