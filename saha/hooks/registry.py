"""Hook registry for managing and triggering hooks."""

import logging
from typing import Any

from saha.hooks.base import Hook, HookEvent

logger = logging.getLogger(__name__)


class HookRegistry:
    """Registry for managing hooks."""

    def __init__(self) -> None:
        self._hooks: list[Hook] = []

    def register(self, hook: Hook) -> None:
        """Register a hook."""
        self._hooks.append(hook)
        logger.debug(f"Registered hook: {hook.name}")

    def unregister(self, hook_name: str) -> bool:
        """Unregister a hook by name."""
        for i, hook in enumerate(self._hooks):
            if hook.name == hook_name:
                del self._hooks[i]
                logger.debug(f"Unregistered hook: {hook_name}")
                return True
        return False

    def trigger(self, event: str | HookEvent, **kwargs: Any) -> None:
        """Trigger all hooks listening to an event.

        Args:
            event: Event name or HookEvent enum.
            **kwargs: Event-specific data to pass to hooks.
        """
        if isinstance(event, str):
            try:
                event = HookEvent(event)
            except ValueError:
                logger.warning(f"Unknown event: {event}")
                return

        for hook in self._hooks:
            if hook.should_trigger(event):
                try:
                    hook.execute(event, **kwargs)
                except Exception as e:
                    logger.error(f"Hook {hook.name} failed for event {event}: {e}")

    def list_hooks(self) -> list[str]:
        """List all registered hook names."""
        return [hook.name for hook in self._hooks]

    def clear(self) -> None:
        """Clear all registered hooks."""
        self._hooks.clear()
