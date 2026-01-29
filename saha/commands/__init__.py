"""CLI command modules for Saha.

This package contains the CLI commands organized by functionality:
- execution: Agentic loop commands (run, resume, status, tools, clean, version)
- plugin: Plugin management commands (plugin, claude)
- common: Shared utilities (logging setup)
"""

from saha.commands.common import setup_logging
from saha.commands.execution import register_execution_commands
from saha.commands.plugin import register_plugin_commands

__all__ = ["register_execution_commands", "register_plugin_commands", "setup_logging"]
