"""Application configuration loaded from environment variables (.env)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


class ConfigError(Exception):
    """Raised when the configuration is invalid or incomplete."""


@dataclass(frozen=True, slots=True)
class Config:
    """Immutable application configuration.

    Attributes:
        bot_token: Token of the main management bot.
        admin_ids: Telegram user IDs allowed to use the management panel.
        db_path: Path to the SQLite database file.
        log_dir: Directory where log files are written.
        default_emoji: Default reaction emoji assigned to newly added bots.
    """

    bot_token: str
    admin_ids: list[int] = field(default_factory=list)
    db_path: str = "data.db"
    log_dir: str = "logs"
    default_emoji: str = "👍"


def _parse_admin_ids(raw: str) -> list[int]:
    """Parse a comma separated string of admin IDs into a list of integers."""
    ids: list[int] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if not chunk.lstrip("-").isdigit():
            raise ConfigError(f"Invalid admin id in ADMIN_IDS: '{chunk}'")
        ids.append(int(chunk))
    return ids


def load_config() -> Config:
    """Load and validate configuration from environment variables.

    Raises:
        ConfigError: If required variables are missing or malformed.
    """
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise ConfigError(
            "BOT_TOKEN is not set. Create a .env file based on .env.example "
            "and provide the token of your main management bot."
        )

    admin_ids_raw = os.getenv("ADMIN_IDS", "")
    admin_ids = _parse_admin_ids(admin_ids_raw)
    if not admin_ids:
        raise ConfigError(
            "ADMIN_IDS is not set. Provide at least one Telegram user id "
            "(comma separated) that is allowed to control the bot manager."
        )

    db_path = os.getenv("DB_PATH", "data.db").strip() or "data.db"
    log_dir = os.getenv("LOG_DIR", "logs").strip() or "logs"
    default_emoji = os.getenv("DEFAULT_EMOJI", "👍").strip() or "👍"

    return Config(
        bot_token=bot_token,
        admin_ids=admin_ids,
        db_path=db_path,
        log_dir=log_dir,
        default_emoji=default_emoji,
    )


config: Config = load_config()
