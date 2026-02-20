# US-005: Write Full Loop E2E Tests

**Priority:** Must Have
**Status:** Draft
**Persona:** Test Engineer
**Estimated Complexity:** L (6-8 hours)

## User Story

As a **Test Engineer**,
I want to **write E2E tests that run complete execution workflows with real runners**,
So that **we can validate the entire agentic loop (implementer → qa → quality → manager → dod) works correctly on all platforms**.

## Acceptance Criteria

1. **Given** authenticated container with any runner (Claude/Codex/Gemini)
   **When** full loop test runs with simple feature task (e.g., "add string utils")
   **Then** loop completes successfully: Implementation → QA → Code Quality → Manager → DoD

2. **Given** full loop test completes
   **When** verifying results
   **Then** all verification levels pass:
   - Process: Exit code 0
   - Artifacts: Required files created (utils.py, tests)
   - Functional: pytest passes, ruff passes, type hints present
   - Structured: state shows task_complete=True

3. **Given** test fixture with intentionally failing tests (e.g., assert False)
   **When** QA runs and detects test failures
   **Then** implementer is called with fix_info and second iteration fixes tests and passes QA

4. **Given** test fixture with intentional code quality issues (e.g., missing type hints)
   **When** code quality runs and detects issues
   **Then** implementer is called with fix_info and second iteration adds type hints and passes quality

5. **Given** execution is interrupted via SIGTERM after implementer phase completes
   **When** test resumes execution from saved state file
   **Then** QA phase continues without re-running implementer, state shows correct iteration count

## Edge Cases

1. **Max iterations reached**
   - Trigger: QA/quality keep failing beyond max_iterations
   - Expected behavior: Loop terminates, state shows FAILED with clear reason

2. **Agent returns malformed JSON**
   - Trigger: Runner returns text without structured output
   - Expected behavior: Loop continues with warning, uses default values

3. **File permission errors**
   - Trigger: Container can't write to mounted volume
   - Expected behavior: Clear error message about permission issue

## Technical Notes

**From research (06-e2e-testing-strategy.md):**

**Test feature: Add String Utilities**
```markdown
Task: Add String Utilities

Requirements:
- reverse_string(s: str) -> str
- capitalize_words(s: str) -> str
- Type hints + docstrings required
- Tests in test_utils.py must pass

Why this works:
- Small scope (5-10 min for LLM)
- Clear success criteria (tests pass)
- Type hints test quality gates
- Common enough all LLMs know how
```

**4-level verification (from research):**
```python
# Level 1: Process
assert result.exit_code == 0

# Level 2: Artifacts
assert (project_dir / "utils.py").exists()
assert "reverse_string" in utils_content
assert "capitalize_words" in utils_content

# Level 3: Functional
assert pytest_run.passed == pytest_run.total
assert ruff_check.issues == []
assert has_type_hints(utils_content)

# Level 4: Structured output
assert state["task_complete"] == True
assert len(state["iterations"]) >= 1
assert state["current_phase"] == "completed"
```

**Test organization:**
- `tests/integration/runners/test_runner_full_loop.py` - Main full loop tests
- Parameterize across runners: `@pytest.mark.parametrize("runner", [claude, codex, gemini])`
- Use test project fixture from `tests/fixtures/projects/simple-python/`

**Estimated timing:**
- Happy path: 5-10 minutes per runner
- With retries: 10-15 minutes per runner
- All runners: 30-45 minutes total

**Cost estimate (per test run):**
- Claude: $0.15-0.30 (haiku)
- Codex: $0.10-0.20 (gpt-4o-mini)
- Gemini: $0.05-0.15 (gemini-flash)
- **Total: ~$0.30-0.65 per full test run**

## Dependencies

- **Requires:**
  - US-003 completed (Authenticated container infrastructure)
  - US-004 completed (Smoke tests pass)
  - US-001 completed (Codex validated)
  - US-002 completed (Gemini fixed)
- **Enables:**
  - High confidence in multi-platform support
  - Validation for production deployment

## Questions

- [ ] Should we test all runners in parallel or sequentially?
- [ ] What's the acceptable total test time? (30 min? 1 hour?)
- [ ] Should we test multiple feature variations or just one canonical task?
- [ ] How often should these tests run? (per-commit, nightly, weekly?)

## Related

- Task: [task-description.md](../task-description.md)
- Research: [06-e2e-testing-strategy.md](../research/06-e2e-testing-strategy.md)
- User Story: [US-003](US-003-authenticated-container-infrastructure.md)
- User Story: [US-004](US-004-smoke-tests-all-runners.md)
