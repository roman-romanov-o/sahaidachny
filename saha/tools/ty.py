"""ty type checker integration (Astral's fast Python type checker)."""

from pathlib import Path
from typing import Any

from saha.models.result import ResultStatus, ToolResult
from saha.tools.registry import Tool


class TyTool(Tool):
    """ty type checker tool for Python type safety."""

    @property
    def name(self) -> str:
        return "ty"

    @property
    def command(self) -> str:
        return "ty"

    def run(
        self,
        target: Path,
        config: dict[str, Any] | None = None,
    ) -> ToolResult:
        """Run ty check on the target."""
        config = config or {}

        cmd = ["ty", "check", str(target)]

        # Add strict mode if specified
        if config.get("strict", False):
            cmd.append("--strict")

        exit_code, stdout, stderr = self._run_command(cmd)

        # Parse output for issues
        issues = []
        metrics: dict[str, Any] = {"total_errors": 0, "by_type": {}}

        output = stdout or stderr
        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue
            if "error:" in line.lower() or "warning:" in line.lower():
                issues.append(line)
                # Try to categorize
                if "error:" in line.lower():
                    metrics["total_errors"] = metrics.get("total_errors", 0) + 1

        # Exit code 0 = no type errors
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
