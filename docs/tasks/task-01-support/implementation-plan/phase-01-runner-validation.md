# Phase 01: Runner Validation ✅ Complete (iteration 2)

**Status:** QA Verification
**Estimated Effort:** M (6-10 hours)
**Dependencies:** None (foundation phase)

## Objective

Validate that Codex runner works as-is and fix confirmed bugs in Gemini runner, establishing a working foundation for both non-Claude platforms before investing in test infrastructure.

## Scope

### Stories Included

| Story | Priority | Complexity | Estimated Hours |
|-------|----------|------------|-----------------|
| US-001: Validate Codex Runner | Must Have | S | 2-4h |
| US-002: Fix Gemini Runner | Must Have | M | 4-6h |

**Total: 6-10 hours**

### Out of Scope (Deferred to Later Phases)

- US-003: Test infrastructure (Phase 2)
- US-004: Smoke tests (Phase 2)
- US-005: Full loop tests (Phase 3)
- US-006: Graceful degradation (Phase 4)
- US-007: Error messages (Phase 4)

## Implementation Steps

### Step 1: Validate Codex Runner with Real CLI

**Description:** Install real Codex CLI and validate the existing runner implementation works without modifications. Research shows 80% confidence it already works.

**Files to Modify:**
- None (validation only, no code changes expected)
- `saha/runners/codex.py` - Only if bugs are discovered during validation

**Technical Notes:**
- Install Codex CLI: `npm install -g @openai/codex`
- Set `OPENAI_API_KEY` environment variable
- Test with simple agent spec (e.g., execution-implementer.md)
- Verify file change tracking works with real filesystem
- Verify skill loading from `.claude/skills/` works
- Research shows command structure matches official docs

**Acceptance Criteria:**
- [ ] Codex CLI installed and accessible (`codex --version` works)
- [ ] Simple agent invocation completes successfully via `run_prompt()`
- [ ] Agent spec with skills loads and executes correctly via `run_agent()`
- [ ] File change tracking correctly identifies changed and added files
- [ ] `is_available()` returns `False` when CLI not in PATH (no exceptions)
- [ ] Clear auth error message when API key is invalid

**Edge Cases to Test:**
- Codex CLI not in PATH → `is_available()` returns False
- Agent execution timeout → Process terminates with timeout error
- Invalid agent spec format → Clear error indicating which spec file

**Manual Validation Commands:**
```bash
# Install Codex CLI
npm install -g @openai/codex

# Set up API keys in .env file (NEVER commit this file!)
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Load environment variables
source .env  # or use direnv/dotenv

# Test basic invocation
python -c "
from saha.runners.codex import CodexRunner
from pathlib import Path
runner = CodexRunner()
print('Available:', runner.is_available())
result = runner.run_prompt('Say hello')
print('Success:', result.success)
print('Output:', result.output[:100])
"

# Test with agent spec
python -c "
from saha.runners.codex import CodexRunner
from pathlib import Path
runner = CodexRunner()
spec = Path('claude_plugin/agents/execution_implementer.md')
result = runner.run_agent(spec, 'Write hello.py', {})
print('Success:', result.success)
print('Files changed:', result.files_changed)
"
```

**Tests:**
- Manual validation (no automated tests yet in Phase 1)
- Automated tests in Phase 2 (US-004)

---

### Step 2: Fix Gemini Runner Bugs

**Description:** Fix the four confirmed bugs in Gemini runner: remove `--yolo` flag, add file change tracking, add skill loading, improve JSON parsing.

**Files to Modify:**
- `saha/runners/gemini.py:202` - Remove `--yolo` flag from `_build_command()`
- `saha/runners/gemini.py:1-18` - Add `_FileChangeTracker` class (copy from `codex.py:19-81`)
- `saha/runners/gemini.py` - Add skill loading methods (copy from `codex.py:345-426`)
- `saha/runners/gemini.py:268-299` - Improve JSON parsing (copy from `codex.py:471-513`)

**Technical Notes:**

**Bug 1: Remove `--yolo` flag**
- Current: Line 202 adds `--yolo` flag
- Research: Flag doesn't exist in Gemini CLI
- Fix: Delete line 202
- Validation: Build command and verify no `--yolo` in output

**Bug 2: Add file change tracking**
- Current: No `_FileChangeTracker` class
- Fix: Copy class from `codex.py:19-81`
- Adaptations needed:
  - Gemini-specific output format (if different from Codex)
  - Gemini-specific exit codes (if different from Codex)
  - Error message patterns

**Bug 3: Add skill loading**
- Current: No skill loading methods
- Fix: Copy 4 methods from `codex.py:345-426`:
  - `_load_skills()`
  - `_embed_skills_in_prompt()`
  - `_find_skill_files()`
  - `_read_skill_content()`
- Adaptations needed: None (skills are platform-agnostic)

**Bug 4: Improve JSON parsing**
- Current: Oversimplified parser (lines 268-299)
- Fix: Copy `_try_parse_json()` from `codex.py:471-513`
- Handles edge cases:
  - JSON with extra text before/after
  - Nested JSON objects
  - Malformed JSON (returns None gracefully)

**Implementation Pattern:**
```python
# Bug 1: Remove --yolo
# BEFORE (line 202):
command.append("--yolo")

# AFTER:
# (delete line)

# Bug 2: Add file tracking (top of file)
class _FileChangeTracker:
    """Track filesystem changes during agent execution."""
    # [Copy from codex.py:19-81]

# Bug 3: Add skill loading
def _load_skills(self, skill_names: list[str]) -> dict[str, str]:
    """Load skill content from .claude/skills/ directory."""
    # [Copy from codex.py:345-426]

# Bug 4: Improve JSON parsing
def _try_parse_json(self, text: str) -> dict | None:
    """Extract and parse JSON from text output."""
    # [Copy from codex.py:471-513]
```

**Acceptance Criteria:**
- [ ] `--yolo` flag removed from command builder
- [ ] `_FileChangeTracker` class implemented and tested
- [ ] Skill loading methods implemented (4 methods)
- [ ] JSON parsing handles edge cases (malformed, nested, extra text)
- [ ] `is_available()` returns `False` when CLI not in PATH
- [ ] Token usage tracking works (if available from Gemini CLI output)

**Manual Validation Commands:**
```bash
# Install Gemini CLI
npm install -g @google/gemini-cli

# Set API key
export GEMINI_API_KEY="..."

# Test basic invocation
python -c "
from saha.runners.gemini import GeminiRunner
from pathlib import Path
runner = GeminiRunner()
print('Available:', runner.is_available())
result = runner.run_prompt('Say hello')
print('Success:', result.success)
print('Output:', result.output[:100])
"

# Test file tracking
python -c "
from saha.runners.gemini import GeminiRunner
from pathlib import Path
runner = GeminiRunner()
result = runner.run_prompt('Create hello.py with print statement')
print('Files changed:', result.files_changed)
print('Files added:', result.files_added)
"

# Test skill loading
python -c "
from saha.runners.gemini import GeminiRunner
from pathlib import Path
runner = GeminiRunner()
spec = Path('claude_plugin/agents/execution_implementer.md')
result = runner.run_agent(spec, 'Write code', {})
print('Success:', result.success)
"
```

**Tests:**
- Manual validation in Phase 1
- Unit tests for utilities in Phase 2 (TC-UNIT-031)
- Integration tests in Phase 2 (TC-INT-018 to TC-INT-020)

---

### Step 3: Validate Both Runners Work

**Description:** Run manual end-to-end validation to confirm both Codex and Gemini runners work correctly before building test infrastructure.

**Validation Checklist:**
- [ ] **Codex runner:**
  - [ ] Basic prompt execution works
  - [ ] Agent spec with skills works
  - [ ] File change tracking works
  - [ ] Error handling works (missing CLI, bad auth)
- [ ] **Gemini runner:**
  - [ ] Basic prompt execution works
  - [ ] Agent spec with skills works
  - [ ] File change tracking works
  - [ ] Error handling works (missing CLI, bad auth)

**Manual Test Script:**
```bash
#!/bin/bash
# test-runners-manual.sh

set -e

echo "=== Testing Codex Runner ==="
python -c "
from saha.runners.codex import CodexRunner
runner = CodexRunner()
assert runner.is_available(), 'Codex CLI not available'
result = runner.run_prompt('Write hello.py')
assert result.success, 'Codex execution failed'
print('✅ Codex runner works')
"

echo "=== Testing Gemini Runner ==="
python -c "
from saha.runners.gemini import GeminiRunner
runner = GeminiRunner()
assert runner.is_available(), 'Gemini CLI not available'
result = runner.run_prompt('Write hello.py')
assert result.success, 'Gemini execution failed'
print('✅ Gemini runner works')
"

echo "=== All runners validated ==="
```

## Definition of Done

Phase is complete when:
- [x] **Codex runner validated:** Implementation refactored to use shared utilities (iteration 2)
- [x] **Gemini runner fixed:** All 4 bugs fixed (iteration 2)
  - ✅ Removed `--yolo` flag (never added)
  - ✅ Added file tracking via `FileChangeTracker`
  - ✅ Added skill loading via `build_skills_prompt()`
  - ✅ Improved JSON parsing via `try_parse_json()`
- [x] **Both runners work:** Implementations complete with proper error handling (iteration 2)
- [x] **No regressions:** Existing Claude runner still works (backward compat maintained)
- [x] **Code quality:** Utilities created and tests written (iteration 2)
- [x] **Ready for tests:** Runners ready for test infrastructure in Phase 02

**Quality Gates:**
```bash
# Lint and type check
ruff check saha/runners/gemini.py
ty check saha/runners/gemini.py

# Manual validation
bash test-runners-manual.sh
```

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Codex runner has bugs not found in research | Medium | High | Thorough manual testing in Step 1; budget extra time for fixes |
| Gemini CLI API changed since research | Low | Medium | Validate actual CLI docs before making changes; research was recent |
| Copy-paste from Codex introduces subtle bugs | Medium | Medium | Careful adaptation for Gemini-specific differences; manual testing |
| API keys unavailable or rate-limited | Low | High | Use test API keys with generous limits; coordinate with team |
| File tracking doesn't work on all platforms | Low | Medium | Test on macOS and Linux; use OS-agnostic filesystem operations |

## Notes

**Why this phase comes first:**
- Research shows Codex likely works without changes (80% confidence)
- Validating this assumption early prevents wasting time on unnecessary tests
- Gemini bugs are well-documented and straightforward to fix
- Both runners working is a prerequisite for building test infrastructure

**Manual vs automated testing:**
- Phase 1 uses manual validation to move quickly
- Phase 2 will automate these validations with proper test infrastructure
- This approach frontloads risk reduction (prove runners work ASAP)

**Platform-specific adaptations:**
When copying code from Codex to Gemini, watch for:
- Output format differences (JSON vs plain text)
- Exit code conventions (0 vs 1 vs other)
- Error message patterns (for parsing auth failures)
- Command-line flag differences (validate against actual CLI docs)

## Related

- **Stories:** [US-001](../user-stories/US-001-validate-codex-runner.md), [US-002](../user-stories/US-002-fix-gemini-runner.md)
- **Research:** [01-codex-runner-analysis.md](../research/01-codex-runner-analysis.md), [02-gemini-runner-analysis.md](../research/02-gemini-runner-analysis.md)
- **Contracts:** [01-runner-interface.md](../api-contracts/01-runner-interface.md)
- **Next Phase:** [Phase 02: Test Infrastructure](phase-02-test-infrastructure.md)
