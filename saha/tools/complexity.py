"""Complexity checker integration using complexipy."""

from pathlib import Path
from typing import Any

from saha.models.result import ResultStatus, ToolResult
from saha.tools.registry import Tool


class ComplexityTool(Tool):
    """Complexity checker using complexipy for cognitive complexity analysis."""

    @property
    def name(self) -> str:
        return "complexity"

    @property
    def command(self) -> str:
        return "complexipy"

    def run(
        self,
        target: Path,
        config: dict[str, Any] | None = None,
    ) -> ToolResult:
        """Run complexipy on the target."""
        config = config or {}

        threshold = config.get("threshold", 15)

        cmd = ["complexipy", str(target)]

        # Add threshold for warnings
        cmd.extend(["--max-complexity", str(threshold)])

        exit_code, stdout, stderr = self._run_command(cmd)

        # Parse output for high-complexity functions
        issues = []
        metrics: dict[str, Any] = {
            "threshold": threshold,
            "high_complexity_functions": [],
        }

        for line in stdout.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Look for complexity scores above threshold
            # complexipy output format varies, so we do basic parsing
            if "complexity" in line.lower() or ":" in line:
                # Try to extract complexity value
                parts = line.split()
                for part in parts:
                    try:
                        complexity = int(part)
                        if complexity > threshold:
                            issues.append(line)
                            metrics["high_complexity_functions"].append(
                                {
                                    "line": line,
                                    "complexity": complexity,
                                }
                            )
                        break
                    except ValueError:
                        continue

        # Consider failure if we have high complexity functions
        has_issues = len(issues) > 0
        status = ResultStatus.FAILURE if has_issues else ResultStatus.SUCCESS

        return ToolResult(
            tool_name=self.name,
            status=status,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            issues=issues,
            metrics=metrics,
        )
