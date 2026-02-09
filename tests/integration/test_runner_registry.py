"""Tests for runner selection logic with default and per-agent overrides."""

from saha.commands.execution import _build_run_settings
from saha.config.settings import AgentRunnerConfig, AgentsConfig, Settings
from saha.orchestrator.factory import create_runner_registry
from saha.runners.claude import ClaudeRunner
from saha.runners.codex import CodexRunner


def test_default_runner_applies_when_not_overridden() -> None:
    settings = Settings(agents=AgentsConfig(default_runner="codex"))
    registry = create_runner_registry(settings)

    runner = registry.get_runner_for_agent("execution-implementer")
    assert isinstance(runner, CodexRunner)


def test_explicit_per_agent_runner_overrides_default() -> None:
    agents = AgentsConfig(
        default_runner="codex",
        qa=AgentRunnerConfig(runner="claude"),
    )
    settings = Settings(agents=agents)
    registry = create_runner_registry(settings)

    runner = registry.get_runner_for_agent("execution-qa")
    assert isinstance(runner, ClaudeRunner)


def test_cli_default_runner_updates_all_agents() -> None:
    settings = _build_run_settings(
        verbose=False,
        dry_run=False,
        qa_runner=None,
        default_runner="codex",
        dangerously_skip_permissions=False,
    )

    assert settings.agents.default_runner == "codex"
    assert settings.agents.implementer.runner == "codex"
    assert settings.agents.qa.runner == "codex"
    assert settings.agents.code_quality.runner == "codex"
    assert settings.agents.manager.runner == "codex"
    assert settings.agents.dod.runner == "codex"
