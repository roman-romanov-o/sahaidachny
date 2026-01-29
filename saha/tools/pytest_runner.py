"""Pytest test runner integration."""

import json
from pathlib import Path
from typing import Any

from saha.models.result import ResultStatus, ToolResult
from saha.tools.registry import Tool


class PytestTool(Tool):
    """Pytest runner for executing tests."""

    @property
    def name(self) -> str:
        return "pytest"

    @property
    def command(self) -> str:
        return "pytest"

    def run(
        self,
        target: Path,
        config: dict[str, Any] | None = None,
    ) -> ToolResult:
        """Run pytest on the target."""
        config = config or {}

        cmd = ["pytest", str(target)]

        # Add verbose by default
        if config.get("verbose", True):
            cmd.append("-v")

        # Add extra args
        extra_args = config.get("extra_args", [])
        cmd.extend(extra_args)

        # Run specific test file or pattern
        test_pattern = config.get("test_pattern")
        if test_pattern:
            cmd.extend(["-k", test_pattern])

        # Add JSON report if pytest-json-report is available
        report_path = config.get("report_path")
        if report_path:
            cmd.extend(["--json-report", f"--json-report-file={report_path}"])

        exit_code, stdout, stderr = self._run_command(cmd, timeout=300)

        # Parse output for test results
        issues = []
        metrics: dict[str, Any] = {
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
        }

        # Try to parse JSON report if available
        if report_path:
            report_file = Path(report_path)
            if report_file.exists():
                try:
                    with report_file.open() as f:
                        report = json.load(f)
                    summary = report.get("summary", {})
                    metrics["passed"] = summary.get("passed", 0)
                    metrics["failed"] = summary.get("failed", 0)
                    metrics["errors"] = summary.get("error", 0)
                    metrics["skipped"] = summary.get("skipped", 0)

                    # Extract failed test details
                    for test in report.get("tests", []):
                        if test.get("outcome") == "failed":
                            nodeid = test.get("nodeid", "")
                            message = test.get("call", {}).get("longrepr", "")
                            issues.append(f"FAILED: {nodeid}\n{message[:500]}")
                except (json.JSONDecodeError, OSError):
                    pass

        # Fall back to parsing stdout
        if not metrics.get("passed") and not metrics.get("failed"):
            self._parse_pytest_output(stdout, metrics, issues)

        # Determine status
        if exit_code == 0:
            status = ResultStatus.SUCCESS
        elif metrics.get("failed", 0) > 0 or metrics.get("errors", 0) > 0:
            status = ResultStatus.FAILURE
        else:
            status = ResultStatus.ERROR

        return ToolResult(
            tool_name=self.name,
            status=status,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            issues=issues,
            metrics=metrics,
        )

    def _parse_pytest_output(
        self,
        output: str,
        metrics: dict[str, Any],
        issues: list[str],
    ) -> None:
        """Parse pytest text output for basic metrics."""
        lines = output.split("\n")

        for line in lines:
            # Look for summary line like "1 passed, 2 failed, 1 error"
            if "passed" in line or "failed" in line or "error" in line:
                parts = line.lower().split()
                for i, part in enumerate(parts):
                    if part == "passed" and i > 0:
                        try:
                            metrics["passed"] = int(parts[i - 1])
                        except ValueError:
                            pass
                    elif part == "failed" and i > 0:
                        try:
                            metrics["failed"] = int(parts[i - 1])
                        except ValueError:
                            pass
                    elif part == "error" and i > 0:
                        try:
                            metrics["errors"] = int(parts[i - 1])
                        except ValueError:
                            pass
                    elif part == "skipped" and i > 0:
                        try:
                            metrics["skipped"] = int(parts[i - 1])
                        except ValueError:
                            pass

            # Capture FAILED lines
            if line.strip().startswith("FAILED"):
                issues.append(line.strip())
