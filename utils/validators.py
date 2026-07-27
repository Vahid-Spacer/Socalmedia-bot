"""Input validation helpers used across the bot manager."""

from __future__ import annotations

import re

_TOKEN_PATTERN = re.compile(r"^\d{6,10}:[A-Za-z0-9_-]{30,45}$")

# A reasonable upper bound for a single (possibly multi-codepoint) emoji.
_MAX_EMOJI_LENGTH = 8


def is_valid_token_format(token: str) -> bool:
    """Check whether a string has the structural shape of a Telegram bot token.

    This performs a purely structural check (``<digits>:<35 char secret>``);
    it does NOT verify the token is real. Use ``BotAPIClient.get_me`` for that.

    Args:
        token: The raw token string to validate.

    Returns:
        True if the token matches the expected structural pattern.
    """
    if not token:
        return False
    return bool(_TOKEN_PATTERN.match(token.strip()))


def is_valid_emoji(value: str) -> bool:
    """Check whether the given string looks like a single emoji.

    Args:
        value: The candidate emoji string.

    Returns:
        True if the value is non-empty, short, and contains no plain
        alphanumeric ASCII characters (which would indicate it is not
        an emoji but regular text).
    """
    value = value.strip()
    if not value:
        return False
    if len(value) > _MAX_EMOJI_LENGTH:
        return False
    if any(ch.isascii() and ch.isalnum() for ch in value):
        return False
    return True


def sanitize_text(value: str, max_length: int = 256) -> str:
    """Strip and truncate arbitrary user-provided text for safe storage/display.

    Args:
        value: Raw input text.
        max_length: Maximum number of characters to keep.

    Returns:
        A trimmed, length-limited version of the input.
    """
    return value.strip()[:max_length]


def is_valid_telegram_user_id(value: str) -> bool:
    """Check whether a string represents a valid positive Telegram user id."""
    return value.strip().lstrip("-").isdigit()
