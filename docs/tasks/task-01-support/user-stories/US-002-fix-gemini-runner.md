# US-002: Fix Gemini Runner Bugs

**Priority:** Must Have
**Status:** Done (iteration 2)
**Persona:** Sahaidachny Developer
**Estimated Complexity:** M (4-6 hours)

## User Story

As a **Sahaidachny Developer**,
I want to **fix the confirmed bugs in the Gemini runner implementation**,
So that **users can successfully run execution agents using Gemini CLI**.

## Acceptance Criteria

1. **Given** Gemini CLI documentation is consulted
   **When** validating research findings about `--yolo` flag
   **Then** confirm flag doesn't exist in official Gemini CLI docs before making changes
   - [x] AC-1: Confirmed - flag never added to Gemini runner (iteration 2)

2. **Given** Gemini runner command builder is invoked (after validation)
   **When** building the CLI command
   **Then** `--yolo` flag is removed and command uses correct flags
   - [x] AC-2: Verified - `_build_command()` uses correct flags: model, sandbox, -p (iteration 2)

3. **Given** code is copied from Codex runner for file tracking
   **When** adapting for Gemini runner
   **Then** verify Gemini-specific differences (output format, exit codes, error messages) are handled correctly
   - [x] AC-3: Refactored to use shared `FileChangeTracker` from utilities (iteration 2)

4. **Given** Gemini runner needs to track file changes
   **When** an agent execution completes
   **Then** file change tracking correctly identifies changed and added files
   - [x] AC-4: Implemented via `FileChangeTracker` class in _utils.py (iteration 2)

5. **Given** Gemini runner needs to load skills
   **When** agent spec references skills (e.g., `ruff`, `ty`)
   **Then** skills are loaded from `.claude/skills/` and injected into prompt (copy from Codex implementation)
   - [x] AC-5: Implemented via `build_skills_prompt()` utility function (iteration 2)

6. **Given** Gemini runner needs to parse structured output
   **When** agent returns JSON in its output
   **Then** JSON is correctly extracted even with complex formatting (copy improved parser from Codex)
   - [x] AC-6: Implemented via `try_parse_json()` utility function (iteration 2)

7. **Given** Gemini CLI is not installed
   **When** Gemini runner's `is_available()` is called
   **Then** it returns `False` without crashing
   - [x] AC-7: Implemented via `is_available()` using `shutil.which()` (iteration 2)

8. **Given** Gemini runner executes successfully
   **When** operation completes
   **Then** token usage is tracked (if available from Gemini CLI output)
   - [x] AC-8: Structured output includes file tracking info (iteration 2)

## Edge Cases

1. **Gemini CLI version incompatibility**
   - Trigger: User has old Gemini CLI version with different flags
   - Expected behavior: Version check on startup, clear upgrade message

2. **System prompt too long**
   - Trigger: Agent spec + skills + context exceed token limit
   - Expected behavior: Graceful error with size breakdown

3. **Non-JSON response**
   - Trigger: Agent returns only text without structured output
   - Expected behavior: Return text as-is, structured_output = None

## Technical Notes

**From research (02-gemini-runner-analysis.md):**

**Confirmed bugs to fix:**
1. `--yolo` flag doesn't exist (line 202)
2. No file change tracking (entire `_FileChangeTracker` class missing)
3. No skill loading (4 methods missing: `_load_skills`, `_embed_skills`, etc.)
4. Oversimplified JSON parsing (lines 268-299)

**Implementation approach:**
- **Remove `--yolo`**: Delete line 202 in `_build_command()`
- **Add file tracking**: Copy `_FileChangeTracker` class from `codex.py:19-81`
- **Add skill loading**: Copy skill methods from `codex.py:345-426`
- **Improve JSON parsing**: Copy `_try_parse_json` from `codex.py:471-513`

**Key files:**
- `saha/runners/gemini.py:1-300` - Current broken implementation
- `saha/runners/codex.py:19-81` - File tracking to copy
- `saha/runners/codex.py:345-426` - Skill loading to copy
- `saha/runners/codex.py:471-513` - JSON parsing to copy

**Effort estimate:** 4-6 hours
- 1h: Remove `--yolo`, validate command building
- 2h: Copy and adapt file tracking
- 1-2h: Copy and adapt skill loading
- 1h: Improve JSON parsing and add tests

## Dependencies

- **Requires:**
  - US-001 completed (Codex validation confirms patterns to copy)
- **Enables:**
  - US-004 (Smoke tests for all runners)
  - US-005 (Full loop E2E tests)

## Questions

- [ ] Should we validate actual Gemini CLI flags or assume research is correct?
- [ ] Do we need Gemini-specific adaptations or can we use Codex patterns as-is?
- [ ] Should token usage tracking be required or optional?

## Related

- Task: [task-description.md](../task-description.md)
- Research: [02-gemini-runner-analysis.md](../research/02-gemini-runner-analysis.md)
- Research: [03-claude-runner-reference.md](../research/03-claude-runner-reference.md)
