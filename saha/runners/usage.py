"""Helpers for normalizing token usage payloads from different runners."""

from typing import Any

_ALIAS_MAP: dict[str, list[str]] = {
    "input_tokens": ["input_tokens", "prompt_tokens", "prompt", "input"],
    "output_tokens": ["output_tokens", "completion_tokens", "completion", "output"],
    "cache_read_input_tokens": [
        "cache_read_input_tokens",
        "cache_read_tokens",
        "cached_tokens",
        "cache_read",
    ],
    "cache_write_input_tokens": [
        "cache_creation_input_tokens",
        "cache_write_input_tokens",
        "cache_creation",
        "cache_write",
    ],
    "reasoning_tokens": ["reasoning_tokens", "reasoning_output_tokens", "reasoning"],
    "total_tokens": ["total_tokens", "total_token_usage", "total"],
}


def normalize_token_usage(raw: dict[str, Any]) -> dict[str, int] | None:
    """Normalize raw usage payloads to a consistent schema."""
    result: dict[str, int] = {}

    for target, aliases in _ALIAS_MAP.items():
        for alias in aliases:
            value = raw.get(alias)
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                result[target] = int(value)
                break

    if not result:
        return None

    if "total_tokens" not in result:
        input_tokens = result.get("input_tokens", 0)
        output_tokens = result.get("output_tokens", 0)
        if input_tokens or output_tokens:
            result["total_tokens"] = input_tokens + output_tokens

    return result
