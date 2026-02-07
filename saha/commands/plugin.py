"""Plugin management CLI commands.

This module contains commands for managing the Claude Code plugin:
- plugin: Show plugin location or copy plugin files
- claude: Launch Claude Code with Sahaidachny plugin configured
"""

import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel

logger = logging.getLogger(__name__)


def _find_plugin_path() -> Path | None:
    """Find the plugin directory in various locations."""
    # First, try to import the plugin package (works when installed)
    try:
        import claude_plugin

        plugin_path = claude_plugin.get_plugin_path()
        if plugin_path.exists() and (plugin_path / "commands").exists():
            return plugin_path
    except ImportError:
        pass

    # Fallback: search in common locations
    candidates = [
        # Current working directory (for development)
        Path.cwd() / "claude_plugin",
        # Relative to package (for editable installs)
        Path(__file__).parent.parent.parent / "claude_plugin",
        # User data directory fallback
        Path.home() / ".local" / "share" / "sahaidachny" / "claude_plugin",
    ]

    for candidate in candidates:
        if candidate.exists() and (candidate / "commands").exists():
            return candidate

    return None


class SyncResult(BaseModel):
    """Result of syncing Claude artifacts."""

    agents_synced: list[str]
    total_synced: int
    plugin_path: str | None


# Required execution agents that must exist for the loop to run
REQUIRED_EXECUTION_AGENTS = [
    "execution-implementer.md",
    "execution-qa.md",
    "execution-code-quality.md",
    "execution-dod.md",
    "execution-manager.md",
    "execution-test-critique.md",
]

# Optional agent variants
OPTIONAL_EXECUTION_AGENTS = [
    "execution-qa-playwright.md",
]


def sync_claude_artifacts(claude_dir: Path | None = None) -> SyncResult:
    """Ensure all required Claude artifacts exist in the project.

    Checks for required execution agents in .claude/agents/ and copies
    any missing ones from the plugin directory.

    Args:
        claude_dir: Path to .claude directory. Defaults to .claude in cwd.

    Returns:
        SyncResult with list of synced files.
    """
    if claude_dir is None:
        claude_dir = Path.cwd() / ".claude"

    plugin_path = _find_plugin_path()
    if plugin_path is None:
        logger.warning("Plugin directory not found, cannot sync agents")
        return SyncResult(agents_synced=[], total_synced=0, plugin_path=None)

    agents_dir = claude_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    plugin_agents = plugin_path / "agents"
    if not plugin_agents.exists():
        logger.warning(f"Plugin agents directory not found: {plugin_agents}")
        return SyncResult(agents_synced=[], total_synced=0, plugin_path=str(plugin_path))

    synced: list[str] = []

    # Sync required agents
    for agent_name in REQUIRED_EXECUTION_AGENTS + OPTIONAL_EXECUTION_AGENTS:
        target = agents_dir / agent_name
        source = plugin_agents / agent_name

        if not target.exists() and source.exists():
            shutil.copy2(source, target)
            synced.append(agent_name)
            logger.info(f"Synced agent: {agent_name}")

    return SyncResult(
        agents_synced=synced,
        total_synced=len(synced),
        plugin_path=str(plugin_path),
    )


def _show_plugin_contents(plugin_path: Path) -> None:
    """Display plugin directory contents."""
    typer.echo(f"Plugin location: {plugin_path}")
    typer.echo("\nContents:")
    for item in sorted(plugin_path.iterdir()):
        if item.is_dir():
            count = len(list(item.iterdir()))
            typer.echo(f"  {item.name}/ ({count} files)")
        else:
            typer.echo(f"  {item.name}")
    typer.echo("\nTo copy plugin: saha plugin --copy-to <target-dir>")


def _get_command_target_name(item_name: str) -> str:
    """Get target filename for command, adding saha: prefix as needed."""
    # Main help command stays as-is (no prefix)
    if item_name == "saha.md":
        return "saha.md"
    return f"saha:{item_name}"


def _copy_plugin_commands(src_dir: Path, dst_dir: Path) -> int:
    """Copy command files with namespace prefix. Returns count of files copied."""
    if not src_dir.exists():
        return 0

    dst_dir.mkdir(exist_ok=True)
    copied = 0

    for item in src_dir.iterdir():
        if item.suffix == ".md":
            target_name = _get_command_target_name(item.name)
            item_dst = dst_dir / target_name
            if not item_dst.exists():
                shutil.copy2(item, item_dst)
                copied += 1

    return copied


def _copy_single_item(src_item: Path, dst_item: Path) -> bool:
    """Copy a single file or directory. Returns True if copied."""
    if dst_item.exists():
        return False

    if src_item.is_dir():
        shutil.copytree(src_item, dst_item)
    else:
        shutil.copy2(src_item, dst_item)
    return True


def _copy_directory_contents(src: Path, dst: Path) -> int:
    """Copy contents of a directory. Returns count of items copied."""
    if not src.exists():
        return 0

    dst.mkdir(exist_ok=True)
    copied = 0
    for item in src.iterdir():
        if _copy_single_item(item, dst / item.name):
            copied += 1
    return copied


def _copy_plugin_directories(plugin_path: Path, target_path: Path, dir_names: list[str]) -> int:
    """Copy plugin directories. Returns count of items copied."""
    total = 0
    for dir_name in dir_names:
        total += _copy_directory_contents(plugin_path / dir_name, target_path / dir_name)
    return total


def _copy_plugin_to_target(plugin_path: Path, target_path: Path) -> int:
    """Copy all plugin files to target directory. Returns total files copied."""
    target_path.mkdir(parents=True, exist_ok=True)
    copied = 0

    # Copy commands with namespace prefix
    copied += _copy_plugin_commands(plugin_path / "commands", target_path / "commands")

    # Copy other directories
    other_dirs = ["agents", "templates", "scripts", "skills"]
    copied += _copy_plugin_directories(plugin_path, target_path, other_dirs)

    # Copy settings.json
    settings_src = plugin_path / "settings.json"
    settings_dst = target_path / "settings.json"
    if settings_src.exists() and not settings_dst.exists():
        shutil.copy2(settings_src, settings_dst)
        copied += 1

    return copied


def _setup_commands_for_claude(commands_src: Path, commands_dst: Path) -> None:
    """Setup commands directory with namespace prefixes for Claude Code."""
    if not commands_src.exists():
        return

    commands_dst.mkdir(exist_ok=True)
    for item in commands_src.iterdir():
        if item.suffix == ".md":
            target_name = _get_command_target_name(item.name)
            item_dst = commands_dst / target_name
            if item_dst.is_symlink():
                item_dst.unlink()
            if not item_dst.exists():
                shutil.copy2(item, item_dst)

            # Clean up legacy files that cause duplicate commands
            # 1. Unprefixed symlinks
            unprefixed_dst = commands_dst / item.name
            if unprefixed_dst.is_symlink():
                unprefixed_dst.unlink()

            # 2. Old sahaidachny: prefixed files (migrated to saha: prefix)
            if item.name == "saha.md":
                old_prefixed = commands_dst / "sahaidachny.md"
            else:
                old_prefixed = commands_dst / f"sahaidachny:{item.name}"
            if old_prefixed.exists() and old_prefixed != item_dst:
                old_prefixed.unlink()


def _symlink_plugin_directory(src: Path, dst: Path) -> None:
    """Symlink a plugin directory, handling existing directories."""
    if not src.exists():
        return

    if dst.is_symlink():
        dst.unlink()
    elif dst.exists():
        # Directory exists, merge by symlinking individual files
        for item in src.iterdir():
            item_dst = dst / item.name
            if not item_dst.exists():
                item_dst.symlink_to(item.resolve())
        return

    dst.symlink_to(src.resolve())


def _copy_plugin_directory(src: Path, dst: Path) -> None:
    """Copy a plugin directory, replacing existing symlinks with actual files."""
    if not src.exists():
        return

    # If destination is a symlink, remove it to replace with actual directory
    if dst.is_symlink():
        dst.unlink()

    dst.mkdir(exist_ok=True)

    for item in src.iterdir():
        item_dst = dst / item.name
        # Remove existing symlink if present
        if item_dst.is_symlink():
            item_dst.unlink()
        if not item_dst.exists():
            if item.is_dir():
                shutil.copytree(item, item_dst)
            else:
                shutil.copy2(item, item_dst)


def _setup_plugin_directories_for_claude(plugin_path: Path, claude_dir: Path) -> None:
    """Setup plugin directories for Claude Code.

    Agents are copied (not symlinked) because Claude Code's Search/Glob tools
    don't follow directory symlinks, causing 'file not found' errors.
    Other directories use symlinks for efficiency.
    """
    # Copy agents directory (Search/Glob doesn't follow symlinks)
    _copy_plugin_directory(plugin_path / "agents", claude_dir / "agents")

    # Symlink other directories
    symlink_dirs = ["templates", "scripts", "skills"]
    for dir_name in symlink_dirs:
        src = plugin_path / dir_name
        dst = claude_dir / dir_name
        _symlink_plugin_directory(src, dst)


def _setup_settings_for_claude(plugin_path: Path, claude_dir: Path) -> None:
    """Copy settings.json and clean up old hooks.json."""
    settings_src = plugin_path / "settings.json"
    settings_dst = claude_dir / "settings.json"
    if settings_src.exists():
        if settings_dst.is_symlink():
            settings_dst.unlink()
        shutil.copy2(settings_src, settings_dst)

    # Remove old hooks.json symlink if it exists
    old_hooks = claude_dir / "hooks.json"
    if old_hooks.is_symlink():
        old_hooks.unlink()


def _validate_claude_prerequisites(plugin_path: Path | None) -> tuple[str, Path]:
    """Validate Claude CLI and plugin path exist. Returns (claude_path, plugin_path)."""
    claude_path = shutil.which("claude")
    if claude_path is None:
        typer.echo("Error: Claude Code CLI not found in PATH.", err=True)
        typer.echo("Install it from: https://claude.ai/code", err=True)
        raise typer.Exit(1)

    resolved_plugin = plugin_path or _find_plugin_path()
    if resolved_plugin is None or not resolved_plugin.exists():
        typer.echo("Error: Plugin directory not found.", err=True)
        typer.echo("Searched locations:", err=True)
        typer.echo("  - ./claude_plugin", err=True)
        typer.echo("  - <package>/claude_plugin", err=True)
        typer.echo(f"  - {sys.prefix}/share/sahaidachny/claude_plugin", err=True)
        raise typer.Exit(1)

    return claude_path, resolved_plugin


def register_plugin_commands(app: typer.Typer) -> None:
    """Register all plugin-related commands with the Typer app."""

    @app.command(name="plugin")
    def plugin_info(
        copy_to: Annotated[
            Path | None,
            typer.Option("--copy-to", "-c", help="Copy plugin to specified directory"),
        ] = None,
    ) -> None:
        """Show plugin location or copy plugin files.

        Examples:
            saha plugin                    # Show plugin location
            saha plugin --copy-to .claude  # Copy plugin to .claude directory
        """
        plugin_path = _find_plugin_path()

        if plugin_path is None:
            typer.echo("Plugin not found!", err=True)
            typer.echo("\nSearched locations:", err=True)
            typer.echo("  - ./claude_plugin", err=True)
            typer.echo("  - <package>/claude_plugin", err=True)
            typer.echo(f"  - {sys.prefix}/share/sahaidachny/claude_plugin", err=True)
            raise typer.Exit(1)

        if copy_to is None:
            _show_plugin_contents(plugin_path)
        else:
            copied = _copy_plugin_to_target(plugin_path, copy_to)
            typer.echo(f"Copied plugin files to: {copy_to}")
            typer.echo(f"Files copied: {copied}")

    @app.command(name="claude")
    def launch_claude(
        args: Annotated[
            list[str] | None,
            typer.Argument(help="Additional arguments to pass to Claude Code"),
        ] = None,
        plugin_path: Annotated[
            Path | None,
            typer.Option("--plugin-path", "-p", help="Path to plugin directory"),
        ] = None,
    ) -> None:
        """Launch Claude Code with Sahaidachny plugin configured.

        This command starts Claude Code with the Sahaidachny plugin commands
        and agents registered, enabling the planning workflow.

        Examples:
            saha claude
            saha claude --resume
            saha claude --dangerously-skip-permissions
        """
        claude_path, resolved_plugin = _validate_claude_prerequisites(plugin_path)

        # Ensure .claude directories exist
        claude_dir = Path.cwd() / ".claude"
        claude_dir.mkdir(exist_ok=True)

        # Setup plugin components
        _setup_commands_for_claude(resolved_plugin / "commands", claude_dir / "commands")
        _setup_plugin_directories_for_claude(resolved_plugin, claude_dir)
        _setup_settings_for_claude(resolved_plugin, claude_dir)

        typer.echo(f"Plugin configured from: {resolved_plugin}")
        typer.echo("Starting Claude Code...")
        typer.echo()

        # Build and execute command
        cmd = [claude_path]
        if args:
            cmd.extend(args)

        try:
            subprocess.run(cmd, check=False)
        except KeyboardInterrupt:
            pass
