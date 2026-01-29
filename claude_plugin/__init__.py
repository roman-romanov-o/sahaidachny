"""Sahaidachny Claude Code plugin.

This package contains the Claude Code plugin files:
- commands/: Slash commands for planning phase
- agents/: Subagent definitions for execution phase
- templates/: Artifact templates
- scripts/: Helper scripts
- skills/: Skill definitions
"""

from pathlib import Path


def get_plugin_path() -> Path:
    """Return the path to the plugin directory."""
    return Path(__file__).parent
