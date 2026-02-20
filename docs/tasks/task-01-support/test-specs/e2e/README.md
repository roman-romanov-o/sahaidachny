# End-to-End Tests

E2E test specifications using real CLIs in authenticated Docker containers.

## Contents

| Spec | Test Cases | Time | Stories |
|------|------------|------|---------|
| [01-runner-smoke-tests.md](01-runner-smoke-tests.md) | 6 | ~2 min | US-004 |
| [02-full-loop-execution.md](02-full-loop-execution.md) | 10 | 55-95 min | US-005 |

## Overview

E2E tests validate complete workflows with real LLM APIs:
- **Smoke tests:** Fast validation that CLIs work (~30s per runner)
- **Full loop tests:** Complete execution workflow (5-15 min per runner)

## Prerequisites

- Docker daemon running
- API keys configured (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`)
- Authenticated container infrastructure (US-003)

## Running E2E Tests

```bash
# All E2E tests (expensive, ~60-100 min)
pytest tests/integration/ -m e2e -v --slow

# Smoke tests only (~2 min)
pytest tests/integration/ -m "e2e and not full_loop" -v

# Specific runner
pytest tests/integration/ -m "e2e and claude" -v
```

## Test Markers

- `@pytest.mark.slow` - All E2E tests (use real APIs)
- `@pytest.mark.e2e` - E2E test category
- `@pytest.mark.claude` / `@pytest.mark.codex` / `@pytest.mark.gemini` - Platform-specific

## Cost & Time

Per full E2E suite (all runners):
- **Time:** 60-100 minutes
- **Cost:** ~$0.30-0.65
- **API calls:** ~50-100 LLM requests

## Related

- [../README.md](../README.md) - Main test specs overview
- [../../user-stories/US-004-smoke-tests-all-runners.md](../../user-stories/US-004-smoke-tests-all-runners.md)
- [../../user-stories/US-005-full-loop-e2e-tests.md](../../user-stories/US-005-full-loop-e2e-tests.md)
