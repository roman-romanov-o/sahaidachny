"""Ruff linter integration."""

import json
from pathlib import Path
from typing import Any

from saha.models.result import ResultStatus, ToolResult
from saha.tools.registry import Tool


class RuffTool(Tool):
    """Ruff linter tool for Python code quality."""

    @property
    def name(self) -> str:
        return "ruff"

    @property
    def command(self) -> str:
        return "ruff"

    def run(
        self,
        target: Path,
        config: dict[str, Any] | None = None,
    ) -> ToolResult:
        """Run ruff check on the target."""
        config = config or {}

        cmd = ["ruff", "check", str(target)]

        # Add config file if specified
        config_path = config.get("config_path")
        if config_path:
            cmd.extend(["--config", str(config_path)])

        # Output format for parsing
        cmd.extend(["--output-format", "json"])

        exit_code, stdout, stderr = self._run_command(cmd)

        # Parse JSON output for issues
        issues = []
        metrics: dict[str, Any] = {"total_issues": 0, "by_code": {}}

        if stdout.strip():
            try:
                parsed = json.loads(stdout)
                for item in parsed:
                    code = item.get("code", "")
                    message = item.get("message", "")
                    location = item.get("location", {})
                    file_path = item.get("filename", "")
                    row = location.get("row", 0)

                    issues.append(f"{file_path}:{row}: [{code}] {message}")
                    metrics["by_code"][code] = metrics["by_code"].get(code, 0) + 1

                metrics["total_issues"] = len(issues)
            except json.JSONDecodeError:
                # Fall back to raw output
                issues = [line for line in stdout.split("\n") if line.strip()]

        # Exit code 0 = no issues, 1 = issues found
        status = ResultStatus.SUCCESS if exit_code == 0 else ResultStatus.FAILURE

        return ToolResult(
            tool_name=self.name,
            status=status,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            issues=issues,
            metrics=metrics,
        )

    def run_fix(
        self,
        target: Path,
        config: dict[str, Any] | None = None,
    ) -> ToolResult:
        """Run ruff check with --fix to auto-fix issues."""
        config = config or {}

        cmd = ["ruff", "check", "--fix", str(target)]

        config_path = config.get("config_path")
        if config_path:
            cmd.extend(["--config", str(config_path)])

        exit_code, stdout, stderr = self._run_command(cmd)

        status = ResultStatus.SUCCESS if exit_code == 0 else ResultStatus.PARTIAL

        return ToolResult(
            tool_name=self.name,
            status=status,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
        )
