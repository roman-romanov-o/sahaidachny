"""Integration tests for token usage extraction in CLI runners."""

import subprocess
from pathlib import Path

from saha.runners.claude import ClaudeRunner
from saha.runners.codex import CodexRunner


def test_claude_runner_extracts_token_usage(monkeypatch, tmp_path: Path) -> None:
    """ClaudeRunner should extract token usage from NDJSON output."""
    ndjson = "\n".join(
        [
            '{"type":"assistant","message":{"content":[{"type":"text","text":"Hello"}]}}',
            '{"type":"result","result":"done","usage":{"input_tokens":12,"output_tokens":8}}',
        ]
    )

    class FakeProcess:
        def __init__(self) -> None:
            self.returncode = 0

        def communicate(self, _input=None, timeout=None):
            return ndjson, ""

        def kill(self) -> None:
            return None

        def terminate(self) -> None:
            return None

        def wait(self, timeout=None):
            return self.returncode

    def fake_popen(*args, **kwargs):
        return FakeProcess()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    runner = ClaudeRunner(working_dir=tmp_path)
    result = runner.run_prompt("hello")

    assert result.token_usage is not None
    assert result.token_usage.get("input_tokens") == 12
    assert result.token_usage.get("output_tokens") == 8
    assert result.tokens_used == 20


def test_codex_runner_extracts_token_usage(monkeypatch, tmp_path: Path) -> None:
    """CodexRunner should extract token usage from JSON output."""
    output_payload = (
        '{"response":"ok","usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15}}'
    )

    class FakeProcess:
        def __init__(self, cmd):
            self._cmd = cmd
            self.returncode = 0

        def communicate(self, _input=None, timeout=None):
            if "--output-last-message" in self._cmd:
                idx = self._cmd.index("--output-last-message")
                output_path = Path(self._cmd[idx + 1])
                output_path.write_text(output_payload)
            return "", ""

        def kill(self) -> None:
            return None

        def terminate(self) -> None:
            return None

        def wait(self, timeout=None):
            return self.returncode

    def fake_popen(cmd, **kwargs):
        return FakeProcess(cmd)

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    runner = CodexRunner(working_dir=tmp_path)
    result = runner.run_prompt("hello")

    assert result.token_usage is not None
    assert result.token_usage.get("input_tokens") == 10
    assert result.token_usage.get("output_tokens") == 5
    assert result.tokens_used == 15
