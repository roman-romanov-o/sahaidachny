# US-007: Improve Error Messages and Add Troubleshooting Guide

**Priority:** Should Have
**Status:** Draft
**Persona:** Sahaidachny Developer
**Estimated Complexity:** S (2-3 hours)

## User Story

As a **Sahaidachny Developer**,
I want **clear, actionable error messages when something goes wrong**,
So that **I can quickly diagnose and fix issues without needing to read source code**.

## Acceptance Criteria

1. **Given** any CLI runner fails
   **When** error is displayed to user
   **Then** error message includes:
   - What went wrong (clear description)
   - Why it went wrong (root cause if known)
   - How to fix it (specific steps)
   - Link to troubleshooting docs

2. **Given** common errors occur (auth failure, CLI not found, timeout)
   **When** user encounters these errors
   **Then** error messages match templates in troubleshooting guide (consistent format)

3. **Given** user needs help debugging
   **When** they consult troubleshooting guide
   **Then** guide includes:
   - Common error scenarios
   - Diagnostic commands
   - Step-by-step fixes
   - When to file bug reports

4. **Given** error occurs in CI/CD
   **When** viewing logs
   **Then** errors output structured JSON to stdout (machine-parseable) AND pretty-printed human-readable format to stderr

5. **Given** verbose mode is enabled
   **When** error occurs
   **Then** additional debug information is included (stack trace, context, state)

## Edge Cases

1. **Cryptic system errors**
   - Trigger: Low-level error (ECONNREFUSED, EPERM, etc.)
   - Expected behavior: Translate to user-friendly message with context

2. **Multiple cascading errors**
   - Trigger: One error causes others (auth fails → agent fails → loop fails)
   - Expected behavior: Show root cause first, hide cascading errors

3. **Intermittent errors**
   - Trigger: Network flakiness, rate limiting
   - Expected behavior: Suggest retry, explain retry strategy

## Technical Notes

**Error message template structure:**
```
╭─ Error: {ErrorType}
│
│  {clear_description}
│
├─ Cause
│  {root_cause_if_known}
│
├─ Fix
│  {specific_actionable_steps}
│
├─ Example
│  {example_command_if_relevant}
│
╰─ Docs: {troubleshooting_url}
```

**Example - CLI Not Found:**
```
╭─ Error: CodexCLINotFoundError
│
│  Codex CLI is not installed or not in your PATH.
│
├─ Cause
│  The 'codex' command could not be found.
│  Searched: /usr/local/bin, /usr/bin, ~/.local/bin
│
├─ Fix
│  1. Install Codex CLI:
│     npm install -g @openai/codex
│
│  2. Verify installation:
│     codex --version
│
│  3. Ensure CLI is in PATH:
│     echo $PATH | grep codex
│
├─ Example
│  # Quick setup
│  npm install -g @openai/codex
│  export OPENAI_API_KEY="sk-..."
│  saha run task-01 --runner codex
│
╰─ Docs: https://sahaidachny.dev/troubleshooting#codex-cli-not-found
```

**Example - Auth Failure:**
```
╭─ Error: AuthenticationError
│
│  API authentication failed for Codex runner.
│
├─ Cause
│  OPENAI_API_KEY environment variable is not set or is invalid.
│
├─ Fix
│  1. Get API key:
│     https://platform.openai.com/api-keys
│
│  2. Set environment variable:
│     export OPENAI_API_KEY="sk-proj-..."
│
│  3. Verify key works:
│     codex exec - <<< "echo test"
│
├─ Security
│  • Never commit API keys to git
│  • Use .env file (excluded in .gitignore)
│  • Rotate keys regularly
│
╰─ Docs: https://sahaidachny.dev/troubleshooting#auth-failure
```

**Troubleshooting guide structure:**
```markdown
# Troubleshooting Guide

## Quick Diagnostics

### Check CLI Installation
\`\`\`bash
claude --version   # Should show version
codex --version    # Should show version
gemini --version   # Should show version
\`\`\`

### Check API Keys
\`\`\`bash
echo $ANTHROPIC_API_KEY | grep -o '^.\\{10\\}'  # Shows first 10 chars
echo $OPENAI_API_KEY | grep -o '^.\\{10\\}'
echo $GEMINI_API_KEY | grep -o '^.\\{10\\}'
\`\`\`

## Common Errors

### 1. CLI Not Found
**Error:** `CodexCLINotFoundError: Codex CLI is not installed`

**Solution:**
[Detailed fix steps]

### 2. Authentication Failed
**Error:** `AuthenticationError: API authentication failed`

**Solution:**
[Detailed fix steps]

### 3. Agent Timeout
**Error:** `TimeoutError: Agent execution exceeded 300s`

**Solution:**
[Detailed fix steps]

## When to File a Bug Report

File a bug if:
- Error persists after following troubleshooting steps
- Error message is unclear or incorrect
- You found a workaround we should document

Include:
- Full error message
- Output of \`saha version\`
- Output of diagnostic commands above
- Minimal reproduction steps
```

**Key files to create/modify:**
- `docs/troubleshooting.md` - Main troubleshooting guide
- `saha/errors.py` - Custom exception classes with formatting
- `saha/cli.py` - Error handler that formats exceptions
- `saha/runners/*.py` - Raise custom exceptions with context

## Dependencies

- **Requires:**
  - US-006 completed (Graceful degradation)
- **Enables:**
  - Better user experience
  - Reduced support burden

## Questions

- [ ] Should error messages be localized (i18n) or English-only?
- [ ] Should we collect error telemetry (opt-in) to improve diagnostics?
- [ ] What's the right balance between concise and comprehensive error messages?

## Related

- Task: [task-description.md](../task-description.md)
- User Story: [US-006](US-006-graceful-degradation.md)
