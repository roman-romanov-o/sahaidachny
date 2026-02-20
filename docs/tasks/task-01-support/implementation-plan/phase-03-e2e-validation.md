# Phase 03: E2E Validation

**Status:** Not Started
**Estimated Effort:** M (6-8 hours)
**Dependencies:** Phase 02 (test infrastructure and smoke tests passing)

## Objective

Write comprehensive end-to-end tests that validate the complete execution workflow (Implementer → QA → Code Quality → Manager → DoD) works correctly on all three platforms, with 4-level verification and recovery scenarios.

## Scope

### Stories Included

| Story | Priority | Complexity | Estimated Hours |
|-------|----------|------------|-----------------|
| US-005: Full Loop E2E Tests | Must Have | L | 6-8h |

**Total: 6-8 hours**

### Out of Scope (Deferred to Later Phases)

- US-006: Graceful degradation (Phase 4)
- US-007: Error messages (Phase 4)

## Implementation Steps

### Step 1: Create Test Project Fixture

**Description:** Build a reusable test project fixture with a simple feature that exercises the full agentic loop.

**Files to Create:**
- `tests/fixtures/projects/simple-python/` - Test project template
- `tests/fixtures/projects/simple-python/README.md` - Project description
- `tests/fixtures/projects/simple-python/pyproject.toml` - Python project config
- `tests/fixtures/projects/simple-python/.gitignore` - Git ignore file

**Test Project Requirements:**
```markdown
# Simple Python Project

A minimal Python project for testing Sahaidachny execution loop.

## Test Feature: String Utilities

Implement string utility functions:
- `reverse_string(s: str) -> str` - Reverse a string
- `capitalize_words(s: str) -> str` - Capitalize first letter of each word

Requirements:
- Type hints required
- Docstrings required
- Tests in test_utils.py must pass
- Ruff and ty checks must pass

Why this works:
- Small scope (5-10 min for LLM)
- Clear success criteria (tests pass)
- Type hints test quality gates
- Common enough all LLMs know how
```

**Fixture pattern:**
```python
# tests/integration/runners/conftest.py
import shutil
import pytest
from pathlib import Path

@pytest.fixture
def test_project(tmp_path):
    """Create a test project from template."""
    template = Path("tests/fixtures/projects/simple-python")
    project = tmp_path / "test-project"
    shutil.copytree(template, project)
    return project
```

**Acceptance Criteria:**
- [ ] Test project template created with pyproject.toml
- [ ] Project has clear requirements document
- [ ] Fixture copies template to tmp_path for each test
- [ ] Project is small enough for LLM (<10 min implementation)

---

### Step 2: Write Full Loop Happy Path Tests

**Description:** Write E2E tests that validate the complete execution loop works correctly on all three platforms.

**Files to Create:**
- `tests/integration/runners/test_runner_full_loop.py` - Full loop tests

**Test Pattern:**

**TC-E2E-010: Full loop happy path (all runners)**
```python
import pytest
from saha.orchestrator import AgenticLoop
from pathlib import Path

@pytest.mark.slow
@pytest.mark.parametrize("runner_type", ["claude", "codex", "gemini"])
@pytest.mark.timeout(600)  # 10 minutes
def test_full_loop_happy_path(authenticated_container, test_project, runner_type):
    """
    Full loop test: Implementer → QA → Quality → Manager → DoD.

    Validates complete workflow with 4-level verification:
    1. Process: Exit code 0
    2. Artifacts: Files created (utils.py, tests)
    3. Functional: Tests pass, quality checks pass
    4. Structured: State shows task_complete=True
    """
    # Skip if API key missing
    if runner_type == "claude" and not has_anthropic_key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    # ... (similar for codex, gemini)

    # Run execution loop
    loop = AgenticLoop(
        task_path=test_project,
        runner_type=runner_type,
        max_iterations=3,
    )

    result = loop.run()

    # Level 1: Process
    assert result.exit_code == 0, "Loop failed"

    # Level 2: Artifacts
    utils_file = test_project / "utils.py"
    assert utils_file.exists(), "utils.py not created"

    utils_content = utils_file.read_text()
    assert "reverse_string" in utils_content
    assert "capitalize_words" in utils_content

    test_file = test_project / "test_utils.py"
    assert test_file.exists(), "test_utils.py not created"

    # Level 3: Functional
    pytest_result = loop.run_tests()
    assert pytest_result.passed == pytest_result.total, "Tests failed"

    ruff_result = loop.run_ruff_check()
    assert len(ruff_result.issues) == 0, "Ruff issues found"

    ty_result = loop.run_ty_check()
    assert ty_result.success, "Type checking failed"

    # Level 4: Structured output
    state = loop.get_state()
    assert state["task_complete"] == True
    assert len(state["iterations"]) >= 1
    assert state["current_phase"] == "completed"
```

**Acceptance Criteria:**
- [ ] Test passes on Claude runner (TC-E2E-011)
- [ ] Test passes on Codex runner (TC-E2E-012)
- [ ] Test passes on Gemini runner (TC-E2E-013)
- [ ] All 4 verification levels pass for each runner
- [ ] Test completes in <10 minutes per runner
- [ ] Proper parametrization across runners

**Tests:**
- TC-E2E-010: Full loop verification structure
- TC-E2E-011: Claude full loop happy path
- TC-E2E-012: Codex full loop happy path

---

### Step 3: Write QA Retry Tests

**Description:** Write tests that validate QA failure recovery with fix_info.

**Test Case:**

**TC-E2E-013: QA retry with fix_info**
```python
@pytest.mark.slow
@pytest.mark.parametrize("runner_type", ["claude", "codex", "gemini"])
@pytest.mark.timeout(900)  # 15 minutes (2 iterations)
def test_full_loop_qa_retry(authenticated_container, test_project, runner_type):
    """
    QA failure recovery: Implementer creates failing test,
    QA detects failure, provides fix_info, second iteration fixes.
    """
    # Inject intentionally failing test
    test_file = test_project / "test_utils.py"
    test_file.write_text("""
def test_reverse_string():
    assert False, "Intentional failure for testing retry"
""")

    loop = AgenticLoop(
        task_path=test_project,
        runner_type=runner_type,
        max_iterations=3,
    )

    result = loop.run()

    # Verify second iteration fixed the issue
    assert result.exit_code == 0
    state = loop.get_state()
    assert len(state["iterations"]) == 2, "Should take 2 iterations"
    assert state["iterations"][0]["qa_result"]["dod_achieved"] == False
    assert state["iterations"][1]["qa_result"]["dod_achieved"] == True

    # Verify fix_info was provided
    fix_info = state["iterations"][1]["fix_info"]
    assert fix_info is not None
    assert "test" in fix_info.lower() or "fail" in fix_info.lower()
```

**Acceptance Criteria:**
- [ ] Test passes on all three runners
- [ ] Second iteration successfully fixes failing tests
- [ ] fix_info is populated and useful
- [ ] State correctly tracks iteration count

**Tests:**
- TC-E2E-013: QA retry with fix_info (all runners)

---

### Step 4: Write Code Quality Retry Tests

**Description:** Write tests that validate code quality failure recovery.

**Test Case:**

**TC-E2E-014: Code quality retry**
```python
@pytest.mark.slow
@pytest.mark.parametrize("runner_type", ["claude", "codex", "gemini"])
@pytest.mark.timeout(900)  # 15 minutes
def test_full_loop_code_quality_retry(authenticated_container, test_project, runner_type):
    """
    Code quality failure recovery: Missing type hints detected,
    second iteration adds them.
    """
    # Pre-populate utils.py without type hints
    utils_file = test_project / "utils.py"
    utils_file.write_text("""
def reverse_string(s):  # Missing type hints
    return s[::-1]

def capitalize_words(s):  # Missing type hints
    return s.title()
""")

    loop = AgenticLoop(
        task_path=test_project,
        runner_type=runner_type,
        max_iterations=3,
    )

    result = loop.run()

    # Verify second iteration added type hints
    assert result.exit_code == 0
    state = loop.get_state()
    assert len(state["iterations"]) == 2

    # Verify type hints added
    final_content = utils_file.read_text()
    assert "-> str" in final_content, "Return type hints missing"
    assert ": str" in final_content, "Parameter type hints missing"
```

**Acceptance Criteria:**
- [ ] Test passes on all three runners
- [ ] Second iteration successfully adds type hints
- [ ] Code quality checks pass after retry

**Tests:**
- TC-E2E-014: Code quality retry (all runners)

---

### Step 5: Write State Resumption Tests

**Description:** Write tests that validate execution can be stopped and resumed.

**Test Case:**

**TC-E2E-015: State resume after SIGTERM**
```python
import signal
import os
import time
from multiprocessing import Process

@pytest.mark.slow
@pytest.mark.parametrize("runner_type", ["claude"])  # Only test on Claude for speed
@pytest.mark.timeout(600)
def test_full_loop_state_resume(authenticated_container, test_project, runner_type):
    """
    State resumption: Stop execution after implementer,
    resume from saved state, QA continues without re-running implementer.
    """
    def run_loop_with_interrupt(project_path, runner):
        """Run loop, interrupt after implementer phase."""
        loop = AgenticLoop(
            task_path=project_path,
            runner_type=runner,
            max_iterations=3,
        )

        # Hook to interrupt after implementer
        original_run_qa = loop._run_qa_agent

        def run_qa_with_interrupt(*args, **kwargs):
            # Save state before QA
            loop.save_state()
            # Interrupt
            os.kill(os.getpid(), signal.SIGTERM)

        loop._run_qa_agent = run_qa_with_interrupt

        try:
            loop.run()
        except SystemExit:
            pass  # Expected from SIGTERM

    # Run in subprocess to handle SIGTERM
    p = Process(target=run_loop_with_interrupt, args=(test_project, runner_type))
    p.start()
    p.join(timeout=300)

    # Verify state was saved
    state_file = test_project / ".sahaidachny" / "execution-state.json"
    assert state_file.exists(), "State not saved"

    # Resume execution
    loop = AgenticLoop(
        task_path=test_project,
        runner_type=runner_type,
        max_iterations=3,
    )

    result = loop.resume()

    # Verify QA ran but implementer did not re-run
    assert result.exit_code == 0
    state = loop.get_state()
    assert len(state["iterations"]) == 1, "Should not create new iteration"
    assert state["current_phase"] == "completed"
```

**Acceptance Criteria:**
- [ ] Test saves state after implementer phase
- [ ] Test resumes from saved state
- [ ] QA phase runs without re-running implementer
- [ ] Iteration count remains correct

**Tests:**
- TC-E2E-015: State resume after SIGTERM

---

### Step 6: Performance and Cost Validation

**Description:** Validate performance targets and cost estimates from research.

**Performance Validation:**
```python
@pytest.mark.slow
def test_performance_targets(test_results):
    """Verify performance targets are met."""
    # Unit tests
    unit_duration = get_test_duration("tests/unit/")
    assert unit_duration < 10, f"Unit tests too slow: {unit_duration}s"

    # Smoke tests
    smoke_duration = get_test_duration("tests/integration/ -k smoke")
    assert smoke_duration < 120, f"Smoke tests too slow: {smoke_duration}s"

    # Full loop per runner
    for runner in ["claude", "codex", "gemini"]:
        loop_duration = get_test_duration(f"tests/integration/ -k full_loop -k {runner}")
        assert loop_duration < 600, f"{runner} full loop too slow: {loop_duration}s"
```

**Cost Tracking:**
```python
def track_test_cost(runner_type, result):
    """Track API costs for tests."""
    cost_estimates = {
        "claude": 0.15,  # Haiku per test
        "codex": 0.10,   # GPT-4o-mini per test
        "gemini": 0.05,  # Gemini Flash per test
    }

    estimated_cost = cost_estimates.get(runner_type, 0)
    print(f"Estimated cost for {runner_type}: ${estimated_cost:.2f}")
```

**Acceptance Criteria:**
- [ ] Unit tests complete in <10s
- [ ] Smoke tests complete in <2 min total
- [ ] Full loop tests complete in <10 min per runner
- [ ] Total cost per test run <$0.65

## Definition of Done

Phase is complete when:
- [ ] **Test project fixture created:** Simple Python project with clear requirements
- [ ] **Happy path tests pass:** All 3 runners complete full loop successfully (TC-E2E-011 to TC-E2E-013)
- [ ] **QA retry works:** All 3 runners handle test failures with fix_info (TC-E2E-013)
- [ ] **Code quality retry works:** All 3 runners add type hints on retry (TC-E2E-014)
- [ ] **State resumption works:** Claude runner resumes execution from saved state (TC-E2E-015)
- [ ] **4-level verification passes:** Process, Artifacts, Functional, Structured checks pass
- [ ] **Performance targets met:** Tests complete within time budgets
- [ ] **Cost estimates validated:** Actual costs match research estimates

**Quality Gates:**
```bash
# Run all E2E tests
pytest tests/integration/runners/test_runner_full_loop.py -v

# Run only happy path (faster validation)
pytest tests/integration/runners/test_runner_full_loop.py -k "happy_path" -v

# Check performance
pytest tests/ --durations=0 | grep "test_full_loop"

# Track costs
pytest tests/integration/runners/ -v --log-cli-level=INFO | grep "Estimated cost"
```

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Tests take >15 min per runner (too slow) | Medium | High | Optimize test feature; use smaller models; parallelize |
| LLM non-determinism causes flaky tests | High | Medium | Use clear requirements; retry logic; accept minor variations |
| API costs higher than estimated | Medium | Medium | Monitor actual costs; use cheaper models; limit test runs |
| State resumption complex to test | High | Medium | Simplify test with mocked interrupt; manual validation |
| One runner consistently slower | Medium | Low | Document performance differences; adjust timeouts |

## Notes

**Why "add string utils" feature:**
- Small enough to complete quickly (5-10 min)
- Clear success criteria (tests pass, type hints present)
- Common enough all LLMs understand
- Exercises all phases (implement, test, quality, manage)
- Representative of real Sahaidachny usage

**4-level verification strategy:**
1. **Process:** Exit code, no crashes
2. **Artifacts:** Files created with expected content
3. **Functional:** Tests pass, quality checks pass
4. **Structured:** State object has expected shape

**LLM non-determinism handling:**
- Accept minor variations in implementation
- Focus on functional outcomes (tests pass) not exact code
- Use clear, unambiguous requirements
- Allow 2-3 retries for flaky tests

**Cost optimization:**
- Use smallest models that work (Haiku, GPT-4o-mini, Flash)
- Run expensive tests less frequently (nightly vs per-commit)
- Parallelize when possible (independent runner tests)

## Related

- **Stories:** [US-005](../user-stories/US-005-full-loop-e2e-tests.md)
- **Research:** [06-e2e-testing-strategy.md](../research/06-e2e-testing-strategy.md)
- **Test Specs:** [e2e/02-full-loop-execution.md](../test-specs/e2e/02-full-loop-execution.md)
- **Previous Phase:** [Phase 02: Test Infrastructure](phase-02-test-infrastructure.md)
- **Next Phase:** [Phase 04: Error Handling](phase-04-error-handling.md)
