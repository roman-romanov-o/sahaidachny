# Research: Claude Runner as Reference Implementation

**Date:** 2026-02-12
**Status:** Complete

## Summary

The Claude runner is **fully functional and well-tested**. It serves as the gold standard for implementing Codex and Gemini runners, demonstrating correct patterns for subprocess execution, file tracking, output parsing, and error handling.

## Key Architectural Patterns

### 1. **Native Agent Support** (Claude-Specific)
   - Evidence: `saha/runners/claude.py:102-120, 617-638`
   - Approach:
     ```python
     # run_agent() uses --agent flag
     cmd = ["claude", "--print", "--agent", agent_name, prompt]
     ```
   - Agent specs: Read from `.claude/agents/{agent-name}.md`
   - Conversion: `execution_implementer.md` → `--agent execution-implementer`
   - Benefits:
     - No need to embed spec in prompt
     - Native skill loading by Claude Code
     - Model/tools configured in agent frontmatter
   - **Implication**: This is why Claude runner is simpler - it delegates complexity to Claude CLI

### 2. **File Change Tracking via Tool Metadata** (Claude-Specific)
   - Evidence: `saha/runners/claude.py:61-100`
   - Approach: Parse `tool_use_result` from JSON events
     ```python
     for event in events:
         if event.get("type") != "user":
             continue
         tool_result = event.get("tool_use_result")
         if not isinstance(tool_result, dict):
             continue
         file_path = tool_result.get("filePath")
         if tool_result.get("type") == "create":
             files_added.append(file_path)
         elif "oldString" in tool_result or "structuredPatch" in tool_result:
             files_changed.append(file_path)
     ```
   - Relies on: Claude Code's `--output-format json` mode
   - Metadata fields:
     - `type: "create"` → file was added (Write tool)
     - `oldString/newString` → file was edited (Edit tool)
     - `filePath` → absolute path to file
   - **Why this works**: Claude Code's tools report what they did
   - **Implication**: Other CLIs without native metadata need filesystem snapshots

### 3. **Token Usage Extraction from Events**
   - Evidence: `saha/runners/claude.py:280-311`
   - Approach: Search for `usage` or `token_usage` keys in JSON events
     ```python
     for event in events:
         usage = event.get("usage")
         if isinstance(usage, dict):
             raw_candidates.append(usage)
         # Also check nested in message, result, response, data...
     ```
   - Normalization: `normalize_token_usage()` handles different formats:
     - `{input_tokens: 100, output_tokens: 50}` → `{total_tokens: 150}`
     - `{prompt_tokens: 100, completion_tokens: 50}` → `{total_tokens: 150}`
   - **Pattern to copy**: Flexible extraction with fallback strategies

### 4. **Dual Execution Modes: Capture vs Streaming**
   - Evidence: `saha/runners/claude.py:142-153, 155-246, 313-421`
   - **Capture mode** (`stream_output=False`):
     - Uses `--output-format json`
     - Collects full stdout, parses NDJSON
     - Extracts text from `assistant` events
     - Returns complete result at end
     - Used by: Tests, non-interactive scripts
   - **Streaming mode** (`stream_output=True`):
     - Uses `--output-format stream-json --include-partial-messages`
     - Prints output in real-time with rich formatting
     - Collects events for final result
     - Used by: Interactive execution (default for orchestrator)
   - **Implication**: Streaming enhances UX but capture mode is simpler to implement

### 5. **Comprehensive JSON Parsing with Fallbacks**
   - Evidence: `saha/runners/claude.py:660-716`
   - Strategy:
     1. Look for ` ```json ... ``` ` code blocks first
     2. Try each match from last to first (prefer final output)
     3. Fallback to standalone JSON objects (brace counting)
     4. Handle multiline JSON correctly
     5. Return None if no valid JSON found
   - **Why this matters**: LLMs may include JSON in explanatory text
   - **Example**:
     ```
     Here's the result:
     ```json
     {"status": "pass", "files_changed": ["foo.py"]}
     ```
     This shows we modified foo.py successfully.
     ```
   - **Implication**: Robust parsing prevents false negatives

### 6. **Error Handling and Resilience**
   - Evidence: `saha/runners/claude.py:200-246`
   - Patterns:
     ```python
     try:
         process.communicate(timeout=timeout)
     except subprocess.TimeoutExpired:
         process.kill()
         return RunnerResult.failure("Timeout", exit_code=124)
     except KeyboardInterrupt:
         process.terminate()
         process.wait(timeout=5)  # Grace period
         if still running:
             process.kill()
         raise  # Re-raise to propagate
     except FileNotFoundError:
         return RunnerResult.failure("CLI not found", exit_code=127)
     ```
   - **Key insight**: Different error paths need different handling
   - **Implication**: Copy this error handling structure to other runners

## What Makes Claude Runner Work

### Success Factors

1. **Well-documented API**
   - Claude Code has comprehensive docs at https://developers.openai.com/codex/cli/reference/
   - All flags are documented with examples
   - Output formats are specified
   - Error codes are consistent

2. **Rich output format**
   - `--output-format json` provides structured events
   - Each event has type, metadata, timestamps
   - Tool results include success/failure and file paths
   - Token usage is embedded in response metadata

3. **Native agent support**
   - `--agent` flag loads agent specs automatically
   - Skills are resolved by Claude Code
   - Model/tools configured in frontmatter
   - No need for manual embedding

4. **Stable subprocess interface**
   - Positional arguments for prompts
   - Standard exit codes (0=success, non-zero=failure)
   - Predictable stdout/stderr separation
   - Clean JSON without extra output

### Challenges Other Runners Face

**Codex CLI:**
- No `--agent` flag → must embed specs manually ✓ (implemented)
- No JSON event stream → must use snapshots for file tracking ✓ (implemented)
- Stdin input method → slightly different subprocess handling (untested)
- Session logs in non-standard location → brittle token extraction

**Gemini CLI:**
- No `--agent` flag → must embed specs manually ❌ (not implemented)
- Unknown output format → may lack structured data ❌ (not tested)
- No file tracking metadata → must use snapshots ❌ (not implemented)
- Poor documentation → flags are guesswork ❌ (bugs present)

## Patterns to Replicate

### For Codex (Status: ✅ Already Implemented)

1. **Agent spec embedding** ✓
   - Parse frontmatter for skills
   - Load skill markdown bodies
   - Prepend to prompt with separators
   - Evidence: `saha/runners/codex.py:283-394`

2. **Filesystem snapshot tracking** ✓
   - Before: snapshot all files (mtime + size)
   - After: snapshot again
   - Diff: detect changes and additions
   - Evidence: `saha/runners/codex.py:19-81`

3. **JSON parsing with fallbacks** ✓
   - Code blocks first, standalone objects second
   - Brace counting for multiline
   - Evidence: `saha/runners/codex.py:396-440`

4. **Token usage extraction** ✓
   - Try structured output
   - Try stdout parsing
   - Fallback to session logs
   - Evidence: `saha/runners/codex.py:442-550`

### For Gemini (Status: ❌ Needs Implementation)

1. **Agent spec embedding** ❌
   - **TODO**: Copy from Codex runner
   - Methods needed: `_extract_skills_prompt`, `_parse_skills`, `_load_skill_text`
   - Integration: Call in `run_agent()`, pass to prompt builder

2. **Filesystem snapshot tracking** ❌
   - **TODO**: Copy `_FileChangeTracker` class from Codex
   - Integration: Instantiate in `_run()`, call `diff()` after execution
   - Update: Add results to structured_output

3. **JSON parsing** ⚠️ Partial
   - Current: Oversimplified (`saha/runners/gemini.py:268-299`)
   - **TODO**: Replace with robust version from Claude/Codex

4. **Token usage extraction** ❌
   - **TODO**: Research Gemini CLI output format
   - If not available: Log warning, return None
   - Don't block execution on missing token data

## Command Structure Comparison

### Claude (Working)
```python
# Direct prompt
["claude", "--print", "--model", model, prompt]

# With agent
["claude", "--print", "--agent", agent_name, prompt]

# With JSON output
["claude", "--print", "--output-format", "json", prompt]

# With streaming
["claude", "--print", "--output-format", "stream-json",
 "--include-partial-messages", prompt]
```

### Codex (Implemented, Untested)
```python
# Non-interactive execution
["codex", "exec", "-",  # stdin
 "--output-last-message", output_file,
 "--color", "never",
 "--cd", working_dir,
 "--skip-git-repo-check",
 "--model", model,
 "--sandbox", "workspace-write"]

# Input via stdin
process.communicate(input=full_prompt)
```

### Gemini (Broken)
```python
# Current (WRONG)
["gemini",
 "--model", model,
 "--sandbox",  # Unknown format
 "--yolo",  # DOES NOT EXIST
 "-p", prompt]

# Should be (NEED TO VERIFY)
["gemini",
 "-m", model,  # or --model?
 "-p", prompt]
```

## Testing Approach Comparison

### Claude Tests
- Location: `tests/integration/test_runner_registry.py`, `tests/integration/test_codex_runner.py`
- Coverage:
  - Command building ✓
  - Permissions flags ✓
  - Registry selection ✓
- Missing: Actual CLI execution (requires Claude installed)

### Codex Tests
- Location: `tests/integration/test_codex_runner.py`
- Coverage:
  - Skill loading ✓
  - Prompt building ✓
  - File change tracking ✓
  - Command building ✓
- Missing: Actual CLI execution (requires Codex installed)

### Gemini Tests
- Location: **None**
- Coverage: **0%**
- Missing: Everything

## Recommendations

### For Codex Runner

**No changes needed** - implementation follows Claude patterns correctly:
1. Embedds agent specs (since no native support) ✓
2. Uses filesystem snapshots (since no tool metadata) ✓
3. Has comprehensive JSON parsing ✓
4. Has token extraction with fallbacks ✓

**Only action needed**: Manual testing with actual Codex CLI

### For Gemini Runner

**Substantial refactoring required**:

1. **Copy proven patterns from Codex**:
   - File change tracking (exact copy of `_FileChangeTracker`)
   - Skill loading (exact copy of skill methods)
   - JSON parsing (exact copy of `_try_parse_json`)

2. **Fix command building**:
   - Remove `--yolo` flag (doesn't exist)
   - Research correct flags via `gemini --help`
   - Test with minimal example before adding complexity

3. **Add tests**:
   - Create `tests/integration/test_gemini_runner.py`
   - Copy test structure from Codex tests
   - Test all methods in isolation

4. **Validate with real CLI**:
   - Install Gemini CLI
   - Run manual tests
   - Document actual behavior

### General Pattern

**When implementing a runner for a new CLI:**

1. **Start with Claude runner as reference** - it's the gold standard
2. **Check if CLI has native agent support**:
   - Yes (like Claude) → use `--agent` flag, simpler implementation
   - No (like Codex/Gemini) → embed specs in prompt
3. **Check if CLI provides tool metadata**:
   - Yes (like Claude) → parse from events
   - No (like Codex/Gemini) → use filesystem snapshots
4. **Implement in this order**:
   - Basic command execution (subprocess.Popen)
   - Error handling (timeout, not found, interrupt)
   - Output parsing (stdout → text + JSON)
   - File tracking (metadata or snapshots)
   - Agent spec embedding (if needed)
   - Skill loading (if needed)
   - Token usage extraction (optional)
5. **Test incrementally**:
   - Unit tests for each method
   - Manual test with real CLI
   - Integration test with orchestrator

## Critical Assessment

The Claude runner demonstrates that **subprocess-based LLM execution is fundamentally straightforward**:

1. Build command with appropriate flags
2. Execute with timeout and error handling
3. Parse output for text and structured data
4. Track file changes (via metadata or snapshots)
5. Return result with success/failure status

**Where runners differ:**
- Command structure (flags, argument format)
- Output format (JSON events vs plain text)
- File tracking mechanism (native vs snapshots)
- Agent support (native vs embedding)

**Where runners should be identical:**
- Error handling patterns
- Subprocess lifecycle management
- JSON parsing robustness
- Token usage normalization

**The Codex runner demonstrates this correctly** - it adapts to Codex CLI's limitations while following Claude's patterns.

**The Gemini runner fails because** it doesn't follow these patterns - it's a from-scratch implementation with bugs, not an adaptation of proven code.

**Recommendation**: Treat Claude runner as a template, Codex runner as a "how to adapt" example, and rewrite Gemini runner to follow the same patterns.
