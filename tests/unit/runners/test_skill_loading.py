"""Unit tests for skill loading utilities.

Tests: TC-UNIT-010 through TC-UNIT-012
Covers: Skill discovery, missing directory handling, skill embedding.
"""

from pathlib import Path

from saha.runners._utils import (
    build_skills_prompt,
    find_skill_text,
    parse_skill_names,
)


class TestParseSkillNames:
    """Tests for YAML frontmatter skill parsing."""

    def test_parses_inline_skills(self) -> None:
        """Parse comma-separated skills from frontmatter."""
        frontmatter = "name: test\nskills: ruff, ty\n"
        skills = parse_skill_names(frontmatter)
        assert skills == ["ruff", "ty"]

    def test_parses_yaml_list_skills(self) -> None:
        """Parse YAML list format skills."""
        frontmatter = "name: test\nskills:\n  - ruff\n  - ty\n"
        skills = parse_skill_names(frontmatter)
        assert skills == ["ruff", "ty"]

    def test_returns_empty_for_no_skills(self) -> None:
        """Return empty list when no skills key in frontmatter."""
        frontmatter = "name: test\nversion: 1\n"
        skills = parse_skill_names(frontmatter)
        assert skills == []

    def test_returns_empty_for_empty_input(self) -> None:
        """Return empty list for empty frontmatter."""
        assert parse_skill_names("") == []


class TestFindSkillText:
    """Tests for skill file lookup."""

    def test_finds_skill_in_directory(self, tmp_path: Path) -> None:
        """TC-UNIT-010: Find skill files in candidate directories."""
        skills_dir = tmp_path / "skills"
        (skills_dir / "ruff").mkdir(parents=True)
        (skills_dir / "ruff" / "SKILL.md").write_text(
            "---\nname: ruff\n---\n\n# Ruff Skill\nLinting tool"
        )

        result = find_skill_text("ruff", [skills_dir])
        assert result is not None
        assert "Ruff Skill" in result
        assert "Linting tool" in result

    def test_returns_none_for_missing_skill(self, tmp_path: Path) -> None:
        """Return None when skill not found in any candidate."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        result = find_skill_text("nonexistent", [skills_dir])
        assert result is None

    def test_returns_none_for_missing_directory(self) -> None:
        """TC-UNIT-011: Return None for nonexistent directory."""
        result = find_skill_text("ruff", [Path("/nonexistent")])
        assert result is None

    def test_searches_multiple_directories(self, tmp_path: Path) -> None:
        """Search across multiple candidate directories."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        (dir2 / "ty").mkdir(parents=True)
        (dir2 / "ty" / "SKILL.md").write_text("---\nname: ty\n---\n\n# Ty Skill\nType checker")

        result = find_skill_text("ty", [dir1, dir2])
        assert result is not None
        assert "Ty Skill" in result


class TestBuildSkillsPrompt:
    """Tests for full skills prompt building."""

    def test_builds_skills_prompt(self, tmp_path: Path) -> None:
        """TC-UNIT-012: Build formatted skills markdown from agent spec."""
        # Set up skills
        skills_dir = tmp_path / "claude_plugin" / "skills"
        (skills_dir / "ruff").mkdir(parents=True)
        (skills_dir / "ty").mkdir(parents=True)
        (skills_dir / "ruff" / "SKILL.md").write_text("---\nname: ruff\n---\n\n# Ruff\nLinter")
        (skills_dir / "ty" / "SKILL.md").write_text("---\nname: ty\n---\n\n# Ty\nType checker")

        # Set up agent spec
        agents_dir = tmp_path / "claude_plugin" / "agents"
        agents_dir.mkdir(parents=True)
        agent_spec = agents_dir / "test-agent.md"
        agent_spec.write_text("---\nname: test-agent\nskills: ruff, ty\n---\n\n# Agent\nBody.\n")

        result = build_skills_prompt(agent_spec, tmp_path)
        assert result is not None
        assert "## Skill: ruff" in result
        assert "## Skill: ty" in result
        assert "Linter" in result
        assert "Type checker" in result

    def test_returns_none_for_no_skills(self, tmp_path: Path) -> None:
        """Return None when agent spec has no skills."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir(parents=True)
        agent_spec = agents_dir / "test-agent.md"
        agent_spec.write_text("---\nname: test-agent\n---\n\n# Agent\nBody.\n")

        result = build_skills_prompt(agent_spec, tmp_path)
        assert result is None

    def test_returns_none_for_missing_spec(self, tmp_path: Path) -> None:
        """Return None when agent spec doesn't exist."""
        result = build_skills_prompt(tmp_path / "nonexistent.md", tmp_path)
        assert result is None
