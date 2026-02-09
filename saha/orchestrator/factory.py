"""Factory functions for creating the agentic loop orchestrator."""

from pathlib import Path

import typer

from saha.config.settings import Settings
from saha.hooks.notification import LoggingHook, NtfyHook
from saha.hooks.registry import HookRegistry
from saha.orchestrator.loop import AgenticLoop
from saha.orchestrator.state import StateManager
from saha.runners.base import Runner
from saha.runners.claude import ClaudeRunner, MockRunner
from saha.runners.codex import CodexRunner
from saha.runners.gemini import GeminiRunner
from saha.runners.registry import AgentConfig, RunnerRegistry, RunnerType
from saha.tools.registry import create_default_registry


def create_runner_registry(settings: Settings) -> RunnerRegistry:
    """Create and configure the runner registry.

    Sets up runners for Claude, Codex, Gemini, and Mock backends, and configures
    per-agent runner assignments based on settings.
    """
    registry = RunnerRegistry()

    # Register runner factories
    # Stream output by default for transparency during execution
    registry.register_factory(
        RunnerType.CLAUDE,
        ClaudeRunner,
        model=settings.claude_model,
        working_dir=Path.cwd(),
        stream_output=True,
        skip_permissions=settings.claude_dangerously_skip_permissions,
    )

    registry.register_factory(
        RunnerType.CODEX,
        CodexRunner,
        model=settings.codex_model,
        working_dir=Path.cwd(),
        sandbox=settings.codex_sandbox,
        dangerously_bypass=settings.codex_dangerously_bypass_sandbox,
    )

    registry.register_factory(
        RunnerType.GEMINI,
        GeminiRunner,
        model=settings.gemini_model,
        working_dir=Path.cwd(),
    )

    registry.register_factory(RunnerType.MOCK, MockRunner)

    # Set default runner type
    default_type = RunnerType(settings.agents.default_runner)
    registry.set_default_runner(default_type)

    # Configure per-agent runners from settings
    agent_mapping = {
        "execution-implementer": settings.agents.implementer,
        "execution-qa": settings.agents.qa,
        "execution-code-quality": settings.agents.code_quality,
        "execution-manager": settings.agents.manager,
        "execution-dod": settings.agents.dod,
    }

    for agent_name, config in agent_mapping.items():
        fields_set = getattr(config, "model_fields_set", set())
        runner_name = config.runner if "runner" in fields_set else default_type.value
        registry.configure_agent(
            AgentConfig(
                agent_name=agent_name,
                runner_type=RunnerType(runner_name),
                agent_variant=config.variant,
                timeout=config.timeout,
            )
        )

    return registry


def validate_configured_runners(registry: RunnerRegistry, settings: Settings) -> None:
    """Validate that all configured runners are available.

    Checks each unique runner type that's actually configured for agents
    and fails fast if any are unavailable.

    Args:
        registry: The runner registry to validate.
        settings: Settings containing agent configurations.

    Raises:
        typer.Exit: If any configured runner is not available.
    """
    # Collect unique runner types actually in use
    configured_types: set[RunnerType] = {RunnerType(settings.agents.default_runner)}

    agent_configs = [
        settings.agents.implementer,
        settings.agents.qa,
        settings.agents.code_quality,
        settings.agents.manager,
        settings.agents.dod,
    ]

    for config in agent_configs:
        configured_types.add(RunnerType(config.runner))

    # Validate each configured runner type
    unavailable: list[str] = []
    for runner_type in configured_types:
        if runner_type == RunnerType.MOCK:
            continue  # Mock is always available

        runner = registry.get_runner(runner_type)
        if not runner.is_available():
            unavailable.append(runner.get_name())

    if unavailable:
        typer.echo("Error: The following configured runners are not available:", err=True)
        for name in unavailable:
            typer.echo(f"  - {name}", err=True)
        typer.echo("\nInstall missing CLIs or change runner configuration.", err=True)
        raise typer.Exit(1)


def _create_default_runner(settings: Settings) -> Runner:
    """Create the default runner based on settings."""
    if settings.runner == "mock":
        return MockRunner()
    elif settings.runner == "gemini":
        return GeminiRunner(
            model=settings.gemini_model,
            working_dir=Path.cwd(),
        )
    elif settings.runner == "codex":
        return CodexRunner(
            model=settings.codex_model,
            working_dir=Path.cwd(),
            sandbox=settings.codex_sandbox,
            dangerously_bypass=settings.codex_dangerously_bypass_sandbox,
        )
    else:
        return ClaudeRunner(
            model=settings.claude_model,
            working_dir=Path.cwd(),
            stream_output=True,  # Stream output for transparency
            skip_permissions=settings.claude_dangerously_skip_permissions,
        )


def _create_hook_registry(settings: Settings) -> HookRegistry:
    """Create and configure the hook registry."""
    hooks = HookRegistry()
    hooks.register(LoggingHook())

    if settings.hooks.ntfy_enabled:
        hooks.register(
            NtfyHook(
                topic=settings.hooks.ntfy_topic,
                server=settings.hooks.ntfy_server,
                token=settings.hooks.ntfy_token,
                user=settings.hooks.ntfy_user,
                password=settings.hooks.ntfy_password,
            )
        )

    return hooks


def create_orchestrator(settings: Settings) -> AgenticLoop:
    """Create the agentic loop orchestrator with all components.

    This is the main factory function that assembles all the pieces:
    - Runner registry for multi-backend support
    - Default runner for backwards compatibility
    - Tool registry for code quality checks
    - Hook registry for event notifications
    - State manager for persistence

    Args:
        settings: Application settings.

    Returns:
        Configured AgenticLoop instance ready to run tasks.
    """
    # Create runner registry for multi-backend support
    runner_registry = create_runner_registry(settings)

    # Validate all configured runners are available (fail fast)
    validate_configured_runners(runner_registry, settings)

    # Create default runner for backwards compatibility
    runner = _create_default_runner(settings)

    # Create tool registry
    tools = create_default_registry()

    # Create hook registry
    hooks = _create_hook_registry(settings)

    # Create state manager
    state_manager = StateManager(settings.state_dir)

    return AgenticLoop(
        runner=runner,
        tool_registry=tools,
        hook_registry=hooks,
        state_manager=state_manager,
        settings=settings,
        runner_registry=runner_registry,
    )
