"""Notification hooks using ntfy.sh."""

import base64
import logging
import urllib.error
import urllib.request
from typing import Any

from saha.hooks.base import Hook, HookEvent
from saha.models.state import ExecutionState, StepStatus

logger = logging.getLogger(__name__)


class NtfyHook(Hook):
    """Hook that sends notifications via ntfy.sh.

    Authentication can be provided via:
    - Access token (SAHA_HOOK_NTFY_TOKEN)
    - Basic auth (SAHA_HOOK_NTFY_USER + SAHA_HOOK_NTFY_PASSWORD)
    """

    def __init__(
        self,
        topic: str,
        server: str = "https://ntfy.sh",
        enabled: bool = True,
        token: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ):
        self._topic = topic
        self._server = server.rstrip("/")
        self._enabled = enabled
        self._token = token
        self._user = user
        self._password = password

    @property
    def name(self) -> str:
        return "ntfy"

    @property
    def events(self) -> list[HookEvent]:
        """Only trigger on completion/failure/stop events."""
        return [
            HookEvent.LOOP_COMPLETE,
            HookEvent.LOOP_FAILED,
            HookEvent.LOOP_ERROR,
            HookEvent.LOOP_STOPPED,
        ]

    def execute(self, event: HookEvent, **kwargs: Any) -> None:
        """Send notification via ntfy.sh."""
        if not self._enabled:
            return

        state: ExecutionState | None = kwargs.get("state")
        error: str | None = kwargs.get("error")

        title, message, priority, tags = self._build_notification(event, state, error)

        self._send(title, message, priority, tags)

    def _build_notification(
        self,
        event: HookEvent,
        state: ExecutionState | None,
        error: str | None,
    ) -> tuple[str, str, str, list[str]]:
        """Build notification content with iteration summary."""
        task_id = state.task_id if state else "unknown"
        iterations = state.current_iteration if state else 0

        # Build summary from iteration data
        summary = self._build_iteration_summary(state)

        if event == HookEvent.LOOP_COMPLETE:
            return (
                f"Task Completed: {task_id}",
                summary or f"Task {task_id} completed successfully after {iterations} iteration(s).",
                "default",
                ["white_check_mark", "robot"],
            )

        elif event == HookEvent.LOOP_FAILED:
            return (
                f"Task Failed: {task_id}",
                summary or f"Task {task_id} failed after {iterations} iteration(s).",
                "high",
                ["x", "warning"],
            )

        elif event == HookEvent.LOOP_ERROR:
            # Don't leak error details - just indicate an error occurred
            return (
                f"Task Error: {task_id}",
                f"An error occurred after {iterations} iteration(s). Check logs for details.",
                "urgent",
                ["warning", "rotating_light"],
            )

        elif event == HookEvent.LOOP_STOPPED:
            return (
                f"Task Stopped: {task_id}",
                summary or f"Task {task_id} was stopped after {iterations} iteration(s).",
                "default",
                ["pause_button", "warning"],
            )

        return (
            f"Task Update: {task_id}",
            summary or f"Event: {event.value}",
            "default",
            ["robot"],
        )

    def _build_iteration_summary(self, state: ExecutionState | None) -> str:
        """Build a safe summary with no sensitive information.

        Only includes generic status info - no output details, error messages,
        or fix info that could leak sensitive project information.
        """
        if not state or not state.iterations:
            return ""

        lines = []
        total_iterations = len(state.iterations)

        for iteration in state.iterations:
            phases_done = []
            phases_failed = []

            for step in iteration.steps:
                phase_name = step.phase.value.replace("_", " ").title()
                if step.status == StepStatus.COMPLETED:
                    phases_done.append(phase_name)
                elif step.status == StepStatus.FAILED:
                    phases_failed.append(phase_name)

            # Add iteration header if multiple iterations
            if total_iterations > 1:
                status = "PASS" if iteration.dod_achieved else "FAIL" if phases_failed else "..."
                lines.append(f"Iter {iteration.iteration}: {status}")

            # Just list phases without details
            if phases_done:
                lines.append(f"  Done: {', '.join(phases_done)}")
            if phases_failed:
                lines.append(f"  Failed: {', '.join(phases_failed)}")

        # Final status (generic)
        final_iter = state.iterations[-1]
        if final_iter.dod_achieved:
            lines.append("\nDoD: PASSED")
        elif final_iter.quality_passed:
            lines.append("\nQuality: PASSED")

        return "\n".join(lines)

    def _send(
        self,
        title: str,
        message: str,
        priority: str,
        tags: list[str],
    ) -> bool:
        """Send the notification to ntfy.sh."""
        url = f"{self._server}/{self._topic}"

        # Use ASCII-safe title to avoid encoding issues
        safe_title = title.encode("ascii", errors="replace").decode("ascii")

        headers = {
            "Title": safe_title,
            "Priority": priority,
            "Tags": ",".join(tags),
        }

        # Add authentication
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        elif self._user and self._password:
            credentials = f"{self._user}:{self._password}"
            encoded = base64.b64encode(credentials.encode()).decode("ascii")
            headers["Authorization"] = f"Basic {encoded}"

        try:
            req = urllib.request.Request(
                url,
                data=message.encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    logger.info(f"Notification sent: {title}")
                    return True
                else:
                    logger.warning(f"Notification failed with status: {response.status}")
                    return False

        except urllib.error.URLError as e:
            logger.error(f"Failed to send notification: {e}")
            return False
        except Exception as e:
            logger.error(f"Notification error: {e}")
            return False


class LoggingHook(Hook):
    """Hook that logs all events for debugging."""

    def __init__(self, log_level: int = logging.INFO):
        self._log_level = log_level

    @property
    def name(self) -> str:
        return "logging"

    def execute(self, event: HookEvent, **kwargs: Any) -> None:
        """Log the event."""
        state: ExecutionState | None = kwargs.get("state")
        task_id = state.task_id if state else "unknown"
        iteration = state.current_iteration if state else 0

        logger.log(
            self._log_level,
            f"[{task_id}] Event: {event.value} (iteration {iteration})",
        )
