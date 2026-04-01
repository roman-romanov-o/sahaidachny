# Multi-CLI Planning Example

This example shows how to use Sahaidachny planning agents with **any CLI** (Claude Code, Gemini CLI, or Codex CLI).

## The Magic: It Already Works!

The infrastructure exists - we just need to expose it through commands.

## Current State (Execution Loop Only)

**This already works:**
```bash
# Run execution loop with Gemini
saha run task-01 --runner gemini

# Run execution loop with Codex
saha run task-01 --runner codex
```

**How?** The `saha/runners/gemini.py` and `saha/runners/codex.py` use:
```python
system_prompt = extract_system_prompt(agent_spec_path)  # Extract agent instructions
skills_prompt = build_skills_prompt(agent_spec_path, ...)  # Load skills
full_prompt = build_prompt_with_context(prompt, context, system_prompt, skills_prompt)
# Pass to CLI
```

## Proposed: Planning with Any CLI

### Example 1: Research Phase with Gemini

```bash
$ saha research --runner gemini --task task-01-auth
```

**What happens:**
1. Loads agent spec: `saha/artifacts/agents/planning/research.md`
2. Extracts system prompt (research instructions)
3. Loads `task-structure` skill
4. Builds prompt:
   ```
   [System Prompt from research.md]

   ## Skill: task-structure
   [Skill content]

   ---

   Research the codebase for task: task-01-auth

   ## Context
   ```json
   {
     "task_path": "docs/tasks/task-01-auth",
     "task_description": "Add JWT authentication..."
   }
   ```
   ```
5. Sends to Gemini CLI
6. Parses markdown output
7. Saves research reports to `docs/tasks/task-01-auth/research/`

### Example 2: Generate User Stories with Codex

```bash
$ saha stories --runner codex --task task-01-auth
```

**Same flow as above but:**
- Uses `agents/planning/stories.md` agent spec
- Sends to Codex CLI
- Saves user stories to `docs/tasks/task-01-auth/user-stories/`

### Example 3: Implementation Plan with Claude

```bash
$ saha plan --runner claude --task task-01-auth
```

**For Claude Code:**
- Can use native slash command: `/saha:plan`
- Or use the same flow as Gemini/Codex

## Full Planning Flow with Gemini

```bash
#!/bin/bash
# Complete planning with Gemini CLI

TASK="task-01-auth"

echo "=== Phase 1: Research ==="
saha research --runner gemini --task $TASK

echo "=== Phase 2: User Stories ==="
saha stories --runner gemini --task $TASK

echo "=== Phase 3: Design Decisions ==="
saha decide --runner gemini --task $TASK

echo "=== Phase 4: Code Changes ==="
saha contracts --runner gemini --task $TASK

echo "=== Phase 5: Test Specs ==="
saha test-specs --runner gemini --task $TASK

echo "=== Phase 6: Implementation Plan ==="
saha plan --runner gemini --task $TASK

echo "=== Verification ==="
saha verify --task $TASK

echo "=== Ready for execution! ==="
saha run $TASK --runner claude  # Switch to Claude for execution
```

## Mixed CLI Workflow (Best of Both Worlds)

```bash
# Use GPT-4 (via Codex) for planning (cheaper, good at analysis)
saha research --runner codex --task task-02
saha stories --runner codex --task task-02

# Use Gemini Flash for test specs (fast, good at test generation)
saha test-specs --runner gemini --task task-02

# Use Claude for execution (best at code generation)
saha run task-02 --runner claude
```

## Implementation Sketch

Here's how simple the implementation would be:

```python
# saha/commands/planning.py

import typer
from pathlib import Path
from saha.runners import get_runner
from saha.artifacts import AGENTS_DIR

app = typer.Typer()

def run_planning_agent(
    agent_name: str,
    runner_name: str,
    task_path: str | None = None,
    timeout: int = 300,
) -> None:
    """Run a planning agent with specified CLI runner."""

    # Get runner
    runner = get_runner(runner_name)

    # Find agent spec
    agent_spec = AGENTS_DIR / "planning" / f"{agent_name}.md"
    if not agent_spec.exists():
        print(f"Agent not found: {agent_name}")
        return

    # Determine task path
    if task_path is None:
        task_path = auto_detect_task()

    # Build prompt
    prompt = f"Execute {agent_name} planning phase for task: {task_path}"

    # Run agent
    context = {
        "task_path": task_path,
        "agent_name": agent_name,
    }

    result = runner.run_agent(agent_spec, prompt, context, timeout)

    if result.success:
        print(f"✓ {agent_name} completed successfully")
        print(f"Output: {result.output[:200]}...")
    else:
        print(f"✗ {agent_name} failed: {result.error}")

@app.command()
def research(
    task: str = typer.Option(None, "--task", "-t", help="Task ID or path"),
    runner: str = typer.Option("claude", "--runner", "-r", help="CLI runner to use"),
    timeout: int = typer.Option(300, "--timeout", help="Timeout in seconds"),
) -> None:
    """Research codebase for task."""
    run_planning_agent("research", runner, task, timeout)

@app.command()
def stories(
    task: str = typer.Option(None, "--task", "-t"),
    runner: str = typer.Option("claude", "--runner", "-r"),
    timeout: int = typer.Option(300, "--timeout"),
) -> None:
    """Generate user stories from task description."""
    run_planning_agent("stories", runner, task, timeout)

@app.command()
def plan(
    task: str = typer.Option(None, "--task", "-t"),
    runner: str = typer.Option("claude", "--runner", "-r"),
    timeout: int = typer.Option(300, "--timeout"),
) -> None:
    """Generate phased implementation plan."""
    run_planning_agent("plan", runner, task, timeout)

# ... more commands for decide, contracts, test-specs, etc.
```

## What Changes Are Needed

### 1. Extract Agent Specs from Commands

**Current:** `claude_plugin/commands/research.md` (Claude-specific slash command)
**New:** `saha/artifacts/agents/planning/research.md` (Universal agent spec)

The content is already perfect - just move it and ensure frontmatter is correct:

```markdown
---
name: research
description: Research codebase and validate assumptions
skills: task-structure
allowed-tools: Read, Glob, Grep, Task
---

# Codebase Research

[Rest of the content stays exactly the same]
```

### 2. Add Runner Commands

Add `saha research`, `saha plan`, etc. commands that accept `--runner` flag.

**Implementation:** ~100 lines of code in `saha/commands/planning.py`

### 3. Update Documentation

Document that planning works with all CLIs.

### 4. Keep Claude Commands

Keep `/saha:research`, `/saha:plan` slash commands in `claude_plugin/commands/` for Claude Code users who prefer native commands.

They can invoke the same underlying agents.

## Benefits

### Cost Optimization
```bash
# Use cheap Gemini Flash for research ($0.075/1M input tokens)
saha research --runner gemini --task task-01

# Use Claude Opus for execution ($15/1M input tokens)
saha run task-01 --runner claude
```

**Savings:** 200x cheaper for planning phase!

### Model Selection
```bash
# GPT-4 is great at planning
saha plan --runner codex --model gpt-4

# Claude is great at code
saha run task-01 --runner claude --model opus
```

### Redundancy
```bash
# Anthropic API down? Use Gemini
saha run task-01 --runner gemini

# Google API down? Use OpenAI
saha run task-01 --runner codex
```

### Flexibility
```bash
# Try different models for same task
saha research --runner gemini > gemini-research.md
saha research --runner codex > codex-research.md
saha research --runner claude > claude-research.md

# Compare outputs and pick best
```

## Timeline

### Week 1: Proof of Concept
- ✅ Extract one agent (research.md) to `saha/artifacts/agents/planning/`
- ✅ Implement `saha research --runner {claude|gemini|codex}`
- ✅ Test with all three CLIs
- ✅ Document approach

### Week 2: Core Planning Agents
- Extract all planning agents: stories, plan, decide, contracts, test-specs
- Implement all `saha <command> --runner <cli>` commands
- Integration tests for each CLI

### Week 3: Polish & Documentation
- Update user guide
- Add examples
- Video tutorials
- Migration guide for existing users

### Week 4: Full Restructure (Optional)
- Rename `claude_plugin/` → `saha/artifacts/`
- Split into `planning/` and `execution/` agents
- CLI-specific configs

## Questions?

1. **Will this break existing Claude Code workflows?**
   - No! `/saha:plan` slash commands still work
   - They just invoke the same underlying agents

2. **Do I need all three CLIs installed?**
   - No, only the one(s) you want to use
   - Sahaidachny detects what's available

3. **Can I mix CLIs in one workflow?**
   - Yes! That's the whole point
   - Use the best tool for each job

4. **What if an agent doesn't work well with a specific CLI?**
   - We can add CLI-specific variants if needed
   - Or configure different prompts per CLI

5. **Performance differences?**
   - Gemini: Fastest, cheapest (Flash model)
   - Claude: Best quality for code
   - GPT-4: Best for analysis and planning
