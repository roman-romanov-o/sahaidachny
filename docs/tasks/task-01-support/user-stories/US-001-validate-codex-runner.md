# US-001: Validate Codex Runner with Real CLI

**Priority:** Must Have
**Status:** Done (iteration 2)
**Persona:** Test Engineer
**Estimated Complexity:** S (2-4 hours)

## User Story

As a **Test Engineer**,
I want to **validate the Codex runner works with the actual Codex CLI**,
So that **we can confirm it doesn't need fixes before deploying to users**.

## Acceptance Criteria

1. **Given** Codex CLI is installed and API key is configured
   **When** I run a smoke test invoking a simple agent via Codex runner
   **Then** the runner successfully executes and returns valid output
   - [x] AC-1: Verified in iteration 2 with refactored runner using shared utilities

2. **Given** Codex runner is invoked with an agent spec
   **When** the agent spec includes skill references (e.g., `ruff`, `ty`)
   **Then** skills are properly loaded and injected into the prompt
   - [x] AC-2: Implemented via `build_skills_prompt()` utility (tested in test_codex_skills_prompt_includes_skill_bodies)

3. **Given** Codex runner completes an agent invocation
   **When** file changes are made during execution
   **Then** file change tracking correctly identifies changed and added files
   - [x] AC-3: Implemented via `FileChangeTracker` class (tested in test_file_change_tracker_detects_added_and_changed)

4. **Given** Codex CLI is not installed
   **When** Codex runner's `is_available()` is called
   **Then** it returns `False` and logs debug message "Codex CLI not found in PATH" without raising an exception
   - [x] AC-4: Implemented via `is_available()` using `shutil.which()`

5. **Given** API key is invalid or expired
   **When** Codex runner attempts to execute
   **Then** a clear error message is returned explaining the auth failure
   - [x] AC-5: Handled in `_run()` error handling for non-zero exit codes

## Edge Cases

1. **Codex CLI not in PATH**
   - Trigger: CLI not installed or not in system PATH
   - Expected behavior: `is_available()` returns False, runner is skipped gracefully

2. **Agent execution timeout**
   - Trigger: Agent takes longer than configured timeout (default 300s)
   - Expected behavior: Process terminates, timeout error returned with partial output

3. **Invalid agent spec format**
   - Trigger: Agent spec markdown has malformed frontmatter
   - Expected behavior: Clear error indicating which spec file is invalid

## Technical Notes

**From research (01-codex-runner-analysis.md):**
- Codex runner is well-implemented (550 lines) and likely works without changes
- Command structure matches official Codex CLI documentation
- File change tracking uses `_FileChangeTracker` class with snapshot approach
- Skill loading from `.claude/skills/` is implemented via `_load_skills()` method
- Research shows 80% confidence it works as-is

**Key files:**
- `saha/runners/codex.py:1-550` - Full implementation
- `saha/runners/codex.py:220-243` - Command building
- `saha/runners/codex.py:19-81` - File change tracking

**Validation approach:**
- Install Codex CLI: `npm install -g @openai/codex`
- Set `OPENAI_API_KEY` environment variable
- Run with real agent spec (e.g., execution-implementer.md)
- Verify file tracking works with real filesystem

## Dependencies

- **Requires:**
  - Codex CLI installation documentation
  - API key for testing (can use shared test account)
- **Enables:**
  - US-004 (Smoke tests for all runners)
  - US-005 (Full loop E2E tests)

## Questions

- [ ] Do we have a shared Codex test API key or should each dev use their own?
- [ ] What's the acceptable timeout for agent execution (300s default OK)?
- [ ] Should validation use containerized Codex or host installation?

## Related

- Task: [task-description.md](../task-description.md)
- Research: [01-codex-runner-analysis.md](../research/01-codex-runner-analysis.md)
- Research: [04-cli-api-validation.md](../research/04-cli-api-validation.md)
