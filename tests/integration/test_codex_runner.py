"""Tests for CodexRunner prompt composition and skill loading."""

from pathlib import Path

from saha.runners._utils import build_prompt_with_context
from saha.runners.claude import ClaudeRunner
from saha.runners.codex import CodexRunner, _FileChangeTracker


def test_agent_skill_references_resolve() -> None:
    """Ensure all skills referenced by agents exist in the plugin skills directory."""
    agents_dir = Path("claude_plugin/agents")
    skills_dir = Path("claude_plugin/skills")

    missing: set[str] = set()

    for agent_path in agents_dir.glob("*.md"):
        text = agent_path.read_text()
        if not text.startswith("---"):
            continue
        parts = text.split("---", 2)
        if len(parts) < 3:
            continue
        frontmatter = parts[1]
        skill_names: list[str] = []
        for line in frontmatter.splitlines():
            stripped = line.strip()
            if stripped.startswith("skills:"):
                value = stripped.split(":", 1)[1].strip()
                if value:
                    skill_names.extend([s.strip() for s in value.split(",") if s.strip()])
                else:
                    continue
            elif stripped.startswith("-"):
                skill_names.append(stripped[1:].strip())

        for skill in skill_names:
            if not (skills_dir / skill / "SKILL.md").exists():
                missing.add(skill)

    assert not missing, f"Missing skill definitions: {sorted(missing)}"


def test_codex_skills_prompt_includes_skill_bodies(tmp_path: Path) -> None:
    """CodexRunner should embed skill bodies referenced in agent frontmatter."""
    agents_dir = tmp_path / "claude_plugin" / "agents"
    skills_dir = tmp_path / "claude_plugin" / "skills"
    agents_dir.mkdir(parents=True)
    (skills_dir / "ruff").mkdir(parents=True)
    (skills_dir / "ty").mkdir(parents=True)

    (skills_dir / "ruff" / "SKILL.md").write_text(
        "---\nname: ruff\n---\n\n# Ruff Skill\n\nRuff details.\n"
    )
    (skills_dir / "ty" / "SKILL.md").write_text("---\nname: ty\n---\n\n# Ty Skill\n\nTy details.\n")

    agent_path = agents_dir / "execution-qa.md"
    agent_path.write_text("---\nname: execution-qa\nskills: ruff, ty\n---\n\n# QA Agent\n\nBody.\n")

    runner = CodexRunner(working_dir=tmp_path)
    skills_prompt = runner._extract_skills_prompt(agent_path)

    assert skills_prompt is not None
    assert "## Skill: ruff" in skills_prompt
    assert "Ruff details." in skills_prompt
    assert "## Skill: ty" in skills_prompt
    assert "Ty details." in skills_prompt


def test_codex_prompt_builds_with_system_and_context(tmp_path: Path) -> None:
    """CodexRunner should include system, skills, prompt, and context."""
    prompt = build_prompt_with_context(
        "Do the thing",
        {"task_id": "task-01"},
        "System prompt",
        "Skill prompt",
    )

    assert "System prompt" in prompt
    assert "Skill prompt" in prompt
    assert "\n---\n" in prompt
    assert "Do the thing" in prompt
    assert '"task_id": "task-01"' in prompt


def test_file_change_tracker_detects_added_and_changed(tmp_path: Path) -> None:
    """File change tracker should detect added and modified files."""
    target_dir = tmp_path / "proj"
    target_dir.mkdir()

    initial_file = target_dir / "file.txt"
    initial_file.write_text("original")

    tracker = _FileChangeTracker(target_dir)

    initial_file.write_text("modified content")
    (target_dir / "new.txt").write_text("new")

    files_changed, files_added = tracker.diff()

    assert "file.txt" in files_changed
    assert "new.txt" in files_added


def test_codex_command_bypass_sandbox(tmp_path: Path) -> None:
    """CodexRunner should add bypass flag when configured."""
    runner = CodexRunner(working_dir=tmp_path, dangerously_bypass=True)
    cmd = runner._build_command(tmp_path / "out.txt")

    assert "--dangerously-bypass-approvals-and-sandbox" in cmd
    assert "--sandbox" not in cmd


def test_claude_command_skip_permissions() -> None:
    """ClaudeRunner should add skip permissions flag when configured."""
    runner = ClaudeRunner(skip_permissions=True)
    cmd = runner._build_command("hello")
    agent_cmd = runner._build_agent_command("execution-qa", "hello")

    assert "--dangerously-skip-permissions" in cmd
    assert "--dangerously-skip-permissions" in agent_cmd
