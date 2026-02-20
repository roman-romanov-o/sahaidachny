# Integration Tests

Integration test specifications for runner components.

## Contents

| Spec | Test Cases | Time | Stories |
|------|------------|------|---------|
| [01-authenticated-containers.md](01-authenticated-containers.md) | 8 | 5-10 min | US-003 |
| [02-runner-compliance.md](02-runner-compliance.md) | 11 | 15-30 min | US-001, US-002 |

## Overview

Integration tests validate:
- **Authenticated containers:** Docker fixtures with API key injection
- **Runner compliance:** Runner ABC interface implementation
- **Real CLI integration:** Actual CLI invocation and output parsing

## Prerequisites

- Docker daemon running
- At least one API key configured
- Real CLIs installed (or skipped if unavailable)

## Running Integration Tests

```bash
# All integration tests
pytest tests/integration/ -v

# Authenticated containers only
pytest tests/integration/ -k "authenticated" -v

# Runner compliance only
pytest tests/integration/ -k "compliance" -v

# Specific runner
pytest tests/integration/ -m codex -v
```

## Test Organization

- `tests/integration/runners/conftest.py` - Shared fixtures
- `tests/integration/runners/test_authenticated_containers.py`
- `tests/integration/runners/test_runner_compliance.py`

## Related

- [../README.md](../README.md) - Main test specs overview
- [../../user-stories/US-001-validate-codex-runner.md](../../user-stories/US-001-validate-codex-runner.md)
- [../../user-stories/US-002-fix-gemini-runner.md](../../user-stories/US-002-fix-gemini-runner.md)
- [../../user-stories/US-003-authenticated-container-infrastructure.md](../../user-stories/US-003-authenticated-container-infrastructure.md)
