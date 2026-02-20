# API Contracts

Interface definitions and API specifications for multi-platform runner support.

## Contents

| Name | Type | Status | Description |
|------|------|--------|-------------|
| [Runner Interface](01-runner-interface.md) | Python ABC | Existing | Base interface all runners must implement |
| [Agent Output Formats](02-agent-output-contracts.md) | JSON Schema | Existing | Structured output from execution agents |
| [CLI Integration Patterns](03-cli-integration-patterns.md) | External Process | Draft | CLI invocation patterns for each platform |

## Contract Map

### Internal Interfaces

**Runner Architecture:**
- [01-runner-interface.md](01-runner-interface.md) - `Runner` ABC and `RunnerResult` contract
  - Defines `run_agent()`, `run_prompt()`, `is_available()`, `get_name()`
  - Standardizes return type across all platforms
  - Error handling contract (recoverable vs non-recoverable)

**Agent Communication:**
- [02-agent-output-contracts.md](02-agent-output-contracts.md) - JSON schemas for execution agents
  - Implementation agent output (`files_changed`, `files_added`, `next_steps`)
  - QA agent output (`dod_achieved`, `checks`, `fix_info`)
  - Code quality agent output (`quality_passed`, `issues`)
  - Manager agent output (`updated`, `artifacts_modified`)
  - DoD agent output (`task_complete`, `remaining_items`)

### External Integration Patterns

**CLI Invocation:**
- [03-cli-integration-patterns.md](03-cli-integration-patterns.md) - Platform-specific CLI usage
  - Claude Code CLI patterns (native agent support)
  - Codex CLI patterns (stdin input, file output)
  - Gemini CLI patterns (prompt-based)
  - File change tracking strategies (native vs filesystem snapshots)
  - Skill loading patterns (native vs manual injection)
  - Environment variables and authentication
  - Error codes and handling

## Usage Guidelines

### For Implementation

When implementing runner support:
1. Ensure compliance with `Runner` interface (01)
2. Parse agent output according to schemas (02)
3. Follow platform-specific CLI patterns (03)
4. Handle all documented error cases
5. Track file changes using appropriate strategy

### For Testing

When writing E2E tests:
1. Verify `RunnerResult` fields match contract (01)
2. Validate agent JSON output schemas (02)
3. Test CLI invocation patterns work correctly (03)
4. Verify file change tracking accuracy
5. Test error handling and graceful degradation

## Compliance Validation

All runners must:
- ✅ Implement all `Runner` ABC methods
- ✅ Return `RunnerResult` with required fields
- ✅ Parse agent JSON output correctly
- ✅ Not raise exceptions in `is_available()`
- ✅ Track file changes (native or filesystem snapshots)

## Related

- **Task:** [task-description.md](../task-description.md)
- **Stories:** [US-001](../user-stories/US-001-validate-codex-runner.md) (Codex), [US-002](../user-stories/US-002-fix-gemini-runner.md) (Gemini)
- **Research:** [01-codex-runner-analysis.md](../research/01-codex-runner-analysis.md), [02-gemini-runner-analysis.md](../research/02-gemini-runner-analysis.md)
