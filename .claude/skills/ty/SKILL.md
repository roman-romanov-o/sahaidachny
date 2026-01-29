---
name: ty
description: |
  Use this skill for Python type checking with ty. Activated when:
  - Running ty check
  - Fixing type errors
  - Adding type annotations
version: 0.1.0
globs:
  - "*.py"
  - "pyproject.toml"
  - "ty.toml"
---

# ty: Python Type Checking

ty is an extremely fast Python type checker and language server. It serves as a modern replacement for mypy and Pyright.

## When to Use ty

- Always use for Python type checking
- Look for `[tool.ty]` in `pyproject.toml` or `ty.toml` config files
- Use when you see type annotations in the codebase

## Running ty

```bash
# Using uv (recommended in projects)
uv run ty check .

# One-off usage
uvx ty check .

# Check specific file
uv run ty check src/main.py

# Check with specific Python version
uv run ty check --python-version 3.11 .
```

## Configuration

In `pyproject.toml`:

```toml
[tool.ty]
python-version = "3.11"

[tool.ty.rules]
# Set rule severities
unresolved-import = "error"
unresolved-attribute = "warning"
invalid-type-form = "error"

[tool.ty.environment]
# Configure virtual environment
python = ".venv/bin/python"
```

Or in `ty.toml`:

```toml
python-version = "3.11"

[rules]
unresolved-import = "error"

[environment]
python = ".venv/bin/python"
```

## Common Type Errors

### Unresolved Import

```python
# Error: Cannot resolve import "nonexistent"
from nonexistent import foo

# Fix: Install the package or check the import path
```

### Type Mismatch

```python
# Error: Expected str, got int
def greet(name: str) -> str:
    return f"Hello, {name}"

greet(42)  # Error!

# Fix: Pass correct type
greet("Alice")
```

### Missing Return Type

```python
# Warning: Missing return type annotation
def add(a: int, b: int):
    return a + b

# Fix: Add return type
def add(a: int, b: int) -> int:
    return a + b
```

### Optional Handling

```python
# Error: "None" has no attribute "strip"
def process(value: str | None) -> str:
    return value.strip()  # Error!

# Fix: Handle None case
def process(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip()
```

## Type Annotation Best Practices

### Use Modern Syntax (Python 3.10+)

```python
# Old style
from typing import List, Dict, Optional, Union

def foo(items: List[str]) -> Optional[Dict[str, int]]:
    ...

# Modern style
def foo(items: list[str]) -> dict[str, int] | None:
    ...
```

### Use Type Aliases for Complex Types

```python
# Define aliases for readability
type UserId = int
type UserMap = dict[UserId, User]

def get_users() -> UserMap:
    ...
```

### Annotate Function Signatures

```python
# Always annotate public functions
def calculate_total(
    items: list[Item],
    discount: float = 0.0,
) -> float:
    ...
```

## Ignoring Errors

When necessary, use targeted ignores:

```python
# ty: ignore[rule-name] - Specific rule
value = some_dynamic_thing  # ty: ignore[unresolved-attribute]

# Avoid blanket ignores
value = thing  # ty: ignore  # Bad - too broad
```

## Migration from mypy

| mypy | ty |
|------|-----|
| `mypy .` | `ty check .` |
| `# type: ignore` | `# ty: ignore` |
| `mypy.ini` | `ty.toml` or `pyproject.toml` |

## Integration with Sahaidachny

The agentic loop runs `ty check` during the Code Quality phase. Type errors will cause the iteration to fail with fix_info listing the type issues to resolve.
