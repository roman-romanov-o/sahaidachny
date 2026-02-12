# Research: Codex Runner Implementation Analysis

**Date:** 2026-02-12
**Status:** Complete

## Summary

The Codex runner implementation is **functionally complete but unvalidated**. The code follows the correct architecture patterns and implements all required methods, but lacks real-world testing against the actual Codex CLI. The claimed "brokenness" appears to be an assumption rather than a confirmed bug.

## Key Findings

### 1. **Architecture is Sound**
   - Evidence: `saha/runners/codex.py:83-551`
   - Implementation: Implements all required `Runner` interface methods (`run_agent`, `run_prompt`, `is_available`, `get_name`)
   - Pattern matches: Uses same subprocess execution patterns as working ClaudeRunner
   - Implication: No architectural refactoring needed

### 2. **Command Building Appears Correct**
   - Evidence: `saha/runners/codex.py:220-243`
   - Command structure:
     ```python
     cmd = [
         "codex", "exec", "-",  # Read from stdin
         "--output-last-message", str(output_file),
         "--color", "never",
         "--cd", str(working_dir),
         "--skip-git-repo-check",
         "--model", model,  # if specified
         "--sandbox", sandbox,  # or --dangerously-bypass-...
     ]
     ```
   - Cross-reference: According to official Codex CLI docs (https://developers.openai.com/codex/cli/reference/), these flags exist:
     - `codex exec` - non-interactive mode ✓
     - `--output-last-message, -o <path>` - writes final message to file ✓
     - `--cd, -C <path>` - set working directory ✓
     - `--skip-git-repo-check` - allow running outside git repos ✓
     - `--model, -m <string>` - override model ✓
     - `--sandbox, -s` - policy options (read-only | workspace-write | danger-full-access) ✓
     - `--dangerously-bypass-approvals-and-sandbox` - bypass safety ✓
   - Implication: **Command structure matches official API**

### 3. **Agent Spec Embedding is Implemented**
   - Evidence: `saha/runners/codex.py:98-113, 283-394`
   - Approach: Since Codex CLI lacks native `--agent` flag (unlike Claude), the runner:
     1. Reads agent spec markdown files
     2. Splits YAML frontmatter from body
     3. Extracts system prompt from body
     4. Parses `skills:` list from frontmatter
     5. Loads skill markdown files
     6. Embeds everything into prompt with separators
   - Implication: This is the **correct strategy** for non-native agent support

### 4. **File Change Tracking Uses Snapshot Approach**
   - Evidence: `saha/runners/codex.py:19-81`
   - Implementation: `_FileChangeTracker` class:
     - Takes filesystem snapshot before execution (mtime_ns + size)
     - Takes snapshot after execution
     - Diffs to detect changed/added files
     - Skips known directories (.git, .venv, node_modules, etc.)
   - Tests: `tests/integration/test_codex_runner.py:90-106` - test passes ✓
   - Comparison: Claude uses native `tool_use_result` metadata from JSON events
   - Implication: **Snapshot approach is valid workaround** for CLIs without native file tracking

### 5. **Token Usage Extraction is Comprehensive**
   - Evidence: `saha/runners/codex.py:442-550`
   - Strategies (in fallback order):
     1. Parse JSON from structured_output dict
     2. Parse JSON from raw stdout
     3. Parse JSON from last message output file
     4. **Fallback to session logs**: Reads latest `~/.codex/sessions/rollout-*.jsonl` file
   - Implication: Handles multiple output formats, resilient to API changes

### 6. **Skill Loading Matches Claude Plugin Structure**
   - Evidence: `saha/runners/codex.py:292-394`
   - Logic:
     - Parses `skills: ruff, ty` or YAML list format from frontmatter
     - Searches in `claude_plugin/skills/{skill_name}/SKILL.md`
     - Splits frontmatter, extracts body
     - Renders as `## Skill: {name}\n\n{body}`
   - Tests: `tests/integration/test_codex_runner.py:43-70` - **test passes** ✓
   - Cross-reference: Agent specs exist in `.claude/agents/execution-*.md` with skill references
   - Implication: **Skill injection works correctly** in tests

## Validated Assumptions

| Assumption | Status | Evidence |
|------------|--------|----------|
| Codex CLI exists and is installable | ✅ Confirmed | https://github.com/openai/codex, npm/brew install available |
| `codex exec` supports non-interactive mode | ✅ Confirmed | Official docs specify `codex exec` command |
| `--output-last-message` flag exists | ✅ Confirmed | Documented as `-o, --output-last-message <path>` |
| Sandbox flags are correct | ✅ Confirmed | `--sandbox <read-only\|workspace-write\|danger-full-access>` |
| Codex CLI lacks native agent support | ✅ Confirmed | No `--agent` flag in docs, requires embedding |
| Runner implementation is broken | ❌ **UNCONFIRMED** | No evidence of actual bugs, only "untested" |

## Risks Identified

### 1. **No Real-World Validation** (Severity: High)
   - Description: Code has never been tested against actual Codex CLI
   - Why this matters: Edge cases, output format changes, error handling may differ from assumptions
   - Mitigation: Run manual integration test with real Codex CLI installation

### 2. **Stdin Input Method Untested** (Severity: Medium)
   - Description: Uses `codex exec -` (read from stdin) via `process.communicate(prompt)`
   - Evidence: `saha/runners/codex.py:146-156`
   - Why risky: Different from Claude's positional argument approach
   - Mitigation: Verify stdin input works in practice, consider file-based input as alternative

### 3. **Session Log Parsing is Brittle** (Severity: Low)
   - Description: Fallback token extraction reads `~/.codex/sessions/rollout-*.jsonl`
   - Evidence: `saha/runners/codex.py:515-550`
   - Why risky: Log file location/format may change, CODEX_HOME env var dependency
   - Mitigation: Make this optional, log warning if logs not found

### 4. **Error Messages Assume CLI Availability** (Severity: Low)
   - Description: `is_available()` only checks `shutil.which("codex")`
   - Evidence: `saha/runners/codex.py:125-127`
   - Why incomplete: Doesn't verify authentication status or API key validity
   - Mitigation: Add authentication check in validation phase

## Open Questions

1. **Does Codex CLI actually accept prompts via stdin with `-` argument?**
   - Need to verify: `echo "prompt" | codex exec -` works
   - Alternative: Write prompt to temp file, use `codex exec @file.txt` (if supported)

2. **What is the actual output format from `--output-last-message`?**
   - Is it plain text or JSON?
   - Does it include tool metadata or just assistant response?
   - Need to: Run test execution and examine output file

3. **Are there undocumented flags or breaking changes in recent Codex versions?**
   - CLI is actively developed (launched April 2025, updated Feb 2026)
   - Need to: Check `codex --help` and `codex exec --help` on actual installation

4. **How does Codex handle long prompts with embedded agent specs?**
   - Agent specs can be 500+ lines
   - Skills add another 100-200 lines each
   - Total prompt could be 2000+ lines
   - Need to: Test with actual execution-implementer agent spec

## Recommendations

### Immediate Actions

1. **Install Codex CLI and run manual smoke test**
   - Command: `npm install -g @openai/codex` or `brew install --cask codex`
   - Test: Run simple `codex exec` with minimal prompt and verify output

2. **Verify stdin input method**
   - Test: `echo "Hello world" | codex exec - --output-last-message /tmp/out.txt`
   - If fails: Switch to temp file approach

3. **Validate command structure**
   - Run: `codex exec --help` and compare flags with implementation
   - Check: Any deprecated or renamed flags

4. **Test with real agent spec**
   - Use: `.claude/agents/execution-implementer.md` as test case
   - Verify: System prompt extraction, skill loading, context injection work end-to-end

### Code Changes Needed

**If manual testing succeeds:**
- No code changes needed
- Add integration test that requires actual Codex CLI (marked with `@pytest.mark.codex`)
- Document setup requirements in README

**If stdin method fails:**
- Refactor `_run()` to write prompt to temp file
- Change command to: `["codex", "exec", temp_file_path, ...]`
- Update tests to cover new approach

**If token usage extraction fails:**
- Make session log parsing optional (wrap in try/except, log debug message)
- Accept that token usage may not be available for Codex

### Testing Strategy

1. **Unit tests** (already exist, passing):
   - Skill loading: `test_codex_skills_prompt_includes_skill_bodies` ✓
   - Prompt building: `test_codex_prompt_builds_with_system_and_context` ✓
   - File tracking: `test_file_change_tracker_detects_added_and_changed` ✓
   - Command building: `test_codex_command_bypass_sandbox` ✓

2. **Manual integration test** (TODO):
   - Install Codex CLI
   - Set up API key / authentication
   - Run simple test with CodexRunner
   - Verify output, file changes, error handling

3. **E2E test** (future):
   - Run full execution loop with Codex runner
   - Compare artifacts with Claude runner (should be equivalent)

## Critical Assessment

**The claim that Codex runner is "broken" is premature.** The implementation is well-structured, follows correct patterns, and aligns with official Codex CLI documentation. All unit tests pass.

The real issue is **lack of validation**, not broken code. The runner needs:
1. Manual testing against real Codex CLI
2. Edge case handling based on actual behavior
3. Documentation of setup requirements

**Recommendation:** Run manual integration test before making any changes. The code may work perfectly as-is, or may need only minor adjustments based on real-world behavior.
