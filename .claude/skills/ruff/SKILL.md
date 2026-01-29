---
name: ruff
description: |
  Use this skill for Python linting and formatting with Ruff. Activated when:
  - Running ruff check or ruff format
  - Fixing linting issues
  - Configuring ruff rules
version: 0.1.0
globs:
  - "*.py"
  - "pyproject.toml"
  - "ruff.toml"
---

# Ruff: Python Linting and Formatting

Ruff is an extremely fast Python linter and code formatter. It replaces Flake8, isort, Black, pyupgrade, autoflake, and dozens of other tools.

## When to Use Ruff

- Always use for Python linting and formatting when you see ruff config files
- Don't format unformatted code—if `ruff format --diff` shows changes throughout an entire file, the project likely isn't using ruff for formatting
- Only fix issues in files being actively modified, unless explicitly asked otherwise

## Running Ruff

```bash
# Using uv (recommended in projects)
uv run ruff check .
uv run ruff format .

# One-off usage
uvx ruff check .
uvx ruff format .

# If globally installed
ruff check .
ruff format .
```

## Core Commands

### Linting

```bash
# Check for issues
ruff check .

# Auto-fix safe issues
ruff check --fix .

# Fix including unsafe fixes (preview changes first!)
ruff check --fix --unsafe-fixes .

# Watch mode
ruff check --watch .

# Check specific rules
ruff check --select E,F .

# Ignore specific rules
ruff check --ignore E501 .
```

### Formatting

```bash
# Format files
ruff format .

# Check if files are formatted (CI)
ruff format --check .

# Show what would change
ruff format --diff .
```

## Configuration

Settings in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
ignore = ["E501"]  # Line too long (handled by formatter)

[tool.ruff.lint.isort]
known-first-party = ["myproject"]
```

Or in `ruff.toml`:

```toml
line-length = 88
target-version = "py311"

[lint]
select = ["E", "F", "I"]
```

## Common Rule Categories

| Prefix | Description |
|--------|-------------|
| E | pycodestyle errors |
| W | pycodestyle warnings |
| F | Pyflakes |
| I | isort |
| UP | pyupgrade |
| B | flake8-bugbear |
| SIM | flake8-simplify |
| C4 | flake8-comprehensions |
| PT | flake8-pytest-style |

## Fixing Common Issues

### Import Sorting (I001)

```bash
ruff check --select I --fix .
```

### Unused Imports (F401)

```bash
ruff check --select F401 --fix .
```

### Upgrade Syntax (UP)

```bash
ruff check --select UP --fix .
```

## Best Practices

1. **Run lint before format** - Linting can restructure code that formatting then refines
2. **Preview unsafe fixes** - Always review `--unsafe-fixes` changes before applying
3. **Use per-file ignores** - For test files or generated code:
   ```toml
   [tool.ruff.lint.per-file-ignores]
   "tests/*" = ["S101"]  # Allow assert in tests
   ```

## Integration with Sahaidachny

The agentic loop runs `ruff check` during the Code Quality phase. Linting violations will cause the iteration to fail with fix_info listing the issues to resolve.
