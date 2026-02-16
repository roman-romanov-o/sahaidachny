"""Shared utilities for CLI-based runners (Codex, Gemini).

Provides common functionality that non-native runners need:
- File change tracking via filesystem snapshots
- JSON extraction from mixed text/markdown output
- Skill loading and embedding for prompt injection
- Agent spec parsing (frontmatter splitting)
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class FileChangeTracker:
    """Track file changes under a root directory using filesystem snapshots.

    Takes a snapshot at construction time, then compares against a new snapshot
    when diff() is called to detect modified and added files.
    """

    _SKIP_DIRS: set[str] = {
        ".git",
        ".sahaidachny",
        ".venv",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        "node_modules",
        ".codex",
        ".claude",
    }

    _SKIP_FILES: set[str] = {".DS_Store"}

    def __init__(self, root: Path) -> None:
        self._root = root
        self._snapshot = self._take_snapshot()

    def diff(self) -> tuple[list[str], list[str]]:
        """Return (files_changed, files_added) relative to the root."""
        new_snapshot = self._take_snapshot()
        if not new_snapshot:
            return [], []

        if not self._snapshot:
            return [], sorted(new_snapshot.keys())

        files_added = [p for p in new_snapshot if p not in self._snapshot]
        files_changed = [
            p
            for p, meta in new_snapshot.items()
            if p in self._snapshot and meta != self._snapshot[p]
        ]

        return sorted(files_changed), sorted(files_added)

    def _take_snapshot(self) -> dict[str, tuple[int, int]]:
        """Snapshot files under the root with (mtime_ns, size)."""
        if not self._root.exists():
            return {}

        snapshot: dict[str, tuple[int, int]] = {}
        for dirpath, dirnames, filenames in os.walk(self._root):
            dirnames[:] = [d for d in dirnames if d not in self._SKIP_DIRS]
            for filename in filenames:
                if filename in self._SKIP_FILES:
                    continue
                path = Path(dirpath) / filename
                try:
                    if not path.is_file():
                        continue
                    stat = path.stat()
                except OSError:
                    continue
                rel_path = path.relative_to(self._root).as_posix()
                snapshot[rel_path] = (stat.st_mtime_ns, stat.st_size)

        return snapshot


def _parse_json_from_markdown(output: str) -> dict[str, Any] | None:
    """Extract JSON from markdown code blocks (```json ... ```).

    Returns the first valid JSON dict found, or None.
    """
    pattern = r"```json\s*\n(.*?)\n```"
    for match in re.findall(pattern, output, re.DOTALL):
        try:
            parsed = json.loads(match.strip())
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _collect_json_blocks(lines: list[str]) -> list[list[str]]:
    """Collect brace-balanced JSON blocks from lines of text."""
    blocks: list[list[str]] = []
    current: list[str] = []
    depth = 0

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("{") and depth == 0:
            depth = stripped.count("{") - stripped.count("}")
            current = [line]
            if depth == 0:
                blocks.append(current)
                current = []
        elif depth > 0:
            current.append(line)
            depth += stripped.count("{") - stripped.count("}")
            if depth <= 0:
                blocks.append(current)
                current = []
                depth = 0

    return blocks


def _parse_json_by_braces(output: str) -> dict[str, Any] | None:
    """Extract JSON by matching balanced braces in raw text.

    Returns the first valid JSON dict found, or None.
    """
    blocks = _collect_json_blocks(output.strip().split("\n"))

    for block in blocks:
        try:
            parsed = json.loads("\n".join(block))
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def try_parse_json(output: str) -> dict[str, Any] | None:
    """Extract and parse JSON from mixed text/markdown output.

    Handles:
    - JSON inside markdown code blocks (```json ... ```)
    - Standalone JSON objects in text
    - Multiple JSON blocks (returns the first valid dict)
    - Nested JSON objects with balanced braces

    Args:
        output: Raw text output that may contain JSON.

    Returns:
        Parsed JSON dict, or None if no valid JSON found.
    """
    if not output or not output.strip():
        return None

    return _parse_json_from_markdown(output) or _parse_json_by_braces(output)


def split_frontmatter(content: str) -> tuple[str, str]:
    """Split YAML frontmatter from markdown content.

    Args:
        content: Full markdown content potentially with frontmatter.

    Returns:
        Tuple of (frontmatter_text, body_text). Frontmatter is empty string
        if not present.
    """
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[1], parts[2]
    return "", content


def extract_system_prompt(agent_spec_path: Path) -> str | None:
    """Extract system prompt from agent spec markdown file.

    Reads the file, strips YAML frontmatter, and returns the body as system prompt.

    Args:
        agent_spec_path: Path to agent spec file.

    Returns:
        System prompt text, or None if file doesn't exist.
    """
    if not agent_spec_path.exists():
        return None

    content = agent_spec_path.read_text()
    _, body = split_frontmatter(content)
    return body.strip() if body else None


def _parse_inline_skills(line: str) -> list[str]:
    """Parse comma-separated skill names from a 'skills: a, b' line."""
    value = line.split(":", 1)[1].strip()
    if not value:
        return []
    return [s.strip() for s in value.split(",") if s.strip()]


def _parse_yaml_list_skills(lines: list[str], start_idx: int) -> tuple[list[str], int]:
    """Parse YAML list items following a bare 'skills:' key.

    Args:
        lines: All frontmatter lines.
        start_idx: Index of the first line after the 'skills:' key.

    Returns:
        Tuple of (skill names, next index to resume parsing).
    """
    skills: list[str] = []
    i = start_idx
    while i < len(lines):
        item = lines[i].strip()
        if not item:
            i += 1
            continue
        if item.startswith("-"):
            skill = item[1:].strip()
            if skill:
                skills.append(skill)
            i += 1
            continue
        # Hit a new YAML key or non-list line
        break
    return skills, i


def parse_skill_names(frontmatter: str) -> list[str]:
    """Parse skill names from YAML frontmatter text.

    Supports both inline format (skills: ruff, ty) and YAML list format.

    Args:
        frontmatter: YAML frontmatter content (without --- delimiters).

    Returns:
        List of skill names.
    """
    if not frontmatter:
        return []

    skills: list[str] = []
    lines = frontmatter.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("#") or not line.startswith("skills:"):
            i += 1
            continue

        inline = _parse_inline_skills(line)
        if inline:
            skills.extend(inline)
            i += 1
            continue

        yaml_skills, i = _parse_yaml_list_skills(lines, i + 1)
        skills.extend(yaml_skills)

    return skills


def find_skill_text(
    skill_name: str,
    candidate_dirs: list[Path],
) -> str | None:
    """Load skill markdown body by searching candidate directories.

    Args:
        skill_name: Name of the skill to find.
        candidate_dirs: List of directories to search for skill files.

    Returns:
        Skill body text (without frontmatter), or None if not found.
    """
    for base_dir in candidate_dirs:
        skill_path = base_dir / skill_name / "SKILL.md"
        if not skill_path.exists():
            continue
        try:
            content = skill_path.read_text()
        except OSError:
            continue
        _, body = split_frontmatter(content)
        return body.strip()
    return None


def build_skills_prompt(
    agent_spec_path: Path,
    working_dir: Path,
) -> str | None:
    """Extract and render referenced skills from an agent spec.

    Args:
        agent_spec_path: Path to agent spec markdown file.
        working_dir: Project working directory.

    Returns:
        Formatted skills markdown, or None if no skills found.
    """
    if not agent_spec_path.exists():
        return None

    content = agent_spec_path.read_text()
    frontmatter, _ = split_frontmatter(content)
    skill_names = parse_skill_names(frontmatter)
    if not skill_names:
        return None

    candidate_dirs = _candidate_skills_dirs(agent_spec_path, working_dir)
    rendered_skills: list[str] = []

    for skill_name in skill_names:
        skill_text = find_skill_text(skill_name, candidate_dirs)
        if not skill_text:
            logger.debug("Skill not found: %s", skill_name)
            continue
        rendered_skills.append(f"## Skill: {skill_name}\n\n{skill_text}")

    if not rendered_skills:
        return None

    return "\n\n".join(rendered_skills)


def build_prompt_with_context(
    prompt: str,
    context: dict[str, Any] | None,
    system_prompt: str | None = None,
    skills_prompt: str | None = None,
) -> str:
    """Build a full prompt with optional system prompt, skills, and context.

    Args:
        prompt: The user prompt.
        context: Optional context dict to include as JSON.
        system_prompt: Optional system instructions.
        skills_prompt: Optional rendered skills markdown.

    Returns:
        Full prompt string ready for CLI input.
    """
    parts: list[str] = []

    prelude_parts: list[str] = []
    if system_prompt:
        prelude_parts.append(system_prompt.strip())
    if skills_prompt:
        prelude_parts.append(skills_prompt.strip())

    if prelude_parts:
        parts.extend(
            [
                "\n\n".join(prelude_parts),
                "",
                "---",
                "",
            ]
        )

    parts.append(prompt)

    if context:
        parts.extend(
            [
                "",
                "## Context",
                "",
                "```json",
                json.dumps(context, indent=2, default=str),
                "```",
            ]
        )

    return "\n".join(parts)


def _candidate_skills_dirs(agent_spec_path: Path, working_dir: Path) -> list[Path]:
    """Return candidate skills directories to search.

    Args:
        agent_spec_path: Path to agent spec file.
        working_dir: Project working directory.

    Returns:
        List of directories that may contain skills.
    """
    candidates: list[Path] = []
    agent_dir = agent_spec_path.parent
    if agent_dir.name == "agents":
        candidates.append(agent_dir.parent / "skills")
    candidates.append(working_dir / "claude_plugin" / "skills")
    return candidates
