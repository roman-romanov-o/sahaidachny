"""Tool registry for managing external tool integrations."""

import shutil
import subprocess
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from saha.models.result import ResultStatus, ToolResult


def _get_venv_bin_path() -> Path | None:
    """Get the bin directory of the current venv."""
    # Get the directory containing the current Python executable
    python_path = Path(sys.executable)
    bin_dir = python_path.parent

    # Verify it looks like a venv bin directory
    if bin_dir.name in ("bin", "Scripts"):
        return bin_dir

    return None


class Tool(ABC):
    """Abstract base class for external tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name for identification."""
        ...

    @property
    @abstractmethod
    def command(self) -> str:
        """Command to check availability."""
        ...

    @abstractmethod
    def run(
        self,
        target: Path,
        config: dict[str, Any] | None = None,
    ) -> ToolResult:
        """Run the tool on the target path.

        Args:
            target: Path to file or directory to check.
            config: Tool-specific configuration.

        Returns:
            ToolResult with execution details.
        """
        ...

    def is_available(self) -> bool:
        """Check if the tool is installed."""
        # First check system PATH
        if shutil.which(self.command) is not None:
            return True

        # Also check in venv bin directory
        venv_bin = _get_venv_bin_path()
        if venv_bin:
            tool_path = venv_bin / self.command
            if tool_path.exists() and tool_path.is_file():
                return True

        return False

    def get_command_path(self) -> str:
        """Get the full path to the command."""
        # Check system PATH first
        system_path = shutil.which(self.command)
        if system_path:
            return system_path

        # Check venv bin
        venv_bin = _get_venv_bin_path()
        if venv_bin:
            tool_path = venv_bin / self.command
            if tool_path.exists():
                return str(tool_path)

        return self.command

    def _run_command(
        self,
        cmd: list[str],
        cwd: Path | None = None,
        timeout: int = 120,
    ) -> tuple[int, str, str]:
        """Run a command and return exit code, stdout, stderr.

        Automatically resolves the command to use venv path if available.
        """
        # Use full path for the command
        resolved_cmd = [self.get_command_path()] + cmd[1:]

        try:
            result = subprocess.run(
                resolved_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 124, "", "Command timed out"
        except FileNotFoundError:
            return 127, "", f"Command not found: {resolved_cmd[0]}"
        except Exception as e:
            return 1, "", str(e)


class ToolRegistry:
    """Registry for managing available tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_available(self) -> list[str]:
        """List names of available tools."""
        return [name for name, tool in self._tools.items() if tool.is_available()]

    def list_all(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def run_tool(
        self,
        name: str,
        target: Path,
        config: dict[str, Any] | None = None,
    ) -> ToolResult:
        """Run a specific tool."""
        tool = self._tools.get(name)
        if not tool:
            return ToolResult(
                tool_name=name,
                status=ResultStatus.ERROR,
                exit_code=1,
                stderr=f"Unknown tool: {name}",
            )

        if not tool.is_available():
            return ToolResult(
                tool_name=name,
                status=ResultStatus.ERROR,
                exit_code=127,
                stderr=f"Tool not installed: {name}",
            )

        return tool.run(target, config)

    def run_all(
        self,
        target: Path,
        tool_names: list[str] | None = None,
        config: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, ToolResult]:
        """Run multiple tools and collect results."""
        names = tool_names or self.list_available()
        config = config or {}

        results = {}
        for name in names:
            results[name] = self.run_tool(name, target, config.get(name))

        return results


def create_default_registry() -> ToolRegistry:
    """Create a registry with default tools."""
    from saha.tools.complexity import ComplexityTool
    from saha.tools.pytest_runner import PytestTool
    from saha.tools.ruff import RuffTool
    from saha.tools.ty import TyTool

    registry = ToolRegistry()
    registry.register(RuffTool())
    registry.register(TyTool())
    registry.register(ComplexityTool())
    registry.register(PytestTool())

    return registry
