---
name: test-critique
description: |
  Comprehensive test quality analysis across 5 dimensions. Use when:
  - Reviewing test implementations before QA
  - Verifying tests actually test real behavior
  - Detecting over-mocking, poor assertions, missing edge cases
  - Identifying flaky patterns and test smells
version: 0.2.0
globs:
  - "**/test_*.py"
  - "**/*_test.py"
  - "**/tests/**/*.py"
  - "**/__tests__/**/*.{ts,tsx,js,jsx}"
  - "**/*.test.{ts,tsx,js,jsx}"
  - "**/*.spec.{ts,tsx,js,jsx}"
---

# Test Quality Critique (Enhanced)

This skill provides **comprehensive test quality analysis** across five dimensions to identify tests that give **false confidence** or have other quality issues.

## The Problem

Bad tests are worse than no tests:
- **Hollow tests** pass when the real code is broken (false confidence)
- **Poor assertions** don't catch bugs even when they run
- **Flaky tests** waste CI time and developer trust
- **Brittle tests** break on refactoring even when behavior is correct
- **Incomplete tests** miss edge cases that cause production bugs

## Five Quality Dimensions

### 1. Mocking & Test Doubles (Weight: 30%)
Focus: Are we testing real code or just mocks?

### 2. Assertion Quality (Weight: 25%)
Focus: Do assertions actually catch bugs?

### 3. Test Structure & Clarity (Weight: 20%)
Focus: Are tests maintainable and understandable?

### 4. Coverage Quality (Weight: 15%)
Focus: Do we test edge cases and error paths?

### 5. Test Independence & Stability (Weight: 10%)
Focus: Are tests reliable and isolated?

## Red Flags to Detect

### 1. Over-Mocking (Critical)

**Pattern**: Every dependency is mocked, nothing real executes.

```python
# BAD: This tests nothing real
def test_process_order(mocker):
    mock_db = mocker.patch("app.db.get_order")
    mock_payment = mocker.patch("app.payment.charge")
    mock_email = mocker.patch("app.email.send")
    mock_inventory = mocker.patch("app.inventory.reserve")

    mock_db.return_value = Order(id=1, total=100)
    mock_payment.return_value = True

    result = process_order(1)  # What is this even testing?

    mock_payment.assert_called_once()  # Only verifies mock was called
```

**Fix**: Use real implementations or testcontainers for integration tests.

### 2. Mocking the System Under Test (Critical)

**Pattern**: Mocking the very function/class being tested.

```python
# BAD: You're testing the mock, not the code
def test_calculator_add(mocker):
    mocker.patch.object(Calculator, 'add', return_value=5)
    calc = Calculator()
    assert calc.add(2, 3) == 5  # This always passes!
```

**Fix**: Never mock the thing you're testing.

### 3. Assertion-Free Tests (Critical)

**Pattern**: Tests that run code but don't assert outcomes.

```python
# BAD: No assertions
def test_user_creation():
    user = User(name="John", email="john@example.com")
    user.save()
    # Test ends without checking anything

# BAD: Only asserts mock calls, not results
def test_send_email(mocker):
    mock_smtp = mocker.patch("smtplib.SMTP")
    send_welcome_email("user@test.com")
    mock_smtp.assert_called()  # So what? Did the email format correctly?
```

**Fix**: Assert on actual outcomes and state changes.

### 4. Integration Tests That Mock External Calls (High)

**Pattern**: Tests labeled "integration" but mock all I/O.

```python
# BAD: This is not an integration test
class TestUserServiceIntegration:
    def test_create_user(self, mocker):
        mocker.patch("app.db.session")  # Mocked!
        mocker.patch("app.cache.redis")  # Mocked!
        mocker.patch("app.queue.publish")  # Mocked!

        service = UserService()
        service.create_user(...)  # Nothing real happens
```

**Fix**: Use testcontainers or real test databases for integration tests.

### 5. Tests That Verify Implementation, Not Behavior (Medium)

**Pattern**: Testing exact method calls instead of outcomes.

```python
# BAD: Brittle, breaks on any refactor
def test_checkout(mocker):
    mock_cart = mocker.patch("app.cart.Cart")
    checkout()
    mock_cart.calculate_total.assert_called_once()
    mock_cart.apply_discount.assert_called_with(0.1)
    mock_cart.finalize.assert_called_once()
```

**Fix**: Test the result of checkout, not internal method calls.

### 6. Placeholder Tests (Critical)

**Pattern**: Tests with `pass`, `...`, or `TODO`.

```python
# BAD: Not a real test
def test_payment_processing():
    pass

def test_refund():
    ...  # TODO: implement

def test_subscription():
    assert True  # Always passes
```

**Fix**: Implement real tests or delete placeholders.

### 7. Tests That Can't Fail (Critical)

**Pattern**: Assertions that are always true.

```python
# BAD: Can never fail
def test_user():
    user = User()
    assert user is not None  # Constructors don't return None
    assert isinstance(user, User)  # Obviously true

# BAD: Catching and ignoring exceptions
def test_risky_operation():
    try:
        risky_operation()
    except:
        pass  # Test passes even on failure!
    assert True
```

**Fix**: Test actual behavior that could fail.

### 8. Excessive Setup, Minimal Verification (Medium)

**Pattern**: 50 lines of setup, 1 trivial assertion.

```python
# BAD: All that setup for this?
def test_report_generation():
    # 40 lines of mock setup...
    mock_this, mock_that, mock_everything...

    report = generate_report()
    assert report is not None  # That's it?
```

**Fix**: If you need that much setup, test smaller units or use fixtures.

## Test Quality Checklist

For each test file, verify:

### Must Have
- [ ] Tests assert on **outcomes**, not just mock calls
- [ ] The system under test (SUT) is **never mocked**
- [ ] No placeholder tests (`pass`, `...`, `assert True`)
- [ ] Tests can actually **fail** when code is broken

### Should Have
- [ ] Integration tests use **real dependencies** (testcontainers, test DB)
- [ ] Assertions verify **business logic**, not implementation details
- [ ] Error paths are tested with **real error conditions**
- [ ] Tests are **independent** (no order dependencies)

### Watch For
- [ ] Mock count > 3 in a single test (probably over-mocking)
- [ ] `assert_called` without corresponding result assertion
- [ ] Tests that only run in "happy path"
- [ ] Commented-out assertions

## Scoring

When critiquing tests, assign a quality score:

| Score | Meaning | Action |
|-------|---------|--------|
| A | Tests verify real behavior | Ship it |
| B | Minor mock overuse, but core logic tested | Acceptable |
| C | Significant mocking, some real verification | Needs improvement |
| D | Mostly mocks, minimal real testing | Rewrite required |
| F | Hollow tests, false confidence | Delete and start over |

## Output Format

When critiquing tests, provide:

```json
{
  "test_quality_score": "A" | "B" | "C" | "D" | "F",
  "tests_analyzed": 15,
  "issues": [
    {
      "severity": "critical" | "high" | "medium",
      "file": "tests/test_orders.py",
      "line": 42,
      "pattern": "over_mocking",
      "description": "All 5 dependencies mocked, no real code executes",
      "suggestion": "Use testcontainers for DB, test with real OrderService"
    }
  ],
  "summary": "8 of 15 tests are hollow (over-mocked). Tests provide false confidence.",
  "recommendations": [
    "Replace mock DB with testcontainers postgres",
    "Remove mock from OrderService - it's the SUT",
    "Add assertions on actual order state, not just mock calls"
  ]
}
```

## Integration with QA Agent

The QA agent should:

1. **Before running tests**: Analyze test quality
2. **If score is D or F**: Fail QA with fix_info about test quality
3. **Include in fix_info**: Specific tests to fix and how

Example fix_info for test quality issues:

```
Tests provide FALSE CONFIDENCE and must be fixed before DoD can be achieved:

1. **Over-mocking in test_order_service.py** (Critical)
   - Lines 15-45: test_create_order mocks OrderRepository, PaymentGateway,
     EmailService, InventoryService - nothing real executes
   - Fix: Use testcontainers for DB, real OrderService, mock only external APIs

2. **Placeholder test in test_payments.py:78** (Critical)
   - test_refund_processing contains only `pass`
   - Fix: Implement actual refund test or remove from test suite

3. **SUT mocked in test_calculator.py:12** (Critical)
   - Calculator.add is mocked in test_addition
   - Fix: Never mock the class you're testing

Test quality score: F (hollow tests)
These tests would pass even if the application is completely broken.
```

## Language-Specific Patterns

### Python (pytest)
- Watch for: `mocker.patch` overuse, `MagicMock` everywhere
- Good: `pytest-docker`, `testcontainers-python`, factory_boy with real DB

### TypeScript/JavaScript (Jest/Vitest)
- Watch for: `jest.mock()` at module level, `mockImplementation` everywhere
- Good: MSW for API mocking (intercepts real HTTP), testcontainers

### General
- Mock **boundaries** (external APIs, third-party services)
- Don't mock **your own code** unless it's truly a unit test
- Integration tests should integrate things
