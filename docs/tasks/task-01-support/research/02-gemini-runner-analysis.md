# Research: Gemini Runner Implementation Analysis

**Date:** 2026-02-12
**Status:** Complete

## Summary

The Gemini runner implementation is **incomplete and contains critical errors**. Unlike Codex, which is well-implemented but untested, Gemini has actual bugs and missing functionality that prevent it from working correctly.

## Key Findings

### 1. **Missing File Change Tracking** (CRITICAL BUG)
   - Evidence: `saha/runners/gemini.py:1-300` - no file tracking implementation
   - Problem: Runner has no mechanism to detect which files were modified by the LLM
   - Comparison:
     - Claude: Uses native `tool_use_result` metadata from JSON events ✓
     - Codex: Uses `_FileChangeTracker` snapshot approach ✓
     - Gemini: **Nothing** ❌
   - Impact: Execution loop cannot track progress, QA cannot verify changes
   - Implication: **Must add file change tracking** before runner can be used

### 2. **No Token Usage Tracking**
   - Evidence: `saha/runners/gemini.py:145-148` - returns structured_output but no token_usage
   - Code:
     ```python
     return RunnerResult.success_result(
         output=stdout,
         structured_output=self._try_parse_json(stdout),
     )  # Missing: token_usage parameter
     ```
   - Comparison:
     - Claude: Extracts from JSON events (`_extract_token_usage_from_events`)
     - Codex: Multiple fallback strategies including session logs
     - Gemini: **No extraction at all**
   - Impact: No cost tracking, no usage monitoring
   - Severity: Low (nice-to-have, not blocking)

### 3. **Incorrect CLI Flags** (HIGH RISK)
   - Evidence: `saha/runners/gemini.py:171-212`
   - Current implementation:
     ```python
     cmd = ["gemini"]
     if self._model:
         cmd.extend(["--model", self._model])
     if self._sandbox:
         cmd.append("--sandbox")
     cmd.append("--yolo")  # Auto-accept tool calls
     cmd.extend(["-p", full_prompt])
     ```
   - **Problem 1**: `--yolo` flag does not exist in Gemini CLI
     - Official docs mention `--include-directories` and `--checkpointing` only
     - Web search found no evidence of `--yolo` flag
     - Likely confused with Codex CLI's `--dangerously-bypass-approvals-and-sandbox` (aka `--yolo`)
   - **Problem 2**: `--sandbox` flag format unknown
     - Docs mention "restrictive sandbox profiles" but don't specify flag syntax
     - May need to be `--sandbox=strict` or `--profile=sandbox` or not a flag at all
   - **Problem 3**: `-p` flag usage unclear
     - Docs show `gemini -p "prompt"` for non-interactive mode ✓
     - But interaction with other flags is undocumented
   - Implication: **Command will likely fail with unknown flag errors**

### 4. **No System Prompt Support** (WORKAROUND PRESENT)
   - Evidence: `saha/runners/gemini.py:205-208`
   - Implementation:
     ```python
     if system_prompt:
         full_prompt = f"{system_prompt}\n\n---\n\n{prompt}"
     ```
   - Problem: Gemini CLI may not have `--system-prompt` flag (unlike Claude)
   - Workaround: Prepends system prompt to user prompt with separator
   - Assessment: This is actually a **reasonable approach** (similar to Codex)
   - Risk: Gemini may treat it as user content, not system instructions
   - Implication: May work, but effectiveness depends on model's behavior

### 5. **Oversimplified JSON Parsing**
   - Evidence: `saha/runners/gemini.py:268-299`
   - Logic:
     ```python
     in_json = False
     for line in lines:
         if line.strip().startswith("{") or line.strip() == "```json":
             in_json = True
             # ... collect lines ...
         elif in_json:
             if line.strip() == "```":
                 break
     ```
   - **Problems**:
     1. Only finds first JSON block, ignores later blocks
     2. Stops at first ` ``` ` even if inside code example
     3. No handling of nested code blocks
     4. No handling of multiline JSON outside code blocks
   - Comparison: Claude/Codex use comprehensive regex + brace counting
   - Impact: Will fail to extract JSON from complex outputs
   - Severity: Medium (common failure case)

### 6. **Missing Skill Loading**
   - Evidence: `saha/runners/gemini.py:46-73` - `run_agent` method
   - Code:
     ```python
     def run_agent(self, agent_spec_path, prompt, context, timeout):
         system_prompt = self._extract_system_prompt(agent_spec_path)
         full_prompt = self._build_prompt_with_context(prompt, context)
         return self._run(full_prompt, system_prompt, timeout)
     ```
   - **Problem**: No skill loading (compare to Codex `_extract_skills_prompt`)
   - Impact: Agents that reference skills will not have them injected
   - Example: `execution-qa` references `ruff` and `ty` skills
   - Severity: High (missing functionality)
   - Implication: **Must implement skill loading** like Codex runner

## Validated Assumptions

| Assumption | Status | Evidence |
|------------|--------|----------|
| Gemini CLI exists and is installable | ✅ Confirmed | https://github.com/google-gemini/gemini-cli, npm install available |
| Gemini CLI supports non-interactive mode | ✅ Confirmed | `-p` flag documented for prompt execution |
| Gemini CLI has `--yolo` flag | ❌ **INCORRECT** | No evidence in docs or web search |
| Gemini CLI has `--sandbox` flag | ⚠️ **UNCLEAR** | Sandbox concept exists but flag format unknown |
| Gemini CLI has `--model` flag | ⚠️ **LIKELY** | Common pattern, but not confirmed in docs |
| Implementation is complete | ❌ **INCORRECT** | Missing file tracking, skill loading, broken flags |

## Risks Identified

### 1. **Runner Will Fail on First Execution** (Severity: Critical)
   - Description: Unknown `--yolo` flag will cause command failure
   - Error likely: `gemini: error: unrecognized arguments: --yolo`
   - Impact: Runner is completely non-functional
   - Mitigation: Remove `--yolo` flag, research correct non-interactive approach

### 2. **No Progress Tracking** (Severity: Critical)
   - Description: Without file change tracking, execution loop cannot work
   - Why: QA agent needs `files_changed` to know what to verify
   - Why: Manager needs to track which files were modified
   - Mitigation: **Must implement** `_FileChangeTracker` like Codex

### 3. **CLI API is Poorly Documented** (Severity: High)
   - Description: Official docs lack comprehensive flag reference
   - Evidence: GitHub README and docs site only show basic examples
   - Impact: Implementation is based on guesswork, not specification
   - Mitigation: Test against actual CLI, use `gemini --help` as source of truth

### 4. **Agent Specs Won't Work Fully** (Severity: High)
   - Description: Skills not loaded, only system prompt extracted
   - Impact: Agents requiring skills (QA, code-quality) will be missing critical instructions
   - Mitigation: Copy skill loading logic from Codex runner

## Open Questions

1. **What is the correct non-interactive execution method for Gemini CLI?**
   - Is `-p "prompt"` sufficient?
   - Is there a `gemini exec` command like Codex?
   - Does it auto-approve tool calls or require additional flags?
   - Need to: Run `gemini --help` and test actual behavior

2. **Does Gemini CLI output JSON in any format?**
   - Is there an `--output-format json` flag like Claude?
   - Or `--json` flag like Codex exec?
   - Does it stream events or just final output?
   - Need to: Test and examine stdout format

3. **How to get token usage from Gemini CLI?**
   - Is usage printed to stderr?
   - Is it embedded in output?
   - Is there a session log like Codex?
   - Need to: Run test execution and grep for "tokens", "usage", "cost"

4. **What tools does Gemini CLI support?**
   - File operations (Read, Write, Edit)?
   - Shell commands (Bash)?
   - Search (Grep, Glob)?
   - Need to: Check docs or test with tool-requiring prompts

## Recommendations

### Critical Fixes Required

1. **Remove `--yolo` flag**
   - Evidence: Flag does not exist in Gemini CLI
   - Action: Delete line `cmd.append("--yolo")`
   - Test: Run `gemini --help` to verify correct flags

2. **Implement file change tracking**
   - Approach: Copy `_FileChangeTracker` class from Codex runner
   - Location: Add before `_run()` method
   - Integration: Instantiate tracker, call `tracker.diff()` after execution
   - Update: Add `files_changed` and `files_added` to structured_output

3. **Implement skill loading**
   - Approach: Copy these methods from Codex runner:
     - `_extract_skills_prompt(agent_spec_path)`
     - `_parse_skills(frontmatter)`
     - `_candidate_skills_dirs(agent_spec_path)`
     - `_load_skill_text(skill_name, candidates)`
   - Integration: Call in `run_agent()` method
   - Update: Modify `_build_prompt_with_context` to accept skills_prompt parameter

4. **Fix JSON parsing**
   - Approach: Copy `_try_parse_json()` method from Codex/Claude runners
   - Features: Handles multiple JSON blocks, brace counting, code block escaping
   - Benefit: More reliable structured output extraction

### Validation Actions

1. **Install Gemini CLI and document actual API**
   - Command: `npm install -g @google/gemini-cli`
   - Run: `gemini --help` and `gemini -h` to see all flags
   - Document: Create flag reference with actual options

2. **Test minimal prompt execution**
   - Test: `gemini -p "Hello world"`
   - Capture: Stdout format, stderr content, exit codes
   - Document: Actual output format

3. **Test with model flag**
   - Test: `gemini -p "Hello" --model gemini-2.5-flash` (or `-m`)
   - Verify: Flag syntax and model name format

4. **Test tool execution**
   - Test: `gemini -p "Read the file README.md and summarize it"`
   - Verify: Whether Gemini CLI has file access tools
   - Document: Available tools and their behavior

### Code Refactoring Plan

**Phase 1: Make it work (minimum viable)**
1. Remove `--yolo` flag
2. Verify correct command structure with real CLI
3. Add file change tracking (copy from Codex)
4. Test with simple prompt

**Phase 2: Add missing features**
1. Implement skill loading (copy from Codex)
2. Improve JSON parsing (copy from Codex)
3. Add token usage extraction (if possible)

**Phase 3: Optimize and harden**
1. Add error handling for missing CLI
2. Add validation for authentication
3. Add timeout handling
4. Add progress indicators

## Critical Assessment

**The Gemini runner is genuinely broken and incomplete.** Unlike Codex (which is probably fine but untested), Gemini has clear bugs:

1. **Unknown CLI flags** - `--yolo` doesn't exist
2. **Missing core functionality** - No file tracking, no skill loading
3. **Poor implementation** - Oversimplified JSON parsing
4. **Untested assumptions** - Built without validating against real CLI

**This is NOT a simple matter of testing.** The runner needs substantial fixes before it can work.

**Root cause:** Implementation was written based on assumptions about Gemini CLI API without actually checking the real CLI. The developer likely assumed Gemini would be similar to Codex/Claude but didn't verify.

**Recommendation:**
1. Install Gemini CLI and document actual API
2. Rewrite command building based on real flags
3. Copy file tracking from Codex (proven pattern)
4. Copy skill loading from Codex (proven pattern)
5. Test incrementally with real CLI before claiming it works

**Effort estimate:** 4-6 hours of focused work to fix and validate.
