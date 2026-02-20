# Multi-CLI Artifacts Proposal

## Problem Statement

Currently, agents and skills are in `claude_plugin/` which:
- Misleadingly suggests they're Claude-only
- Makes it unclear to Gemini/Codex users they can use these
- Doesn't provide CLI-specific entry points

**Reality:** The infrastructure already supports all CLIs via `_utils.py`, we just need better organization.

## Current Structure

```
claude_plugin/
  agents/              # Already works for Gemini, Codex, Claude
    execution-implementer.md
    execution-qa.md
    execution-test-critique.md
    ...
  skills/              # Already works for all CLIs
    ruff/
    test-critique/
    complexity/
    ...
  commands/            # Claude Code specific (slash commands)
    plan.md
    stories.md
    ...
```

## Proposed Structure

### Option A: Rename (Minimal Change)

```
saha/
  artifacts/           # Renamed from claude_plugin
    agents/            # Works for ALL CLIs
    skills/            # Works for ALL CLIs
    commands/          # Claude Code specific
  cli/
    README.md          # Documents CLI-specific usage
```

**Changes needed:**
- Rename directory
- Update imports
- Update documentation

### Option B: Full Restructure (Better Long-term)

```
saha/
  artifacts/
    agents/            # Shared agents (ALL CLIs)
      planning/        # Planning agents
        research.md
        plan.md (agent version)
        stories.md (agent version)
      execution/       # Execution loop agents
        execution-implementer.md
        execution-qa.md
        execution-test-critique.md
        execution-code-quality.md
        execution-dod.md
        execution-manager.md
    skills/            # Shared skills (ALL CLIs)
      ruff/
      test-critique/
      complexity/
      task-structure/

  cli/
    claude/
      commands/        # Claude Code slash commands
        plan.md        # Invokes planning agent
        stories.md     # Invokes stories agent
        research.md    # Invokes research agent
      config.json      # Claude-specific settings

    gemini/
      config.json      # Gemini-specific settings
      aliases.sh       # Shell aliases for common commands

    codex/
      config.json      # Codex-specific settings
      aliases.sh       # Shell aliases for common commands
```

**Benefits:**
- Clear separation: shared vs CLI-specific
- Easy to add CLI-specific tools
- Planning agents accessible to all CLIs
- Better discoverability

## How Each CLI Uses Artifacts

### Claude Code (Native Support)

**Agents:**
```bash
# .claude/agents/ contains symlinks or copies
claude --agent execution-qa ...
```

**Skills:**
```markdown
---
skills: test-critique, ruff
---
```

**Commands:**
```bash
/saha:plan
/saha:stories
/saha:research
```

### Gemini CLI (Embedded Prompts)

**Agents:**
```python
# saha/runners/gemini.py
system_prompt = extract_system_prompt(agent_spec_path)
skills_prompt = build_skills_prompt(agent_spec_path, working_dir)
full_prompt = build_prompt_with_context(prompt, context, system_prompt, skills_prompt)
```

**Usage:**
```bash
# Planning
gemini --prompt "$(saha gemini-prompt plan --task task-01)"

# Execution agent
saha run task-01 --runner gemini  # Uses execution agents
```

### Codex CLI (Embedded Prompts)

**Agents:**
```python
# saha/runners/codex.py - same as Gemini
system_prompt = extract_system_prompt(agent_spec_path)
skills_prompt = build_skills_prompt(agent_spec_path, working_dir)
```

**Usage:**
```bash
# Planning
codex "$(saha codex-prompt plan --task task-01)"

# Execution agent
saha run task-01 --runner codex  # Uses execution agents
```

## Implementation Plan

### Phase 1: Planning Agents for All CLIs (Quick Win)

**Goal:** Make planning agents (research, plan, stories) available to Gemini/Codex

1. **Convert commands to agents**
   ```
   saha/artifacts/agents/planning/
     research.md       # Agent spec (extracted from commands/research.md)
     plan.md           # Agent spec (extracted from commands/plan.md)
     stories.md        # Agent spec (extracted from commands/stories.md)
     test-specs.md
     decide.md
     contracts.md
   ```

2. **Create CLI helpers**
   ```python
   # saha/cli/helpers.py
   def run_planning_agent(
       agent_name: str,
       runner: Runner,
       task_path: str | None = None
   ) -> RunnerResult:
       """Run a planning agent with any CLI runner."""
       agent_path = ARTIFACTS_DIR / "agents" / "planning" / f"{agent_name}.md"
       prompt = build_planning_prompt(agent_name, task_path)
       return runner.run_agent(agent_path, prompt)
   ```

3. **Add CLI commands**
   ```bash
   # Works with any runner
   saha research --runner gemini
   saha plan --runner codex
   saha stories --runner claude
   ```

### Phase 2: Execution Loop for All CLIs

**Already works!** Just document it:

```bash
# Run execution loop with Gemini
saha run task-01 --runner gemini

# Run execution loop with Codex
saha run task-01 --runner codex

# All execution agents work: implementer, qa, test-critique, etc.
```

### Phase 3: Full Restructure

- Move `claude_plugin/` → `saha/artifacts/`
- Split agents into `planning/` and `execution/`
- Create `saha/cli/{claude,gemini,codex}/`
- Update all documentation

## Example: Planning with Gemini

**Before (doesn't work):**
```bash
gemini "help me plan task-01"  # Generic, no structure
```

**After (structured planning):**
```bash
# Research phase
saha research --runner gemini --task task-01

# Generate user stories
saha stories --runner gemini --task task-01

# Create implementation plan
saha plan --runner gemini --task task-01

# All artifacts saved to docs/tasks/task-01/
```

**How it works:**
1. `saha research` finds agent spec: `saha/artifacts/agents/planning/research.md`
2. Extracts system prompt (instructions for research)
3. Loads skills: `task-structure`
4. Builds prompt with task context
5. Passes to Gemini CLI
6. Parses output and saves artifacts

## Example: Execution Loop with Codex

**Already works:**
```bash
saha run task-01 --runner codex --max-iterations 5
```

**What happens:**
1. Loop runs `execution-implementer` agent via Codex
2. Codex receives embedded system prompt from agent spec
3. Writes code following TDD approach
4. Loop runs `execution-test-critique` agent via Codex
5. Codex analyzes test quality across 5 dimensions
6. Loop runs `execution-qa` agent via Codex
7. Codex verifies DoD criteria
8. Continues until DoD achieved or max iterations

**All agents already work!** We just need to document it better.

## Benefits Summary

### For Users
- ✅ Use ANY CLI for planning and execution
- ✅ Choose best model for each phase (GPT-4 for planning, Claude for execution)
- ✅ Cost optimization (use cheaper models where appropriate)
- ✅ Redundancy (if one provider is down, use another)

### For Maintainers
- ✅ Single source of truth for agents and skills
- ✅ Test once, works everywhere
- ✅ Easy to add new CLIs
- ✅ Clear separation of concerns

## Migration Path

### Immediate (No Breaking Changes)
1. Add `saha research/plan/stories --runner {claude|gemini|codex}` commands
2. Document that execution loop works with all runners
3. Keep `claude_plugin/` for backward compatibility

### Short-term (Minor Version Bump)
1. Rename `claude_plugin/` → `saha/artifacts/`
2. Add deprecation warning for old import paths
3. Update documentation

### Long-term (Major Version)
1. Full restructure as in Option B
2. Remove deprecated paths
3. CLI-specific optimizations

## Next Steps

1. **Validate approach** - Get feedback on structure
2. **Create planning agents** - Extract from commands
3. **Add CLI helpers** - `run_planning_agent()` utility
4. **Test with Gemini/Codex** - Verify everything works
5. **Document** - Usage examples for each CLI
6. **Announce** - Let users know they can use any CLI

## Questions to Resolve

1. Should we keep `/saha:plan` style commands for Claude Code only?
   - **Proposal:** Yes, as convenience wrappers

2. Should planning agents be separate from execution agents?
   - **Proposal:** Yes, different concerns and workflows

3. How to handle CLI-specific optimizations (model selection, timeouts)?
   - **Proposal:** CLI-specific config files in `saha/cli/{name}/`

4. Should we support mixing CLIs in one execution? (e.g., Gemini for planning, Claude for execution)
   - **Proposal:** Yes, that's already supported, just document it
