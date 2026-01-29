# Claude Code Plugin System Reference

This document captures what we know about building plugins for Claude Code.

---

## Plugin Architecture Overview

Claude Code plugins consist of several components:

| Component | Location | Purpose |
|-----------|----------|---------|
| Plugin Manifest | `.claude-plugin/plugin.json` | Plugin metadata and configuration |
| Commands | `commands/*.md` | Slash commands (e.g., `/mycommand`) |
| Agents | `agents/*.md` | Subagent definitions |
| Skills | `skills/*/SKILL.md` | Knowledge modules and context |
| Hooks | `hooks.json` | Event handlers |

---

## 1. Plugin Manifest

**Location:** `.claude-plugin/plugin.json`

```json
{
  "name": "my-plugin",
  "version": "0.1.0",
  "description": "Description of what the plugin does",
  "author": {
    "name": "Author Name",
    "email": "author@example.com"
  },
  "homepage": "https://github.com/user/repo",
  "license": "MIT",
  "keywords": ["keyword1", "keyword2"]
}
```

---

## 2. Commands (Slash Commands)

**Location:** `commands/<command-name>.md`

Commands are markdown files with YAML frontmatter that define slash commands.

### Structure

```markdown
---
description: Brief description shown in command list
argument-hint: [optional-args]
allowed-tools: Read, Write, Bash, Glob, Grep, Task
---

[Prompt instructions for Claude when this command is invoked]

The command can reference:
- Arguments via $ARGUMENTS or $1, $2, etc.
- Plugin files via `.claude/` relative path (e.g., `.claude/scripts/`, `.claude/agents/`)
- Dynamic content via !`command` syntax
```

### Frontmatter Options

| Field | Required | Description |
|-------|----------|-------------|
| `description` | Yes | Short description shown in `/help` |
| `argument-hint` | No | Hint for expected arguments (e.g., `[--flag] <file>`) |
| `allowed-tools` | No | Tools the command can use |

### Example: `/myproject:init`

```markdown
---
description: Initialize a new project structure
argument-hint: [project-name]
allowed-tools: Read, Write, Bash(mkdir:*), Glob
---

Initialize a new project with the given name.

**Arguments:**
- `$1`: Project name (required)

**Process:**
1. Create project directory structure
2. Generate initial configuration files
3. Report success

Project name: $ARGUMENTS
```

### Dynamic Content

Commands can execute shell commands inline:

```markdown
Current git branch: !`git branch --show-current`
Files in src: !`ls src/`
```

### Namespaced Commands

Commands can be namespaced using colons:
- `commands/init.md` → `/init`
- `commands/myproject:init.md` → `/myproject:init`

Or via folder structure:
- `commands/myproject/init.md` → `/myproject:init`

---

## 3. Agents (Subagents)

**Location:** `agents/<agent-name>.md`

Agents are specialized subagents that can be invoked via the Task tool.

### Structure

```markdown
---
name: agent-name
description: |
  When to use this agent. Include examples:

  <example>
  Context: Description of the situation
  user: "User's message"
  assistant: "How assistant should respond"
  <commentary>Why this agent is appropriate</commentary>
  </example>

model: inherit | sonnet | opus | haiku
color: cyan | green | yellow | etc.
tools: ["Read", "Write", "Glob", "Grep", "Bash(git:*)"]
---

[System prompt for the agent]

Describe:
- Agent's responsibilities
- How it should behave
- Output format expectations
```

### Frontmatter Options

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Agent identifier |
| `description` | Yes | When to use (with examples) |
| `model` | No | Model to use (`inherit`, `sonnet`, `opus`, `haiku`) |
| `color` | No | Terminal color for agent output |
| `tools` | No | List of allowed tools |

### Tool Restrictions

Tools can have pattern restrictions:
- `Bash(git:*, npm:*)` - Only git and npm commands
- `Bash(python:*)` - Only python commands
- `Read` - Full read access
- `Write` - Full write access

### Example: Explore Agent

```markdown
---
name: codebase-explorer
description: |
  Use when user asks to "explore the codebase", "find patterns",
  or "understand the architecture".

  <example>
  user: "How is authentication implemented?"
  assistant: "I'll use the explorer agent to analyze auth patterns."
  </example>

model: inherit
tools: ["Read", "Glob", "Grep"]
---

You are a codebase exploration specialist.

**Responsibilities:**
1. Analyze project structure
2. Identify patterns and conventions
3. Find relevant code examples

**Output:** Provide structured findings with file references.
```

---

## 4. Skills (Knowledge Modules)

**Location:** `skills/<skill-name>/SKILL.md`

Skills provide context and knowledge that Claude can reference.

### Structure

```markdown
---
name: Skill Name
description: When this skill should be activated
version: 0.1.0
---

# Skill Name

[Knowledge content that Claude should be aware of]

## When to Use
- Trigger conditions
- Related commands

## Key Information
- Domain knowledge
- Conventions
- Best practices
```

### Example: Planning Context Skill

```markdown
---
name: Planning Context
description: Activated when user asks about planning progress or runs planning commands
version: 0.1.0
---

# Planning Context

This skill provides awareness of the current planning state.

## State Location
- State file: `.sahaidachny/state.yaml`
- Task folder: `docs/tasks/task-XX/`

## Planning Steps
1. research
2. task_description
3. stories
4. verify
5. design_decisions
...
```

---

## 5. Hooks (Event Handlers)

**Location:** `hooks.json` or specified in config

Hooks execute shell commands in response to events.

### Structure

```json
{
  "hooks": {
    "pre-tool-use": [
      {
        "tool": "Write",
        "pattern": "*.py",
        "command": "python -m py_compile $FILE"
      }
    ],
    "post-tool-use": [
      {
        "tool": "Edit",
        "command": "prettier --write $FILE"
      }
    ],
    "user-prompt-submit": [
      {
        "command": "echo 'User submitted prompt'"
      }
    ]
  }
}
```

### Hook Events

| Event | Trigger |
|-------|---------|
| `pre-tool-use` | Before a tool is executed |
| `post-tool-use` | After a tool completes |
| `user-prompt-submit` | When user submits a prompt |

### Hook Variables

- `$FILE` - File path being operated on
- `$TOOL` - Tool being used
- `$CONTENT` - Content being written (for Write/Edit)

---

## 6. Templates

Templates can be stored in the plugin and referenced by commands.

**Location:** `templates/*.j2` or `templates/*.md`

Commands can reference templates:
```markdown
Use template from: @.claude/templates/user-story.md.j2
```

---

## 7. Plugin Discovery

Claude Code discovers plugins in:
1. Current project directory (`.claude-plugin/`)
2. User's global plugins directory
3. Installed plugins via package manager

---

## 8. Best Practices

### Commands
- Keep descriptions concise (shown in `/help`)
- Use `argument-hint` to document expected args
- Restrict `allowed-tools` to minimum needed
- Use namespacing for related commands

### Agents
- Provide clear examples in description
- Specify appropriate model for complexity
- Limit tools to what agent needs
- Define clear output format

### Skills
- Activate based on user intent
- Provide actionable context
- Keep content focused and scannable

---

## References

- [Claude Code Documentation](https://docs.anthropic.com/claude-code)
- [Claude Code Hooks](https://docs.anthropic.com/claude-code/hooks)
- [MCP (Model Context Protocol)](https://modelcontextprotocol.io)

---

**Last Updated:** 2026-01-19
