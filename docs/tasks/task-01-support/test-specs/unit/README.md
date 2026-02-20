# Unit Tests

Unit test specifications for runner utility functions.

## Contents

| Spec | Test Cases | Time | Stories |
|------|------------|------|---------|
| [01-runner-utilities.md](01-runner-utilities.md) | 23 | <5 min | US-001, US-002 |

## Overview

Fast unit tests for isolated functions:
- File change tracking (`_FileChangeTracker`)
- Skill loading (`_load_skills`, `_embed_skills`)
- JSON parsing (`_try_parse_json`)
- Command building (`_build_command`)
- RunnerResult helpers

## Prerequisites

- No external dependencies (all mocked)
- Fast execution (<1s per test)

## Running Unit Tests

```bash
# All unit tests
pytest tests/unit/ -v

# Specific category
pytest tests/unit/ -k "file_tracking" -v
pytest tests/unit/ -k "skill_loading" -v
pytest tests/unit/ -k "json_parsing" -v

# Fast tests only
pytest tests/unit/ -m fast -v
```

## Test Organization

- `tests/unit/runners/test_file_tracking.py`
- `tests/unit/runners/test_skill_loading.py`
- `tests/unit/runners/test_json_parsing.py`
- `tests/unit/runners/test_command_building.py`
- `tests/unit/runners/test_runner_result.py`

## Mocking Strategy

- Mock `subprocess.run` for command execution
- Mock `Path` operations for filesystem
- Mock `os.environ` for environment variables
- Use `pytest.monkeypatch` for temporary changes

## Related

- [../README.md](../README.md) - Main test specs overview
- [../../api-contracts/01-runner-interface.md](../../api-contracts/01-runner-interface.md)
