# E2E Test Spec: Full Loop Execution Tests

**Related Stories:** US-005
**Priority:** Critical
**Status:** Draft

## Overview

End-to-end tests that run complete execution workflows with real runners, validating the entire agentic loop (Implementation → QA → Code Quality → Manager → DoD) works correctly on all platforms.

## Preconditions

- Authenticated container with all three CLIs installed
- Test project fixture (`tests/fixtures/projects/simple-python/`)
- Execution orchestrator available
- API keys configured for desired runners

## Test Feature: Add String Utilities

All full loop tests use this canonical feature for consistency:

```markdown
Task: Add String Utilities

Requirements:
- reverse_string(s: str) -> str
  - Returns reversed string
  - Handle empty strings

- capitalize_words(s: str) -> str
  - Capitalizes first letter of each word
  - Handles hyphenated words (e.g., "hello-world" → "Hello-World")

- Type hints + docstrings required
- Tests in test_utils.py must pass
- Code must pass ruff linting
```

**Why this feature:**
- Small scope (5-10 min for LLM to implement)
- Clear success criteria (tests pass, linting passes)
- Type hints test code quality gates
- Common enough that all LLMs know how to implement

## Test Cases

### TC-E2E-010: Full Loop Happy Path (Claude)

**Description:** Run complete execution loop with Claude Code runner on simple feature task.

**Steps:**
1. Initialize test project with empty `src/` directory
2. Create task specification for "Add String Utilities"
3. Run execution loop with Claude Code runner
4. Wait for completion (timeout: 15 minutes)
5. Validate at all 4 verification levels

**Expected Results:**

**Level 1: Process**
- Exit code: 0
- Loop phase: COMPLETED
- No exceptions raised

**Level 2: Artifacts**
- File exists: `src/utils.py`
- File exists: `tests/test_utils.py`
- `utils.py` contains `reverse_string` function
- `utils.py` contains `capitalize_words` function

**Level 3: Functional**
- `pytest tests/` returns 0 (all tests pass)
- `ruff check src/` returns 0 (no linting errors)
- Type hints present on function signatures
- Docstrings present on functions

**Level 4: Structured Output**
- State file shows `task_complete: True`
- State shows `current_phase: "completed"`
- At least 1 iteration logged
- No errors in iteration history

**Test Data:**
```python
task_spec = {
    "name": "Add String Utilities",
    "requirements": [
        "reverse_string(s: str) -> str",
        "capitalize_words(s: str) -> str",
        "Type hints and docstrings required",
        "Tests must pass"
    ]
}
```

**Assertions:**
```python
# Level 1
assert result.exit_code == 0
assert state["current_phase"] == "completed"

# Level 2
assert (project_dir / "src" / "utils.py").exists()
assert (project_dir / "tests" / "test_utils.py").exists()
utils_content = (project_dir / "src" / "utils.py").read_text()
assert "reverse_string" in utils_content
assert "capitalize_words" in utils_content

# Level 3
pytest_result = subprocess.run(["pytest", "tests/"], cwd=project_dir)
assert pytest_result.returncode == 0
ruff_result = subprocess.run(["ruff", "check", "src/"], cwd=project_dir)
assert ruff_result.returncode == 0
assert "def reverse_string(s: str) -> str:" in utils_content

# Level 4
assert state["task_complete"] is True
assert len(state["iterations"]) >= 1
```

**Markers:**
- `@pytest.mark.slow`
- `@pytest.mark.e2e`
- `@pytest.mark.claude`
- `@pytest.mark.timeout(900)` # 15 minutes

---

### TC-E2E-011: Full Loop Happy Path (Codex)

**Description:** Same as TC-E2E-010 but using Codex runner.

**Steps:** Same as TC-E2E-010

**Expected Results:** Same 4-level validation as TC-E2E-010

**Markers:**
- `@pytest.mark.slow`
- `@pytest.mark.e2e`
- `@pytest.mark.codex`
- `@pytest.mark.timeout(900)`

---

### TC-E2E-012: Full Loop Happy Path (Gemini)

**Description:** Same as TC-E2E-010 but using Gemini runner.

**Steps:** Same as TC-E2E-010

**Expected Results:** Same 4-level validation as TC-E2E-010

**Markers:**
- `@pytest.mark.slow`
- `@pytest.mark.e2e`
- `@pytest.mark.gemini`
- `@pytest.mark.timeout(900)`

---

### TC-E2E-013: QA Retry with Intentional Test Failures

**Description:** Verify QA agent detects test failures and implementer fixes them in retry iteration.

**Steps:**
1. Initialize test project
2. Create task spec with intentionally failing test fixture
3. Run execution loop
4. Verify first iteration fails QA
5. Verify second iteration fixes tests and passes QA

**Test Fixture:**
```python
# tests/test_utils.py (intentionally wrong)
def test_reverse_string():
    # This will fail initially
    assert reverse_string("hello") == "olleh"
    assert reverse_string("") == ""  # Edge case that might be missed
    assert False, "Intentional failure to trigger retry"
```

**Expected Results:**
- **Iteration 1:**
  - Implementation phase: SUCCESS (creates utils.py)
  - QA phase: FAILED (`dod_achieved: false`)
  - QA output includes `fix_info`: "Test assertion failed: Intentional failure"

- **Iteration 2:**
  - Implementation phase: SUCCESS (fixes test based on fix_info)
  - QA phase: SUCCESS (`dod_achieved: true`)
  - Final state: COMPLETED

**Assertions:**
```python
assert len(state["iterations"]) == 2
assert state["iterations"][0]["qa"]["dod_achieved"] is False
assert "fix_info" in state["iterations"][0]["qa"]
assert state["iterations"][1]["qa"]["dod_achieved"] is True
assert state["task_complete"] is True
```

---

### TC-E2E-014: Code Quality Retry with Missing Type Hints

**Description:** Verify code quality agent detects missing type hints and implementer adds them in retry.

**Steps:**
1. Initialize test project
2. Modify implementation prompt to skip type hints initially
3. Run execution loop
4. Verify first iteration fails code quality
5. Verify second iteration adds type hints and passes

**Expected Results:**
- **Iteration 1:**
  - Implementation: SUCCESS (but no type hints)
  - QA: SUCCESS (tests pass)
  - Code Quality: FAILED (`quality_passed: false`)
  - Code Quality includes `fix_info`: "Missing type annotation on reverse_string"

- **Iteration 2:**
  - Implementation: SUCCESS (adds type hints based on fix_info)
  - Code Quality: SUCCESS (`quality_passed: true`)
  - Final state: COMPLETED

**Assertions:**
```python
assert len(state["iterations"]) == 2
assert state["iterations"][0]["code_quality"]["quality_passed"] is False
assert "type annotation" in state["iterations"][0]["code_quality"]["fix_info"].lower()
assert state["iterations"][1]["code_quality"]["quality_passed"] is True
```

---

### TC-E2E-015: State Persistence and Resume After SIGTERM

**Description:** Verify execution state is saved and can resume after interruption.

**Steps:**
1. Initialize test project
2. Start execution loop in subprocess
3. Wait for implementer phase to complete (monitor state file)
4. Send SIGTERM to subprocess
5. Verify state file shows interrupted state
6. Resume execution from state file
7. Verify QA phase continues without re-running implementer

**Expected Results:**
- **After SIGTERM:**
  - State file exists
  - `current_phase`: "qa" or "paused"
  - `iterations[0].implementation`: Shows completion
  - `iterations[0].qa`: Not yet run

- **After Resume:**
  - QA phase runs (reads existing implementation)
  - Implementer NOT re-run
  - Iteration count matches (no duplicate iterations)
  - Final state: COMPLETED

**Assertions:**
```python
# After interrupt
interrupted_state = load_state_file()
assert interrupted_state["iterations"][0]["implementation"]["status"] == "success"
assert "qa" not in interrupted_state["iterations"][0] or interrupted_state["iterations"][0]["qa"] is None

# After resume
resumed_state = load_state_file()
assert resumed_state["iterations"][0]["qa"]["dod_achieved"] is True
assert len(resumed_state["iterations"]) == 1  # Not duplicated
assert resumed_state["task_complete"] is True
```

---

### TC-E2E-016: Max Iterations Termination

**Description:** Verify loop terminates gracefully when max iterations is reached without success.

**Steps:**
1. Initialize test project
2. Configure max_iterations=2
3. Create impossible task (forces QA to always fail)
4. Run execution loop
5. Verify loop stops after 2 iterations with FAILED state

**Test Data:**
```python
max_iterations = 2

# Test fixture with impossible assertion
test_fixture = """
def test_always_fails():
    assert 1 + 1 == 3, "This test will always fail"
"""

impossible_task = {
    "requirements": [
        "Create src/impossible.py with any implementation",
        "Tests in test_impossible.py must pass"
    ],
    "test_fixture": test_fixture  # Pre-written test that cannot pass
}
```

**Expected Results:**
- Exactly 2 iterations run
- Both iterations: QA fails
- Final state: FAILED
- Failure reason includes "max iterations reached"

**Assertions:**
```python
assert len(state["iterations"]) == 2
assert state["current_phase"] == "failed"
assert "max iterations" in state["failure_reason"].lower()
```

---

## Edge Cases

### 1. Malformed Agent JSON Output

**Trigger:** Agent returns text without structured JSON

**Expected Behavior:**
- Loop continues with warning logged
- `structured_output`: None
- Defaults used for missing fields
- Loop doesn't crash

### 2. File Permission Errors

**Trigger:** Container can't write to mounted volume

**Expected Behavior:**
- Clear error message: "Permission denied writing to /path/to/file"
- State saved before failure
- Exit code: non-zero
- Error details in state file

### 3. CLI Crashes Mid-Execution

**Trigger:** CLI process killed unexpectedly

**Expected Behavior:**
- RunnerResult with `success: False`
- Error message includes CLI exit code/signal
- State shows iteration as failed
- Loop can retry if iterations remaining

## Cleanup

After each test:
- Test project directory removed
- State files cleared
- Container processes terminated cleanly

After all tests:
- Authenticated container stopped
- Temporary volumes removed

## Test Organization

**File:** `tests/integration/runners/test_runner_full_loop.py`

**Parametrization:**
```python
@pytest.mark.parametrize("runner_type", [
    pytest.param("claude", marks=pytest.mark.claude),
    pytest.param("codex", marks=pytest.mark.codex),
    pytest.param("gemini", marks=pytest.mark.gemini),
])
def test_full_loop_happy_path(authenticated_container, runner_type):
    ...
```

## Performance Targets

| Test Case | Estimated Time | Timeout |
|-----------|---------------|---------|
| TC-E2E-010 (Claude) | 5-10 min | 15 min |
| TC-E2E-011 (Codex) | 5-10 min | 15 min |
| TC-E2E-012 (Gemini) | 5-10 min | 15 min |
| TC-E2E-013 (Retry) | 10-15 min | 20 min |
| TC-E2E-014 (Quality) | 10-15 min | 20 min |
| TC-E2E-015 (Resume) | 10-15 min | 20 min |
| TC-E2E-016 (Max iter) | 10-15 min | 20 min |
| **Total** | 55-95 min | - |

## Cost Estimates

Per full test run (all runners, all test cases):
- Claude (Haiku): $0.15-0.30
- Codex (GPT-4o-mini): $0.10-0.20
- Gemini (Flash): $0.05-0.15
- **Total: ~$0.30-0.65**

## Related

- **Story:** [US-005](../../user-stories/US-005-full-loop-e2e-tests.md)
- **Research:** [06-e2e-testing-strategy.md](../../research/06-e2e-testing-strategy.md)
- **Contracts:** [02-agent-output-contracts.md](../../api-contracts/02-agent-output-contracts.md)
