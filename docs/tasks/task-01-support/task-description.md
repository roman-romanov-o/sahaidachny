# Task Description: Multi-Platform Support for Agentic Coding

**Task ID:** TASK-01
**Status:** Ready for Stories
**Last Updated:** 2026-02-12

## Problem Statement

Sahaidachny currently has runner implementations for Codex and Gemini CLI (in `saha/runners/codex.py` and `saha/runners/gemini.py`), but **they don't work**. Only the Claude Code runner (`saha/runners/claude.py`) functions correctly, limiting users to a single platform and preventing them from leveraging the strengths of different AI platforms.

### Current State

- **Claude Code runner** (`claude.py`, 775 lines): Fully functional with native agent support, tool execution tracking, and robust error handling
- **Codex runner** (`codex.py`, 550 lines): Implementation exists with file change tracking but is non-functional
- **Gemini runner** (`gemini.py`, 299 lines): Complete implementation with all methods but untested and broken
- **RunnerRegistry**: Infrastructure exists (`saha/runners/registry.py`) supporting CLAUDE, CODEX, GEMINI, MOCK
- Users cannot reliably use Codex or Gemini CLI for either planning or execution phases
- No end-to-end tests validating multi-platform functionality
- Documentation assumes Claude Code as the only working option

### Desired State

All three platforms (Claude Code, Codex CLI, Gemini CLI) work seamlessly across both planning and execution phases, with:
- Full feature parity: all Sahaidachny features work identically across platforms
- Common abstraction layer for agent invocation, tool execution, context management, and configuration
- Comprehensive end-to-end tests validating each platform
- Complete setup guides and examples for all platforms

## Success Criteria

Measurable outcomes that define "done":

1. [ ] **End-to-end tests pass** - Automated tests successfully run specific workflows on all three platforms:
   - Planning workflow: `init → research → task → stories` produces valid artifacts (user-stories/, task-description.md)
   - Execution workflow: `implementer → qa → code-quality → manager → dod` completes one full iteration
   - State resumption: execution can be stopped and resumed, maintaining progress across all platforms
2. [ ] **Manual validation succeeds** - Run task-01-support planning phase on all 3 platforms and verify:
   - All platforms produce: (a) user-stories/ folder with ≥3 stories, (b) implementation-plan/ with ≥2 phases, (c) test-specs/ folder
   - Artifacts are equivalent in structure (same markdown sections) and completeness (no missing required fields)
3. [ ] **Documentation complete** - Setup guides, configuration examples, and troubleshooting docs exist for Codex and Gemini CLI users
4. [ ] **Feature parity achieved** - All platforms reach equivalent outcomes:
   - Planning commands produce equivalent artifacts (same sections, completeness)
   - Execution agents reach equivalent outcomes (tests pass, code quality passes)
   - Platform differences (native agent support vs. embedded specs) are acceptable if end results match
5. [ ] **No regressions** - Existing Claude Code workflows continue working without any changes to user code or configs
6. [ ] **CI validation** - GitHub Actions run integration tests against mocked CLIs (validates code paths and error handling; actual CLI integration validated manually)

## Scope

### In Scope

- **Fix Codex runner** (`saha/runners/codex.py`):
  - Debug and fix file change tracking
  - Validate agent spec loading and skill injection
  - Ensure proper non-interactive execution
  - Test snapshot-based file change detection
  - Implement error handling for missing Codex CLI

- **Fix Gemini runner** (`saha/runners/gemini.py`):
  - Validate CLI command building (`--yolo`, `--sandbox` flags)
  - Test system prompt extraction from agent specs
  - Fix JSON parsing from Gemini output
  - Validate model selection and timeout handling
  - Implement error handling for missing Gemini CLI

- **Platform limitation handling**:
  - Graceful degradation when a platform doesn't support a feature
  - Clear error messages when CLI is unavailable or not installed
  - Document platform-specific limitations in user guide
  - Provide manual override options for tool selection (e.g., fallback to Claude if Codex fails)

- **Unified abstraction layer**:
  - Common interface for agent invocation (already exists in `saha/runners/base.py`)
  - Consistent tool/command execution across platforms
  - Shared context management patterns
  - Unified configuration schema for platform-specific settings

- **Planning phase support**:
  - Enable Codex CLI to run planning commands (`/saha:init`, `/saha:research`, `/saha:stories`, etc.)
  - Enable Gemini CLI to run planning commands
  - Ensure Claude Code plugin commands work with alternative runners

- **Execution phase support**:
  - Validate execution agents work on all platforms (implementer, QA, code-quality, manager, DoD)
  - Test iterative loop with fix_info across platforms
  - Validate state persistence and resumption

- **Testing**:
  - End-to-end integration tests for each platform
  - Test fixtures for all three CLIs (may use mocks or testcontainers)
  - Validation scripts in CI/CD pipeline

- **Documentation**:
  - Setup guides for Codex CLI and Gemini CLI
  - Configuration examples (`SAHA_RUNNER=codex`, `SAHA_CODEX_MODEL=o3`, etc.)
  - Migration guide for users switching between platforms
  - Troubleshooting common issues

### Out of Scope

- **UI/web interface** - CLI-only; no web dashboard or GUI
- **Supporting additional platforms** - Only targeting Claude Code, Codex CLI, Gemini CLI (no Cursor, Windsurf, Aider, etc.)
- **Performance optimization** - Focus on functionality first; performance tuning comes in future iterations
- **Migration tooling** - No automated scripts to migrate existing single-platform configs
- **Cost optimization features** - No automatic model selection or cost-based routing between platforms

## Constraints

| Type | Constraint | Reason |
|------|------------|--------|
| Technical | None - full freedom to refactor | User explicitly approved no constraints |
| Time | None specified | - |
| Resource | Must maintain backward compatibility | Existing Claude Code workflows must continue working without changes |

## Dependencies

### Prerequisites

- [x] Claude Code CLI installed and functioning (already working)
- [ ] Codex CLI installed and accessible in PATH
- [ ] Gemini CLI installed and accessible in PATH
- [ ] Access to test accounts/API keys for Codex and Gemini
- [x] Runner registry infrastructure exists (`saha/runners/registry.py`)
- [x] Base runner interface defined (`saha/runners/base.py`)

### Blockers

- None currently identified

## Technical Context

Sahaidachny uses a **runner pattern** to abstract LLM backend execution. All runners implement the `Runner` interface:

```python
# saha/runners/base.py
class Runner(ABC):
    def run_agent(agent_spec_path, prompt, context, timeout) -> RunnerResult
    def run_prompt(prompt, system_prompt, timeout) -> RunnerResult
    def is_available() -> bool
    def get_name() -> str
```

### Affected Components

- `saha/runners/codex.py` - Fix file change tracking, agent invocation, skill loading
- `saha/runners/gemini.py` - Fix CLI command building, output parsing, system prompt handling
- `saha/runners/registry.py` - May need updates for platform-specific configs
- `saha/orchestrator/loop.py:101-534` - AgenticLoop uses runners for all agent invocations
- `saha/orchestrator/factory.py` - Creates runner registry, may need updates
- `saha/config/settings.py:97-164` - Configuration for runner selection (`SAHA_RUNNER`, `SAHA_CODEX_MODEL`, etc.)
- `claude_plugin/commands/*.md` - Planning commands may need adjustments for Codex/Gemini
- `claude_plugin/agents/execution_*.md` - Execution agents may need platform-specific instructions

### Integration Points

- **Claude Code CLI** (`claude` command) - Native agent support with `--agent` flag
- **Codex CLI** (`codex exec` command) - Non-interactive execution with `--output-last-message`
- **Gemini CLI** (`gemini` command) - Auto-accept tool calls with `--yolo` flag
- **Runner Registry** - Factory pattern for creating platform-specific runners
- **Orchestrator** - Invokes runners for each agent in the execution loop
- **State Management** - Persists execution state (must work identically across platforms)
- **Tools** (ruff, ty, complexity, pytest) - Invoked by QA and code-quality agents

### Key Differences Between Platforms

| Feature | Claude Code | Codex CLI | Gemini CLI |
|---------|-------------|-----------|------------|
| Agent support | Native (`--agent`) | Embed spec in prompt | Embed spec in prompt |
| Tool tracking | Built-in metadata | Filesystem snapshots | Filesystem snapshots |
| Interactive mode | Supported | Use `codex exec` non-interactive | Use `--yolo` for auto-accept |
| Model selection | `--model` flag | `--model` flag | `--model` flag |
| Sandboxing | Permission modes | Sandbox flags | `--sandbox` flag |
| Output format | Text with JSON extraction | `--output-last-message` | Text with JSON extraction |
| Skill loading | Native | Manual injection | Manual injection |

## Planning Artifacts

<!-- Check off artifacts as they are created -->

### Required

- [ ] **User Stories** - `user-stories/` folder
- [ ] **Implementation Plan** - `implementation-plan/` folder with phases
- [ ] **Test Specifications** - `test-specs/` folder

### Optional

- [ ] **API Contracts** - `api-contracts/` folder (for runner interface contracts)
- [ ] **Design Decisions** - `design-decisions/` folder (for abstraction layer choices)
- [ ] **Research Report** - `research/` folder (for investigating actual Codex/Gemini CLI APIs)

## Open Questions

- [x] **Codex CLI validation**: What are the actual Codex CLI commands and flags? Does `codex exec --output-last-message` work as expected? → **Resolved in research phase**
- [x] **Gemini CLI validation**: Are the Gemini CLI flags (`--yolo`, `--sandbox`) correct? Has the API changed since implementation? → **Resolved in research phase**
- [ ] **Agent spec compatibility**: Do agent markdown specs need platform-specific adaptations? Do tool names/signatures differ?
- [ ] **Planning command support**: How do planning commands work with Codex/Gemini? Do they need special handling?
- [ ] **Skill injection**: How should skills from `.claude/skills/` be loaded and injected for non-Claude runners?
- [ ] **Token usage tracking**: Should we track token usage for Codex/Gemini? Is usage data available from their CLIs?
- [ ] **CI mock strategy**: Should CI use real CLIs with test credentials or mocked CLIs? What are the trade-offs?

## References

- `README.md:1-276` - Project overview and installation guide
- `docs/architecture.md:434-525` - Runner architecture documentation
- `saha/runners/base.py` - Runner interface definition
- `saha/runners/registry.py:1-100` - Runner registry implementation
- `saha/runners/claude.py:12-206` - Working Claude runner reference
- `saha/runners/codex.py:1-550` - Broken Codex runner to fix
- `saha/runners/gemini.py:1-300` - Broken Gemini runner to fix
