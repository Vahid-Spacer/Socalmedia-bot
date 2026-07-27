"""Miscellaneous helper utilities: formatting, masking and access filters."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Sequence

from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject

from config import Config


def mask_token(token: str) -> str:
    """Mask a bot token so it is safe to display in chat/logs.

    Example: ``123456789:AAExampleTokenValue`` -> ``123456789:AAEx...alue``

    Args:
        token: The full bot token.

    Returns:
        A masked representation revealing only a small, non-sensitive part.
    """
    if ":" not in token:
        return "***"
    bot_id_part, secret = token.split(":", 1)
    if len(secret) <= 8:
        masked_secret = "*" * len(secret)
    else:
        masked_secret = f"{secret[:4]}...{secret[-4:]}"
    return f"{bot_id_part}:{masked_secret}"


def format_datetime(value: str | datetime) -> str:
    """Format a datetime (or ISO string) into a human friendly string.

    Args:
        value: Either a ``datetime`` instance or an ISO-8601 formatted string.

    Returns:
        A string formatted as ``YYYY-MM-DD HH:MM``.
    """
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    return value.strftime("%Y-%m-%d %H:%M")


def utc_now_iso() -> str:
    """Return the current UTC time formatted as an ISO-8601 string."""
    return datetime.utcnow().isoformat(timespec="seconds")


def chunk(sequence: Sequence[Any], size: int) -> list[Sequence[Any]]:
    """Split a sequence into consecutive chunks of the given size.

    Args:
        sequence: The sequence to split.
        size: Maximum length of each chunk.

    Returns:
        A list of sub-sequences, each of length at most ``size``.
    """
    return [sequence[i : i + size] for i in range(0, len(sequence), size)]


class IsAdmin(BaseFilter):
    """Aiogram filter that only allows configured administrators through.

    ``config`` is resolved via aiogram's dependency injection (it is
    registered as workflow data in ``main.py``), so this filter can be
    attached to any router without needing the admin list at construction
    time.
    """

    async def __call__(self, event: TelegramObject, config: Config) -> bool:
        user = getattr(event, "from_user", None)
        return bool(user is not None and user.id in config.admin_ids)
