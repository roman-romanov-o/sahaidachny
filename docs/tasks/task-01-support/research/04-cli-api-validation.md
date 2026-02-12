# Research: CLI API Validation and Documentation Gaps

**Date:** 2026-02-12
**Status:** Complete

## Summary

Research into the actual Codex and Gemini CLI APIs reveals **significant documentation gaps and uncertainties**. The implementations make assumptions that need validation against real CLI installations. Neither CLI has comprehensive public documentation comparable to Claude Code.

## Codex CLI API Research

### Official Documentation Status

**Sources checked:**
- https://developers.openai.com/codex/cli/reference/ - Command reference page ✓
- https://github.com/openai/codex - Official GitHub repo ✓
- https://developers.openai.com/codex - Main docs site ✓

**Quality assessment:** Good
- Comprehensive flag reference exists
- `codex exec` mode documented
- Examples provided for common use cases
- Official documentation site maintained

### Validated Flags (Codex)

| Flag | Status | Evidence | Usage in Runner |
|------|--------|----------|----------------|
| `codex exec` | ✅ Confirmed | Official docs | `saha/runners/codex.py:223` |
| `--output-last-message, -o <path>` | ✅ Confirmed | Official docs | `saha/runners/codex.py:226` ✓ |
| `--cd, -C <path>` | ✅ Confirmed | Official docs | `saha/runners/codex.py:230` ✓ |
| `--skip-git-repo-check` | ✅ Confirmed | Official docs | `saha/runners/codex.py:232` ✓ |
| `--model, -m <string>` | ✅ Confirmed | Official docs | `saha/runners/codex.py:236` ✓ |
| `--sandbox, -s <policy>` | ✅ Confirmed | Policies: read-only \| workspace-write \| danger-full-access | `saha/runners/codex.py:241` ✓ |
| `--dangerously-bypass-approvals-and-sandbox` | ✅ Confirmed | Also aliased as `--yolo` | `saha/runners/codex.py:239` ✓ |
| `--color <never\|auto\|always>` | ✅ Confirmed | Official docs | `saha/runners/codex.py:228` ✓ |
| Reading from stdin with `-` | ⚠️ **UNCONFIRMED** | Not documented, but common pattern | `saha/runners/codex.py:225` **NEEDS TESTING** |

### Open Questions (Codex)

1. **Does `codex exec -` actually read from stdin?**
   - Evidence: Not explicitly documented
   - Alternative: `codex exec @file.txt` for file input (also undocumented)
   - Risk: High - entire input mechanism relies on this
   - **Action needed**: Test with actual CLI

2. **What is the exact format of `--output-last-message` file?**
   - Is it plain text only?
   - Does it include any metadata?
   - Is it UTF-8 encoded?
   - **Action needed**: Run test and examine file contents

3. **Does `--ephemeral` flag affect our use case?**
   - Docs say: "Run without persisting session files"
   - Question: Should we use this for orchestrator runs?
   - Benefit: Cleaner, no session pollution
   - Risk: Might break token usage extraction from session logs
   - **Action needed**: Test with and without flag

4. **What is the exit code for timeout vs error vs success?**
   - Success: Likely 0
   - Error: Likely 1
   - Timeout: Unknown (we assume 124 but should verify)
   - **Action needed**: Test error scenarios

5. **Can we use `--json` for structured output?**
   - Docs mention: "Output newline-delimited JSON events"
   - Question: Does this provide file change metadata like Claude?
   - Benefit: Would eliminate need for filesystem snapshots
   - **Action needed**: Test and examine JSON structure

## Gemini CLI API Research

### Official Documentation Status

**Sources checked:**
- https://github.com/google-gemini/gemini-cli - Official GitHub repo ✓
- https://geminicli.com/docs/ - Official docs site ⚠️ Limited
- https://google-gemini.github.io/gemini-cli/docs/cli/commands.html - CLI commands ⚠️ Interactive only
- https://developers.google.com/gemini-code-assist/docs/gemini-cli - Google Developer docs ⚠️ Basic

**Quality assessment:** Poor
- No comprehensive flag reference
- Most docs focus on interactive mode
- Non-interactive mode barely documented
- No examples of programmatic usage

### Validated Flags (Gemini)

| Flag | Status | Evidence | Usage in Runner |
|------|--------|----------|----------------|
| `gemini` (basic command) | ✅ Confirmed | All docs | `saha/runners/gemini.py:191` |
| `-p <prompt>` | ✅ Confirmed | WebFetch result, GitHub README | `saha/runners/gemini.py:210` ✓ |
| `-m <model>` | ⚠️ Likely | Common pattern, not confirmed | `saha/runners/gemini.py:195` **UNCONFIRMED** |
| `--model <model>` | ⚠️ Alternative | May use long form instead | Alternative to `-m` |
| `--output-format json` | ⚠️ Mentioned | WebFetch mentions it but no details | **NOT USED** in runner |
| `--output-format stream-json` | ⚠️ Mentioned | WebFetch mentions it but no details | **NOT USED** in runner |
| `--include-directories` | ✅ Confirmed | CLI docs page | **NOT USED** in runner |
| `--yolo` | ❌ **DOES NOT EXIST** | No evidence found | `saha/runners/gemini.py:202` **BUG** |
| `--sandbox` | ⚠️ Unknown format | Concept exists but flag format unclear | `saha/runners/gemini.py:199` **UNCONFIRMED** |

### Critical Issues (Gemini)

1. **`--yolo` flag does not exist**
   - Evidence: Not in any documentation
   - Not in GitHub repo
   - Not mentioned in web search results
   - Likely confusion with Codex CLI's flag
   - **Impact**: Runner will fail immediately with unknown flag error
   - **Fix**: Remove this flag, research correct approach

2. **Sandbox mode format unknown**
   - Docs mention: "restrictive sandbox profiles"
   - But no flag syntax documented
   - May be `--sandbox`, `--sandbox=strict`, `--profile=sandbox`, or not a flag at all
   - Current implementation: `cmd.append("--sandbox")` (boolean flag)
   - **Impact**: May fail or may silently not work as intended
   - **Fix**: Test with actual CLI or remove until confirmed

3. **Model selection format unclear**
   - Implementation assumes: `--model gemini-2.5-pro`
   - Alternative: `-m gemini-2.5-pro`
   - Alternative: `--model=gemini-2.5-pro`
   - No documentation confirms which format
   - **Impact**: May fail with wrong flag format
   - **Fix**: Test all variations with actual CLI

### Open Questions (Gemini)

1. **How to run Gemini CLI in truly non-interactive mode?**
   - Current: `gemini -p "prompt"`
   - Question: Does this auto-approve tool calls?
   - Or does it still prompt for confirmation?
   - If prompts: How to auto-approve?
   - **Action needed**: Test with tool-requiring prompt

2. **What is the output format from `gemini -p`?**
   - Plain text only?
   - Mixed text + JSON?
   - Formatted with colors/markup?
   - **Action needed**: Run test and examine stdout

3. **Does Gemini CLI support `--output-format json`?**
   - WebFetch mentioned it
   - But no details in docs
   - Question: What JSON structure does it produce?
   - Does it include file change metadata?
   - **Action needed**: Test with flag and examine output

4. **What tools does Gemini CLI support?**
   - File operations (Read, Write, Edit)?
   - Shell commands?
   - Search?
   - Web access?
   - **Action needed**: Run with tool-requiring prompt and observe behavior

5. **Where are token usage stats?**
   - In stdout?
   - In stderr?
   - In a log file?
   - Not available at all?
   - **Action needed**: Run test and grep all output

## Documentation Quality Comparison

### Claude Code CLI: Grade A
- **Strengths**:
  - Comprehensive flag reference
  - Output format documented
  - Examples for all use cases
  - Error codes specified
  - Native agent support documented
- **Weaknesses**: None significant
- **Usability**: Can implement runner from docs alone

### Codex CLI: Grade B
- **Strengths**:
  - Good flag reference
  - Non-interactive mode documented
  - Sandbox policies clear
  - Official docs maintained
- **Weaknesses**:
  - Stdin input not explicitly documented
  - Output formats not fully specified
  - Session log structure not documented
- **Usability**: Need some testing to fill gaps

### Gemini CLI: Grade D
- **Strengths**:
  - Basic usage shown
  - `-p` flag for prompts documented
- **Weaknesses**:
  - No comprehensive flag reference
  - Non-interactive mode barely covered
  - Output formats unclear
  - No programmatic usage examples
  - Recent (launched 2026) so docs may be incomplete
- **Usability**: Cannot implement correctly without extensive testing

## Risk Assessment

### Codex Runner Risks

1. **Stdin input method** (Medium risk)
   - Assumption: `codex exec -` reads from stdin
   - If wrong: Need to use file-based input
   - Mitigation: Test immediately, easy to fix if needed

2. **Session log parsing** (Low risk)
   - Fallback only, not critical path
   - If breaks: Token usage won't be available but execution continues
   - Mitigation: Wrap in try/except, log warning

3. **JSON output format** (Low risk)
   - If `--json` flag provides rich metadata, could simplify implementation
   - If not: Current approach (snapshots) works fine
   - Mitigation: Research as optimization, not blocking

### Gemini Runner Risks

1. **Unknown flags** (Critical risk)
   - `--yolo` definitely wrong
   - `--sandbox` format unknown
   - `--model` vs `-m` unclear
   - Impact: Command will fail immediately
   - Mitigation: **Must** test with actual CLI before any claims of working

2. **No file tracking** (Critical risk)
   - No implementation at all
   - Execution loop cannot work without it
   - Mitigation: Copy from Codex (proven pattern)

3. **Unknown output format** (High risk)
   - Don't know what `gemini -p "..."` outputs
   - JSON parsing may fail completely
   - Structured output extraction unreliable
   - Mitigation: Test and adapt parser to actual format

4. **Tool support unknown** (High risk)
   - Don't know if Gemini CLI can read/write files
   - Agents require file tools to work
   - If not supported: Runner is useless for orchestrator
   - Mitigation: Test with file operation prompts

## Validation Checklist

### Before Claiming Codex Runner Works

- [ ] Install Codex CLI: `npm install -g @openai/codex`
- [ ] Authenticate: `codex auth` or API key setup
- [ ] Test stdin input: `echo "Hello" | codex exec -`
- [ ] Test output file: `codex exec ... --output-last-message /tmp/test.txt`
- [ ] Test with agent spec: Full execution-implementer prompt
- [ ] Test file operations: Verify Write/Edit tools work
- [ ] Test JSON output: Try `--json` flag and examine structure
- [ ] Test error scenarios: Timeout, invalid model, network error
- [ ] Document actual behavior vs assumptions

### Before Claiming Gemini Runner Works

- [ ] Install Gemini CLI: `npm install -g @google/gemini-cli`
- [ ] Authenticate: `gemini auth` or API key setup
- [ ] Test help: `gemini --help` to see all flags
- [ ] Test basic prompt: `gemini -p "Hello world"`
- [ ] Test model flag: Try `-m` and `--model` variations
- [ ] Test tool execution: `gemini -p "Read file README.md"`
- [ ] Test output format: Try `--output-format json` if exists
- [ ] Remove `--yolo` flag from implementation
- [ ] Implement file change tracking
- [ ] Implement skill loading
- [ ] Test with real agent spec
- [ ] Document actual behavior vs assumptions

## Recommendations

### Immediate Actions

1. **Create CLI validation scripts**
   - Location: `scripts/validate-codex-cli.sh` and `scripts/validate-gemini-cli.sh`
   - Purpose: Quick tests to verify CLI behavior
   - Content: Basic commands to test flags, output format, tools
   - Benefit: Repeatable validation during development

2. **Document actual API in research folder**
   - Create: `research/codex-cli-actual-api.md`
   - Create: `research/gemini-cli-actual-api.md`
   - Content: Output of `--help`, test results, flag behavior
   - Benefit: Source of truth for implementation

3. **Add integration tests with real CLIs**
   - Mark with: `@pytest.mark.codex` and `@pytest.mark.gemini`
   - Run conditionally: Skip if CLI not installed
   - Cover: Command execution, output parsing, file tracking, error handling
   - Benefit: Catch regressions, validate assumptions

### Testing Strategy

**Phase 1: Manual validation (1-2 hours)**
- Install both CLIs
- Run validation scripts
- Document findings
- Update implementation based on reality

**Phase 2: Fix Gemini runner (4-6 hours)**
- Remove wrong flags
- Add file tracking
- Add skill loading
- Fix JSON parsing
- Test with validation script

**Phase 3: Automated tests (2-3 hours)**
- Write integration tests for both runners
- Mark as requiring real CLIs
- Add to CI with conditional execution
- Document test setup requirements

**Phase 4: End-to-end validation (2-3 hours)**
- Run full orchestrator loop with Codex
- Run full orchestrator loop with Gemini
- Compare outputs with Claude
- Validate artifact equivalence

## Critical Assessment

**The root problem is not code quality - it's validation methodology.**

The Codex runner was **implemented against documentation** (good practice) but never validated against the real CLI (bad practice). The Gemini runner was **implemented based on assumptions** (very bad practice) without even checking documentation thoroughly.

**This is a classic "works in theory" situation.**

**What we know for certain:**
1. Claude runner works ✓ (tested in production)
2. Codex runner architecture is sound ✓ (follows patterns, matches docs)
3. Gemini runner has bugs ✓ (wrong flags, missing features)

**What we don't know:**
1. Does Codex runner actually work? (probably yes, but unconfirmed)
2. What flags does Gemini CLI actually support? (unknown)
3. What output format do these CLIs produce? (unknown)
4. Do they support the tools agents need? (unknown)

**The solution is straightforward:**
1. Install the CLIs
2. Test with them
3. Fix any discrepancies
4. Document actual behavior
5. Add automated tests

**This is 90% validation work, 10% coding.**

The task description's focus on "fixing broken implementations" is misguided. The real task is **"validate implementations against real CLIs and fix any discovered issues."**

**Estimated effort:**
- Codex: 2-3 hours (mostly validation, minimal fixes expected)
- Gemini: 6-8 hours (validation + substantial fixes required)
- Total: 8-11 hours of focused work
