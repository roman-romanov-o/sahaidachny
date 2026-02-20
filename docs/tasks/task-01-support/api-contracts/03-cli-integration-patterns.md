# API Contract: CLI Integration Patterns

**Type:** External Process Integration
**CLIs:** Claude Code CLI, Codex CLI, Gemini CLI
**Status:** Draft (Validating patterns)

## Overview

This contract defines how Sahaidachny invokes external CLI tools for each platform. Each CLI has different command structures, flags, and output formats that runners must handle correctly.

## Claude Code CLI

### Command Pattern

```bash
claude [options] [--agent <agent-name>] [--prompt <prompt>]
```

### Common Flags

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--print` | boolean | No | Non-interactive output mode |
| `--agent <name>` | string | No | Native agent invocation |
| `--prompt <text>` | string | No | User prompt to send |
| `--model <model>` | string | No | Model alias (sonnet, opus, haiku) |
| `--output-format <fmt>` | string | No | Output format (json, text) |

### Agent Invocation

```bash
claude --print \
       --agent execution-implementer \
       --prompt "Implement string utilities" \
       --model sonnet
```

**Features:**
- Native agent support (no manual spec embedding)
- Built-in tool execution tracking
- Structured output with `--output-format json`
- Permission prompts (can bypass with settings)

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | API key for authentication |
| `CLAUDE_MODEL` | No | Default model (overridable with `--model`) |

### Output Format

**Standard output:**
```
[Agent reasoning and tool calls]
Final response text

<tool_use_metadata>
{"files_changed": ["src/utils.py"], ...}
</tool_use_metadata>
```

**JSON output (`--output-format json`):**
```json
{
  "output": "Agent response text",
  "tool_uses": [...],
  "files_changed": ["src/utils.py"],
  "token_usage": {"input": 1234, "output": 567}
}
```

---

## Codex CLI

### Command Pattern

```bash
codex exec [options] [input-file | -]
```

### Common Flags

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `exec` | command | Yes | Execute non-interactive prompt |
| `-` | argument | No | Read prompt from stdin |
| `--output-last-message <file>` | string | No | Write final assistant message to file |
| `--cd <dir>` | string | No | Working directory |
| `--model <model>` | string | No | Model to use (o3, o1, gpt-4o) |
| `--sandbox <mode>` | string | No | Sandbox mode (read-only, workspace-write, danger-full-access) |
| `--skip-git-repo-check` | boolean | No | Skip git repository validation |
| `--dangerously-bypass-approvals-and-sandbox` | boolean | No | Auto-approve all tool calls (DANGER!) |

### Agent Invocation

```bash
# Build full prompt with agent spec embedded
prompt="$(cat agent-spec.md)\n\n---\n\n${user_prompt}"

# Send via stdin, capture output to file
echo "$prompt" | codex exec - \
  --output-last-message /tmp/codex-output.txt \
  --cd /path/to/project \
  --model o3 \
  --sandbox workspace-write \
  --skip-git-repo-check \
  --dangerously-bypass-approvals-and-sandbox
```

**Features:**
- No native agent support (embed spec in prompt)
- Stdin input for long prompts
- Output to file (cleaner than stdout capture)
- Sandbox modes for safety
- Non-interactive mode via `--dangerously-bypass-approvals-and-sandbox`

**Important:** Codex does NOT provide file change tracking metadata. Runners MUST use filesystem snapshots (before/after diff) to detect changes.

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | API key for authentication |
| `CODEX_MODEL` | No | Default model |

### Output Format

**File output (--output-last-message):**
```
Agent's final response text.
No structured metadata provided.

May include markdown code blocks with JSON:
```json
{
  "status": "success",
  "files_changed": ["src/utils.py"]
}
```
```

**Parser must:**
1. Read output file
2. Look for JSON in markdown blocks or standalone
3. Extract JSON if present
4. Fall back to text-only if no JSON

---

## Gemini CLI

### Command Pattern

```bash
gemini [options] -p <prompt>
```

### Common Flags

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `-p <text>` | string | Yes | Prompt to send |
| `--model <model>` | string | No | Model to use (gemini-2.5-pro, gemini-2.5-flash) |
| `-m <model>` | string | No | Model shorthand (alternative to --model) |
| `--sandbox` | boolean | No | Enable sandbox mode (if supported) |

**IMPORTANT:** The `--yolo` flag does NOT exist in Gemini CLI despite current implementation attempting to use it (see [research/02-gemini-runner-analysis.md](../research/02-gemini-runner-analysis.md)). This is a confirmed bug that must be fixed in US-002.

### Agent Invocation

```bash
# Build full prompt with agent spec + context
system_prompt="$(cat agent-spec.md)"
full_prompt="${system_prompt}\n\n---\n\n${user_prompt}"

# Send prompt
gemini --model gemini-2.5-pro \
       -p "$full_prompt"
```

**Features:**
- No native agent support (embed spec in prompt)
- Simple prompt-based interface
- No `--yolo` flag (bug in current implementation)
- Output to stdout

**Important:** Like Codex, Gemini CLI does NOT provide file change tracking or tool metadata. Runners MUST use filesystem snapshots.

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | API key for authentication |
| `GOOGLE_API_KEY` | Alternative | Alternative key name |
| `GEMINI_MODEL` | No | Default model |

### Output Format

**Standard output:**
```
Agent response text.

May include JSON in markdown or standalone:
```json
{
  "status": "success",
  "summary": "..."
}
```
```

**Parser must:**
1. Capture stdout
2. Look for JSON blocks or standalone JSON
3. Extract and parse JSON
4. Fall back to text-only if no JSON

---

## File Change Tracking Strategies

### Native (Claude Code)

Use `--output-format json` to get tool metadata:
```json
{
  "files_changed": ["src/utils.py", "tests/test_utils.py"],
  "tool_uses": [...]
}
```

### Filesystem Snapshots (Codex, Gemini)

1. **Before execution:** Take snapshot of filesystem
   ```python
   snapshot_before = {
       path: (stat.st_mtime, stat.st_size)
       for path in project_files
   }
   ```

2. **After execution:** Take new snapshot
   ```python
   snapshot_after = {
       path: (stat.st_mtime, stat.st_size)
       for path in project_files
   }
   ```

3. **Diff snapshots:**
   ```python
   files_changed = [
       path for path in snapshot_before
       if snapshot_after.get(path) != snapshot_before[path]
   ]
   files_added = [
       path for path in snapshot_after
       if path not in snapshot_before
   ]
   ```

**Implementation:** `_FileChangeTracker` class in `codex.py` (lines 19-81)

---

## Skill Loading Patterns

### Native (Claude Code)

Skills loaded automatically from `.claude/skills/` by Claude Code itself. No manual injection needed.

### Manual Injection (Codex, Gemini)

1. **Locate skills:**
   ```python
   skill_dirs = [
       Path(".claude/skills"),
       Path("claude_plugin/skills")
   ]
   ```

2. **Load skill definitions:**
   ```python
   for skill_path in skill_dirs:
       if skill_path.exists():
           skills = load_skills_from_dir(skill_path)
   ```

3. **Embed in prompt:**
   ```python
   prompt = f"""
   {agent_spec}

   ## Available Skills

   {skills_markdown}

   ---

   {user_prompt}
   """
   ```

**Implementation:** Skill loading methods in `codex.py` (lines 345-426)

---

## Error Codes

### Common Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | Continue |
| 1 | General error | Check stderr for details |
| 124 | Timeout | Retry or fail gracefully |
| 127 | CLI not found | Fail with clear install message |
| 130 | Interrupted (SIGINT) | Clean shutdown |
| 137 | Killed (SIGKILL) | Unexpected termination |

### Authentication Errors

- **Claude:** "Invalid API key" in stderr
- **Codex:** "401 Unauthorized" in output
- **Gemini:** "API key not found" or "Invalid credentials"

---

## Related

- **Stories:** US-001 (Codex), US-002 (Gemini)
- **Files:**
  - `saha/runners/claude.py:143-160` - Claude command building
  - `saha/runners/codex.py:220-243` - Codex command building
  - `saha/runners/gemini.py:191-212` - Gemini command building
- **Research:**
  - [04-cli-api-validation.md](../research/04-cli-api-validation.md) - CLI flag validation
  - [02-gemini-runner-analysis.md](../research/02-gemini-runner-analysis.md) - Gemini bugs
