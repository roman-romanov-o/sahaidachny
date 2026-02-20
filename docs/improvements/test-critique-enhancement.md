# Test Critique Enhancement Summary

## Overview

Enhanced the test-critique agent from a single-dimension check (mocking only) to a **comprehensive 5-dimension quality analysis** with strict standards.

## Previous State (v0.1.0)

**Single Focus:** Over-mocking detection
- ❌ Detected hollow tests (everything mocked)
- ❌ Detected SUT being mocked
- ❌ Detected placeholder tests
- ✅ Basic but incomplete

**Pass/Fail:** Scores A/B/C passed, D/F failed

## Enhanced State (v0.2.0)

**Five Quality Dimensions:**

### 1. Mocking & Test Doubles (Weight: 30%)
**Focus:** Are we testing real code or just mocks?

**Detects:**
- Over-mocking (>3 mocks per test)
- Mocking the SUT (testing a mock instead of real code)
- Mock-only assertions (only checking `assert_called`, not outcomes)

### 2. Assertion Quality (Weight: 25%) ⭐ NEW
**Focus:** Do assertions actually catch bugs?

**Detects:**
- **Vague assertions:** `assert result is not None`, `assert len(items) > 0`
- **Incomplete assertions:** Only checking one field when multiple matter
- **Always-true assertions:** `assert True`, `assert isinstance(x, X)`
- **Implementation assertions:** Testing internal method calls, not behavior
- **Missing negative assertions:** Only happy path, no error cases

**Examples:**
```python
# BAD: Vague
assert user is not None

# GOOD: Specific
assert user.email == "john@test.com"
assert user.id is not None
assert user.created_at is not None
assert user.is_active is True
```

### 3. Test Structure & Clarity (Weight: 20%) ⭐ NEW
**Focus:** Are tests maintainable and understandable?

**Detects:**
- **Unclear test names:** `test_case_1`, `test_user`, generic names
- **Missing AAA structure:** Arrange/Act/Assert all mixed
- **Complex tests:** >50 lines, nested logic, multiple actions
- **Magic values:** Unexplained numbers/strings

**Examples:**
```python
# BAD: Unclear name and structure
def test_user():
    u = User("john@test.com", "pass")
    u.save()
    assert u.id == 42  # Why 42?

# GOOD: Clear name and AAA structure
def test_user_email_can_be_updated_after_creation():
    # Arrange
    user = create_user(email="john@test.com")
    new_email = "new@test.com"

    # Act
    user.update(email=new_email)

    # Assert
    assert user.email == new_email
    assert_email_sent_to(new_email)
```

### 4. Coverage Quality (Weight: 15%) ⭐ NEW
**Focus:** Do we test edge cases and error paths?

**Detects:**
- **Only happy path:** No error cases, edge cases
- **Missing edge cases:** Empty lists, null values, boundary conditions
- **No exception testing:** Functions that can raise exceptions not tested
- **Missing test coverage:** Changed production files without ANY tests (critical)

**Examples:**
```python
# BAD: Only happy path
def test_divide():
    assert divide(10, 2) == 5

# GOOD: Multiple cases
def test_divide_success():
    assert divide(10, 2) == 5
    assert divide(0, 5) == 0

def test_divide_by_zero_raises_error():
    with pytest.raises(ValueError, match="division by zero"):
        divide(10, 0)
```

### 5. Test Independence & Stability (Weight: 10%) ⭐ NEW
**Focus:** Are tests reliable and isolated?

**Detects:**
- **Shared state:** Tests depend on order or global state
- **Flaky patterns:** `time.sleep()`, `random()`, timing dependencies
- **Missing cleanup:** Creating files/data without teardown
- **Hard-coded timing:** `sleep(5)` hoping something completes

**Examples:**
```python
# BAD: Flaky timing
def test_async_job():
    trigger_job()
    time.sleep(5)  # Hope it finishes
    assert job_completed()

# GOOD: Proper waiting
def test_async_job():
    job_id = trigger_job()
    wait_for_job(job_id, timeout=30)
    assert job_status(job_id) == "completed"
```

## Critical New Feature: Coverage Detection

**Before running quality checks, verify all changed production files have tests:**

1. Get `files_changed` from context
2. For each production file, find corresponding test file
3. **Flag missing coverage as CRITICAL** - blocks QA
4. Report `files_with_coverage` and `files_missing_coverage`

**Example:**
```json
{
  "severity": "critical",
  "file": "saha/pipeline/factory.py",
  "pattern": "missing_tests",
  "description": "PipelineFactory class (358 lines) has NO test coverage",
  "missing_tests": ["create_pipeline()", "cancel_response()"]
}
```

## Stricter Pass/Fail Standards

**OLD:** A/B/C passed, D/F failed
**NEW:** Only A/B pass, C/D/F fail

**Rationale:** We don't accept mediocrity. C grade means "acceptable but needs improvement" - we want excellent tests.

## Enhanced Output Schema

### New Fields

```python
class DimensionScores(BaseModel):
    """Quality scores for each dimension."""
    mocking: TestQualityScore
    assertions: TestQualityScore  # NEW
    structure: TestQualityScore   # NEW
    coverage: TestQualityScore    # NEW
    independence: TestQualityScore # NEW

class TestCritiqueOutput(BaseModel):
    # ... existing fields ...
    dimension_scores: DimensionScores | None  # NEW
    files_with_coverage: list[str] | None     # NEW
    files_missing_coverage: list[str] | None  # NEW
```

### Extended Patterns

**Old patterns:**
- `over_mocking`, `mocking_sut`, `placeholder`

**New patterns (18 total):**
- **Mocking:** over_mocking, mocking_sut
- **Assertions:** vague_assertion, incomplete_assertion, always_true, brittle_assertion, missing_negative
- **Structure:** unclear_name, no_aaa_structure, complex_test, magic_values
- **Coverage:** only_happy_path, missing_edge_cases, no_exception_tests, missing_tests
- **Independence:** flaky_timing, shared_state, missing_cleanup, random_values

## Scoring Algorithm

```python
weighted_score = (
    mocking_score * 0.30 +
    assertions_score * 0.25 +
    structure_score * 0.20 +
    coverage_score * 0.15 +
    independence_score * 0.10
)

# Map to grade
if weighted_score >= 4.5: grade = A
elif weighted_score >= 3.5: grade = B
elif weighted_score >= 2.5: grade = C
elif weighted_score >= 1.5: grade = D
else: grade = F

# Only A and B pass
critique_passed = grade in ["A", "B"]
```

## Example Output Comparison

### OLD (v0.1.0)
```json
{
  "critique_passed": true,
  "test_quality_score": "C",
  "tests_analyzed": 15,
  "summary": "Some over-mocking but acceptable"
}
```
**Problem:** Would pass even with vague assertions, no edge cases, flaky tests!

### NEW (v0.2.0)
```json
{
  "critique_passed": false,
  "test_quality_score": "C",
  "tests_analyzed": 15,
  "files_with_coverage": ["saha/auth.py"],
  "files_missing_coverage": ["saha/factory.py"],
  "dimension_scores": {
    "mocking": "B",
    "assertions": "C",
    "structure": "B",
    "coverage": "F",
    "independence": "B"
  },
  "issues": [
    {
      "severity": "critical",
      "file": "saha/factory.py",
      "pattern": "missing_tests",
      "dimension": "coverage",
      "description": "PipelineFactory has NO test coverage"
    }
  ],
  "fix_info": "C grade does not meet the bar (only A/B pass)..."
}
```
**Better:** Comprehensive analysis with actionable feedback!

## Impact on Execution Loop

**Before Enhancement:**
1. Implementation writes code + hollow tests
2. Test critique: "Some mocking but OK" ✅
3. QA runs tests: All pass! ✅
4. **Production:** Code is broken 💥

**After Enhancement:**
1. Implementation writes code + hollow tests
2. Test critique: "D grade - vague assertions, missing edge cases, SUT mocked" ❌
3. **Loop blocks** - must fix tests first
4. Implementation fixes tests to be comprehensive
5. Test critique: "B grade - good quality" ✅
6. QA runs tests: Tests actually verify behavior ✅
7. **Production:** Code works correctly ✨

## Files Changed

### Agent Definitions
- `.claude/agents/execution-test-critique.md` - Enhanced with 5 dimensions
- `claude_plugin/agents/execution-test-critique.md` - Synced

### Schemas
- `saha/schemas/agent_outputs.py`:
  - Added `DimensionScores` model
  - Extended `TestCritiqueIssue` with more patterns and `dimension` field
  - Enhanced `TestCritiqueOutput` with dimension_scores, files_with_coverage

### Skills
- `.claude/skills/test-critique/SKILL.md` - Updated description to v0.2.0

## Benefits

1. **Prevents false confidence** - Catches hollow tests before they give false security
2. **Improves test quality** - Forces comprehensive, maintainable tests
3. **Catches more bugs** - Edge cases, error paths, negative tests required
4. **Reduces flakiness** - Detects timing issues, shared state
5. **Better maintainability** - Clear structure, good naming, simple tests
6. **Enforces coverage** - All changed files must have tests

## Migration Notes

**Backward Compatible:** Existing tests won't break, but may now fail critique with stricter standards.

**Expected Impact:**
- More tests will fail critique initially (good thing!)
- Teams will need to improve test quality to reach A/B grade
- Long-term: Much higher quality test suites

## Next Steps

1. ✅ Deploy enhanced agent
2. Monitor first few runs to tune weights
3. Consider adding language-specific patterns (JS/TS specific checks)
4. Add performance test detection (tests that should be marked `@slow`)
5. Consider integration with coverage tools (pytest-cov, c8)
