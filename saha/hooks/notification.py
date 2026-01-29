"""Notification hooks using ntfy.sh."""

import logging
import urllib.error
import urllib.request
from typing import Any

from saha.hooks.base import Hook, HookEvent
from saha.models.state import ExecutionState

logger = logging.getLogger(__name__)


class NtfyHook(Hook):
    """Hook that sends notifications via ntfy.sh."""

    def __init__(
        self,
        topic: str,
        server: str = "https://ntfy.sh",
        enabled: bool = True,
    ):
        self._topic = topic
        self._server = server.rstrip("/")
        self._enabled = enabled

    @property
    def name(self) -> str:
        return "ntfy"

    @property
    def events(self) -> list[HookEvent]:
        """Only trigger on completion/failure events."""
        return [
            HookEvent.LOOP_COMPLETE,
            HookEvent.LOOP_FAILED,
            HookEvent.LOOP_ERROR,
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
        """Build notification content based on event."""
        task_id = state.task_id if state else "unknown"
        iterations = state.current_iteration if state else 0

        if event == HookEvent.LOOP_COMPLETE:
            return (
                f"✅ Task Completed: {task_id}",
                f"Task {task_id} completed successfully after {iterations} iteration(s).",
                "default",
                ["white_check_mark", "robot"],
            )

        elif event == HookEvent.LOOP_FAILED:
            return (
                f"❌ Task Failed: {task_id}",
                f"Task {task_id} failed after {iterations} iteration(s).",
                "high",
                ["x", "warning"],
            )

        elif event == HookEvent.LOOP_ERROR:
            error_msg = error[:200] if error else "Unknown error"
            return (
                f"⚠️ Task Error: {task_id}",
                f"Task {task_id} encountered an error: {error_msg}",
                "urgent",
                ["warning", "rotating_light"],
            )

        return (
            f"Task Update: {task_id}",
            f"Event: {event.value}",
            "default",
            ["robot"],
        )

    def _send(
        self,
        title: str,
        message: str,
        priority: str,
        tags: list[str],
    ) -> bool:
        """Send the notification to ntfy.sh."""
        url = f"{self._server}/{self._topic}"

        headers = {
            "Title": title,
            "Priority": priority,
            "Tags": ",".join(tags),
        }

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
