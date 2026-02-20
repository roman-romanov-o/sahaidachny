# Test Specifications

Test specs organized by type for multi-platform runner support.

## Coverage Summary

| Type | Specs | Test Cases | Stories Covered | Est. Time |
|------|-------|------------|-----------------|-----------|
| E2E | 2 | 16 | US-004, US-005 | 60-100 min |
| Integration | 2 | 18 | US-001, US-002, US-003, US-006 | 20-40 min |
| Unit | 1 | 23 | US-001, US-002 | <5 min |
| **Total** | **5** | **57** | **6/7 stories** | **85-145 min** |

## Test Hierarchy

```
E2E Tests (Real CLIs, Authenticated Containers)
├── Smoke Tests (~2 min per runner)
│   └── Validate basic CLI invocation works
└── Full Loop Tests (5-15 min per runner)
    └── Validate complete execution workflow

Integration Tests (Real CLIs, Isolated Components)
├── Authenticated Containers (~1-2 min setup)
│   └── Docker fixtures with API keys
└── Runner Compliance (2-5 min per runner)
    └── Validate Runner ABC implementation

Unit Tests (Mocked, Fast)
└── Runner Utilities (<1 sec per test)
    └── File tracking, skill loading, JSON parsing
```

## Contents

### E2E Tests

| Spec | Test Cases | Priority | Time Estimate |
|------|------------|----------|---------------|
| [01-runner-smoke-tests.md](e2e/01-runner-smoke-tests.md) | TC-E2E-001 to TC-E2E-006 | Critical | ~2 min total |
| [02-full-loop-execution.md](e2e/02-full-loop-execution.md) | TC-E2E-010 to TC-E2E-016 | Critical | 55-95 min total |

### Integration Tests

| Spec | Test Cases | Priority | Time Estimate |
|------|------------|----------|---------------|
| [01-authenticated-containers.md](integration/01-authenticated-containers.md) | TC-INT-001 to TC-INT-008 | Critical | 5-10 min |
| [02-runner-compliance.md](integration/02-runner-compliance.md) | TC-INT-010 to TC-INT-020 | Critical | 15-30 min |

### Unit Tests

| Spec | Test Cases | Priority | Time Estimate |
|------|------------|----------|---------------|
| [01-runner-utilities.md](unit/01-runner-utilities.md) | TC-UNIT-001 to TC-UNIT-042 | High | <5 min |

## Test Coverage Matrix

| Story | E2E | Integration | Unit | Coverage |
|-------|-----|-------------|------|----------|
| US-001: Validate Codex | TC-E2E-002, TC-E2E-011 | TC-INT-013 to TC-INT-017 | TC-UNIT-001 to TC-UNIT-042 | ✅ Full |
| US-002: Fix Gemini | TC-E2E-003, TC-E2E-012 | TC-INT-018 to TC-INT-020 | TC-UNIT-031 | ✅ Full |
| US-003: Auth Containers | - | TC-INT-001 to TC-INT-008 | - | ✅ Full |
| US-004: Smoke Tests | TC-E2E-001 to TC-E2E-006 | - | - | ✅ Full |
| US-005: Full Loop E2E | TC-E2E-010 to TC-E2E-016 | - | - | ✅ Full |
| US-006: Graceful Degradation | TC-E2E-005, TC-E2E-006 | TC-INT-006 to TC-INT-008 | - | ⚠️ Partial |
| US-007: Error Messages | - | - | - | ❌ None |

**Notes:**
- **US-006 (Graceful Degradation):** Partially covered by existing tests (skip behavior, error handling). Additional edge cases may be tested manually or in implementation phase.
- **US-007 (Error Messages):** Documentation-focused story. Error format compliance can be validated through existing integration tests (TC-INT-016, TC-INT-017) that verify error messages are actionable.

## Acceptance Criteria Coverage

### US-001: Validate Codex Runner (6/6 criteria)

- ✅ AC1: Smoke test with real CLI - TC-E2E-002
- ✅ AC2: Agent spec with skills - TC-INT-014
- ✅ AC3: File change tracking - TC-INT-015
- ✅ AC4: is_available() behavior - TC-INT-016
- ✅ AC5: Auth failure message - TC-INT-017
- ✅ AC6: Edge cases - TC-E2E-006, TC-INT-013

### US-002: Fix Gemini Runner (7/7 criteria)

- ✅ AC1: Validate --yolo research - TC-INT-018
- ✅ AC2: Remove --yolo flag - TC-UNIT-031
- ✅ AC3: Adapt Codex patterns - TC-INT-019, TC-INT-020
- ✅ AC4: File change tracking - TC-INT-019
- ✅ AC5: Skill loading - TC-INT-020
- ✅ AC6: is_available() behavior - TC-INT-011
- ✅ AC7: Token usage tracking - TC-E2E-004

### US-003: Authenticated Containers (5/5 criteria)

- ✅ AC1: API keys via env vars - TC-INT-001
- ✅ AC2: All CLIs installed - TC-INT-002
- ✅ AC3: Skip when key missing - TC-INT-003
- ✅ AC4: Keys cleared on stop - TC-INT-004
- ✅ AC5: Module-scoped reuse - TC-INT-005

### US-004: Smoke Tests (5/5 criteria)

- ✅ AC1: Claude smoke test - TC-E2E-001
- ✅ AC2: Codex smoke test - TC-E2E-002
- ✅ AC3: Gemini smoke test - TC-E2E-003
- ✅ AC4: RunnerResult validation - TC-E2E-004
- ✅ AC5: Skip when key missing - TC-E2E-005

### US-005: Full Loop E2E (5/5 criteria)

- ✅ AC1: Full loop happy path - TC-E2E-010, TC-E2E-011, TC-E2E-012
- ✅ AC2: 4-level verification - TC-E2E-010 (all levels)
- ✅ AC3: QA retry with fix_info - TC-E2E-013
- ✅ AC4: Code quality retry - TC-E2E-014
- ✅ AC5: State resume after SIGTERM - TC-E2E-015

## Running Tests

### All Tests
```bash
pytest tests/ -v
```

### By Type
```bash
pytest tests/integration/ -v --slow  # Integration + E2E
pytest tests/unit/ -v               # Unit only
```

### By Runner
```bash
pytest -m claude tests/  # Claude Code only
pytest -m codex tests/   # Codex only
pytest -m gemini tests/  # Gemini only
```

### Skip Slow Tests
```bash
pytest -m "not slow" tests/  # Skip E2E and integration
```

## Performance Targets

| Test Suite | Target Time | Max Time |
|------------|-------------|----------|
| Unit tests | <10s | 30s |
| Integration (per runner) | <10 min | 20 min |
| E2E smoke (all runners) | <2 min | 5 min |
| E2E full loop (per runner) | 5-10 min | 15 min |
| **Full suite (all runners)** | **85-145 min** | **180 min** |

## Cost Estimates

Per full test run (all runners, all E2E tests):
- Claude (Haiku): $0.15-0.30
- Codex (GPT-4o-mini): $0.10-0.20
- Gemini (Flash): $0.05-0.15
- **Total: ~$0.30-0.65**

## Related

- **Task:** [task-description.md](../task-description.md)
- **User Stories:** [user-stories/](../user-stories/)
- **API Contracts:** [api-contracts/](../api-contracts/)
- **Research:** [research/06-e2e-testing-strategy.md](../research/06-e2e-testing-strategy.md)
