"""Unit tests for command building in Codex and Gemini runners.

Tests: TC-UNIT-030 through TC-UNIT-032
Covers: Codex stdin mode, Gemini no --yolo, Claude --print flag.
"""

from pathlib import Path

from saha.runners.codex import CodexRunner
from saha.runners.gemini import GeminiRunner


class TestCodexCommandBuilding:
    """Tests for CodexRunner._build_command()."""

    def test_basic_command_structure(self, tmp_path: Path) -> None:
        """TC-UNIT-030: Codex command uses exec with stdin and output file."""
        runner = CodexRunner(working_dir=tmp_path)
        output_file = tmp_path / "out.txt"
        cmd = runner._build_command(output_file)

        assert "codex" in cmd
        assert "exec" in cmd
        assert "-" in cmd  # stdin marker
        assert "--output-last-message" in cmd
        assert str(output_file) in cmd
        assert "--skip-git-repo-check" in cmd

    def test_includes_model_when_set(self, tmp_path: Path) -> None:
        """Codex command includes --model when model is configured."""
        runner = CodexRunner(model="o3", working_dir=tmp_path)
        cmd = runner._build_command(tmp_path / "out.txt")

        assert "--model" in cmd
        assert "o3" in cmd

    def test_bypass_mode(self, tmp_path: Path) -> None:
        """TC-UNIT-030 ext: Codex command includes bypass when configured."""
        runner = CodexRunner(working_dir=tmp_path, dangerously_bypass=True)
        cmd = runner._build_command(tmp_path / "out.txt")

        assert "--dangerously-bypass-approvals-and-sandbox" in cmd
        assert "--sandbox" not in cmd

    def test_sandbox_mode(self, tmp_path: Path) -> None:
        """Codex command includes sandbox when configured."""
        runner = CodexRunner(working_dir=tmp_path, sandbox="workspace-write")
        cmd = runner._build_command(tmp_path / "out.txt")

        assert "--sandbox" in cmd
        assert "workspace-write" in cmd

    def test_no_model_when_none(self, tmp_path: Path) -> None:
        """Codex command omits --model when model is None."""
        runner = CodexRunner(model=None, working_dir=tmp_path)
        cmd = runner._build_command(tmp_path / "out.txt")

        assert "--model" not in cmd


class TestGeminiCommandBuilding:
    """Tests for GeminiRunner._build_command()."""

    def test_no_yolo_flag(self, tmp_path: Path) -> None:
        """TC-UNIT-031: Gemini command does NOT contain --yolo."""
        runner = GeminiRunner(working_dir=tmp_path)
        cmd = runner._build_command("Test prompt")

        assert "--yolo" not in cmd
        assert "gemini" in cmd

    def test_uses_prompt_flag(self, tmp_path: Path) -> None:
        """Gemini command uses -p flag for prompt."""
        runner = GeminiRunner(working_dir=tmp_path)
        cmd = runner._build_command("Test prompt")

        assert "-p" in cmd

    def test_includes_model(self, tmp_path: Path) -> None:
        """Gemini command includes --model when configured."""
        runner = GeminiRunner(model="gemini-2.5-flash", working_dir=tmp_path)
        cmd = runner._build_command("Test")

        assert "--model" in cmd
        assert "gemini-2.5-flash" in cmd

    def test_includes_sandbox(self, tmp_path: Path) -> None:
        """Gemini command includes --sandbox when enabled."""
        runner = GeminiRunner(working_dir=tmp_path, sandbox=True)
        cmd = runner._build_command("Test")

        assert "--sandbox" in cmd

    def test_combines_system_prompt_with_user_prompt(self, tmp_path: Path) -> None:
        """Gemini command embeds system prompt into the -p argument."""
        runner = GeminiRunner(working_dir=tmp_path)
        cmd = runner._build_command("User question", system_prompt="You are helpful")

        # Find the prompt argument (after -p)
        p_index = cmd.index("-p")
        full_prompt = cmd[p_index + 1]

        assert "You are helpful" in full_prompt
        assert "User question" in full_prompt
        assert "---" in full_prompt
