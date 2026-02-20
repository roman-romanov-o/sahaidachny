# Unit Test Spec: Runner Utilities

**File:** `saha/runners/*.py`
**Priority:** High
**Status:** Draft

## Overview

Unit tests for isolated runner utility functions: file change tracking, skill loading, JSON parsing, and command building.

## Test Cases

### File Change Tracking (_FileChangeTracker)

#### TC-UNIT-001: FileChangeTracker Detects Modified Files

**Input:**
```python
tracker = _FileChangeTracker(project_dir=Path("/tmp/test"))
tracker.snapshot_before()

# Modify file
(project_dir / "file.txt").write_text("new content")

tracker.snapshot_after()
changed, added = tracker.get_changes()
```

**Expected:** `changed = ["file.txt"]`, `added = []`

**Assertions:**
```python
assert "file.txt" in changed
assert len(added) == 0
```

---

#### TC-UNIT-002: FileChangeTracker Detects Added Files

**Input:**
```python
tracker = _FileChangeTracker(project_dir)
tracker.snapshot_before()

# Create new file
(project_dir / "new.txt").write_text("content")

tracker.snapshot_after()
changed, added = tracker.get_changes()
```

**Expected:** `changed = []`, `added = ["new.txt"]`

**Assertions:**
```python
assert len(changed) == 0
assert "new.txt" in added
```

---

#### TC-UNIT-003: FileChangeTracker Handles Nested Directories

**Input:**
```python
tracker.snapshot_before()

# Create nested structure
(project_dir / "src" / "utils").mkdir(parents=True)
(project_dir / "src" / "utils" / "helper.py").write_text("code")

tracker.snapshot_after()
changed, added = tracker.get_changes()
```

**Expected:** `added = ["src/utils/helper.py"]`

**Assertions:**
```python
assert "src/utils/helper.py" in added
```

---

#### TC-UNIT-004: FileChangeTracker Detects mtime and Size Changes

**Input:**
```python
tracker.snapshot_before()

# Touch file (change mtime but not content)
os.utime(project_dir / "file.txt", None)

tracker.snapshot_after()
changed, added = tracker.get_changes()
```

**Expected:** `changed = ["file.txt"]` (mtime changed, so file considered modified)

**Notes:** File tracker uses (mtime, size) tuple for change detection. Any change to either mtime or size triggers detection. This is simpler than content hashing and sufficient for agent execution tracking.

---

### Skill Loading

#### TC-UNIT-010: _load_skills Finds Skills in Directory

**Input:**
```python
# Create skill files
skills_dir = Path(".claude/skills")
skills_dir.mkdir(parents=True)
(skills_dir / "ruff.md").write_text("# Ruff Skill\nLinting tool")
(skills_dir / "ty.md").write_text("# Ty Skill\nType checker")

skills = runner._load_skills(skills_dir)
```

**Expected:** `skills = {"ruff": "# Ruff Skill\nLinting tool", "ty": "# Ty Skill\nType checker"}`

**Assertions:**
```python
assert "ruff" in skills
assert "ty" in skills
assert "Ruff Skill" in skills["ruff"]
assert "Ty Skill" in skills["ty"]
```

---

#### TC-UNIT-011: _load_skills Handles Missing Directory

**Input:** `skills = runner._load_skills(Path("/nonexistent"))`

**Expected:** Returns empty dict `{}`

**Assertions:**
```python
assert skills == {}
```

---

#### TC-UNIT-012: _embed_skills Formats Skills as Markdown

**Input:**
```python
skills = {"ruff": "# Ruff\nLinter", "ty": "# Ty\nType checker"}
embedded = runner._embed_skills(skills)
```

**Expected:**
```markdown
## Available Skills

### ruff
# Ruff
Linter

### ty
# Ty
Type checker
```

**Assertions:**
```python
assert "## Available Skills" in embedded
assert "### ruff" in embedded
assert "### ty" in embedded
```

---

### JSON Parsing

#### TC-UNIT-020: _try_parse_json Extracts JSON from Markdown

**Input:**
```python
output = '''
Some text before

```json
{"status": "success", "files": ["a.py"]}
```

Some text after
'''
parsed = runner._try_parse_json(output)
```

**Expected:** `parsed = {"status": "success", "files": ["a.py"]}`

**Assertions:**
```python
assert parsed["status"] == "success"
assert "a.py" in parsed["files"]
```

---

#### TC-UNIT-021: _try_parse_json Handles Standalone JSON

**Input:**
```python
output = '{"key": "value"}'
parsed = runner._try_parse_json(output)
```

**Expected:** `parsed = {"key": "value"}`

---

#### TC-UNIT-022: _try_parse_json Returns None for Non-JSON

**Input:**
```python
output = "Just plain text with no JSON"
parsed = runner._try_parse_json(output)
```

**Expected:** `parsed = None`

**Assertions:**
```python
assert parsed is None
```

---

#### TC-UNIT-023: _try_parse_json Handles Multiple JSON Blocks

**Input:**
```python
output = '''
```json
{"first": "block"}
```

Some text

```json
{"second": "block"}
```
'''
parsed = runner._try_parse_json(output)
```

**Expected:** Returns first valid JSON block

**Assertions:**
```python
assert parsed["first"] == "block"
```

---

### Command Building

#### TC-UNIT-030: Codex _build_command Uses Stdin

**Input:**
```python
runner = CodexRunner(working_dir=Path("/tmp"))
cmd = runner._build_command(
    full_prompt="Test prompt",
    output_file=Path("/tmp/out.txt")
)
```

**Expected:**
```bash
codex exec - \
  --output-last-message /tmp/out.txt \
  --cd /tmp \
  --model o3 \
  --skip-git-repo-check \
  --dangerously-bypass-approvals-and-sandbox
```

**Assertions:**
```python
assert "codex" in cmd
assert "exec" in cmd
assert "-" in cmd  # stdin
assert "--output-last-message" in cmd
assert "/tmp/out.txt" in cmd
```

---

#### TC-UNIT-031: Gemini _build_command No --yolo Flag

**Input:**
```python
runner = GeminiRunner(working_dir=Path("/tmp"))
cmd = runner._build_command(prompt="Test")
```

**Expected:** Command does NOT contain `--yolo`

**Assertions:**
```python
assert "--yolo" not in cmd
assert "gemini" in cmd
assert "-p" in cmd or "--prompt" in cmd
```

---

#### TC-UNIT-032: Claude _build_command Uses --print Flag

**Input:**
```python
runner = ClaudeRunner(working_dir=Path("/tmp"))
cmd = runner._build_command(prompt="Test")
```

**Expected:**
```bash
claude --print --prompt "Test"
```

**Assertions:**
```python
assert "claude" in cmd
assert "--print" in cmd
assert "--prompt" in cmd or prompt in cmd
```

---

### RunnerResult Helpers

#### TC-UNIT-040: RunnerResult.success_result Creates Success

**Input:**
```python
result = RunnerResult.success_result(
    output="Agent output",
    structured_output={"status": "done"},
    tokens_used=100
)
```

**Expected:**
- `success`: True
- `exit_code`: 0
- `output`: "Agent output"
- `structured_output`: {"status": "done"}
- `tokens_used`: 100

**Assertions:**
```python
assert result.success is True
assert result.exit_code == 0
assert result.output == "Agent output"
assert result.structured_output["status"] == "done"
assert result.tokens_used == 100
```

---

#### TC-UNIT-041: RunnerResult.failure Creates Failure

**Input:**
```python
result = RunnerResult.failure(
    error="CLI not found",
    exit_code=127
)
```

**Expected:**
- `success`: False
- `exit_code`: 127
- `error`: "CLI not found"
- `output`: ""

**Assertions:**
```python
assert result.success is False
assert result.exit_code == 127
assert result.error == "CLI not found"
assert result.output == ""
```

---

#### TC-UNIT-042: RunnerResult Infers Total Tokens

**Input:**
```python
result = RunnerResult.success_result(
    output="test",
    token_usage={"input_tokens": 50, "output_tokens": 30}
)
```

**Expected:** `tokens_used` inferred as 80

**Assertions:**
```python
assert result.tokens_used == 80
assert result.token_usage["input_tokens"] == 50
assert result.token_usage["output_tokens"] == 30
```

---

## Parameterized Cases

### File Change Detection

| Before State | After State | Expected Changed | Expected Added |
|--------------|-------------|------------------|----------------|
| `{"a.txt": (mtime1, size1)}` | `{"a.txt": (mtime2, size2)}` | `["a.txt"]` | `[]` |
| `{"a.txt": ...}` | `{"a.txt": ..., "b.txt": ...}` | `[]` | `["b.txt"]` |
| `{}` | `{"a.txt": ...}` | `[]` | `["a.txt"]` |
| `{"a.txt": ...}` | `{}` | `[]` | `[]` (deletion not tracked) |

### JSON Extraction

| Input | Expected Output |
|-------|----------------|
| `'{"a":1}'` | `{"a": 1}` |
| `'```json\n{"a":1}\n```'` | `{"a": 1}` |
| `'text {"a":1} text'` | `{"a": 1}` or `None` (depends on strictness) |
| `'not json'` | `None` |

## Mocks Required

- `subprocess.run` - For testing command execution without actual CLI calls
- `Path.exists` / `Path.read_text` - For filesystem operations
- `os.environ` - For environment variable testing

## Test Organization

**Files:**
- `tests/unit/runners/test_file_tracking.py`
- `tests/unit/runners/test_skill_loading.py`
- `tests/unit/runners/test_json_parsing.py`
- `tests/unit/runners/test_command_building.py`
- `tests/unit/runners/test_runner_result.py`

**Markers:**
- `@pytest.mark.unit`
- `@pytest.mark.fast`

## Related

- **Stories:** [US-001](../../user-stories/US-001-validate-codex-runner.md), [US-002](../../user-stories/US-002-fix-gemini-runner.md)
- **Files:** `saha/runners/codex.py`, `saha/runners/gemini.py`, `saha/runners/base.py`
