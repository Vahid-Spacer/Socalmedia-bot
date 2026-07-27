"""Async SQLite data access layer for the bot manager.

All database access goes through the ``Database`` class, which owns the
connection lifecycle and exposes typed, purpose-specific methods so that
handlers never write raw SQL themselves.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import aiosqlite

from utils.helpers import utc_now_iso

_CREATE_BOTS_TABLE = """
CREATE TABLE IF NOT EXISTS bots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_id INTEGER UNIQUE NOT NULL,
    token TEXT UNIQUE NOT NULL,
    username TEXT NOT NULL,
    first_name TEXT NOT NULL,
    emoji TEXT NOT NULL DEFAULT '👍',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);
"""

_CREATE_SETTINGS_TABLE = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

_CREATE_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    bot_id INTEGER,
    created_at TEXT NOT NULL
);
"""


@dataclass(slots=True)
class BotRecord:
    """A single managed bot row from the ``bots`` table."""

    id: int
    bot_id: int
    token: str
    username: str
    first_name: str
    emoji: str
    enabled: bool
    created_at: str

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "BotRecord":
        return cls(
            id=row["id"],
            bot_id=row["bot_id"],
            token=row["token"],
            username=row["username"],
            first_name=row["first_name"],
            emoji=row["emoji"],
            enabled=bool(row["enabled"]),
            created_at=row["created_at"],
        )


class Database:
    """Owns the SQLite connection and provides typed CRUD operations."""

    def __init__(self, db_path: str, logger: logging.Logger) -> None:
        self._db_path = db_path
        self._logger = logger
        self._connection: aiosqlite.Connection | None = None

    @property
    def connection(self) -> aiosqlite.Connection:
        if self._connection is None:
            raise RuntimeError("Database is not initialized. Call connect() first.")
        return self._connection

    async def connect(self) -> None:
        """Open the database connection and ensure the schema exists."""
        self._connection = await aiosqlite.connect(self._db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._connection.execute("PRAGMA foreign_keys = ON;")
        await self._create_schema()
        self._logger.info("Database connected at '%s'.", self._db_path)

    async def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
            self._logger.info("Database connection closed.")

    async def _create_schema(self) -> None:
        await self.connection.execute(_CREATE_BOTS_TABLE)
        await self.connection.execute(_CREATE_SETTINGS_TABLE)
        await self.connection.execute(_CREATE_LOGS_TABLE)
        await self.connection.commit()

    # ------------------------------------------------------------------ #
    # Bots
    # ------------------------------------------------------------------ #

    async def add_bot(
        self,
        bot_id: int,
        token: str,
        username: str,
        first_name: str,
        emoji: str,
    ) -> BotRecord:
        """Insert a new managed bot row.

        Raises:
            aiosqlite.IntegrityError: If ``bot_id`` or ``token`` already exist.
        """
        created_at = utc_now_iso()
        cursor = await self.connection.execute(
            """
            INSERT INTO bots (bot_id, token, username, first_name, emoji, enabled, created_at)
            VALUES (?, ?, ?, ?, ?, 1, ?)
            """,
            (bot_id, token, username, first_name, emoji, created_at),
        )
        await self.connection.commit()
        row_id = cursor.lastrowid
        record = await self.get_bot_by_row_id(row_id)
        assert record is not None
        return record

    async def get_bot_by_row_id(self, row_id: int) -> BotRecord | None:
        cursor = await self.connection.execute(
            "SELECT * FROM bots WHERE id = ?", (row_id,)
        )
        row = await cursor.fetchone()
        return BotRecord.from_row(row) if row else None

    async def get_bot_by_bot_id(self, bot_id: int) -> BotRecord | None:
        cursor = await self.connection.execute(
            "SELECT * FROM bots WHERE bot_id = ?", (bot_id,)
        )
        row = await cursor.fetchone()
        return BotRecord.from_row(row) if row else None

    async def get_bot_by_token(self, token: str) -> BotRecord | None:
        cursor = await self.connection.execute(
            "SELECT * FROM bots WHERE token = ?", (token,)
        )
        row = await cursor.fetchone()
        return BotRecord.from_row(row) if row else None

    async def token_exists(self, token: str) -> bool:
        return await self.get_bot_by_token(token) is not None

    async def get_all_bots(self) -> list[BotRecord]:
        cursor = await self.connection.execute(
            "SELECT * FROM bots ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [BotRecord.from_row(row) for row in rows]

    async def get_enabled_bots(self) -> list[BotRecord]:
        cursor = await self.connection.execute(
            "SELECT * FROM bots WHERE enabled = 1 ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [BotRecord.from_row(row) for row in rows]

    async def set_bot_enabled(self, bot_id: int, enabled: bool) -> None:
        await self.connection.execute(
            "UPDATE bots SET enabled = ? WHERE bot_id = ?", (int(enabled), bot_id)
        )
        await self.connection.commit()

    async def set_bot_emoji(self, bot_id: int, emoji: str) -> None:
        await self.connection.execute(
            "UPDATE bots SET emoji = ? WHERE bot_id = ?", (emoji, bot_id)
        )
        await self.connection.commit()

    async def delete_bot(self, bot_id: int) -> None:
        await self.connection.execute("DELETE FROM bots WHERE bot_id = ?", (bot_id,))
        await self.connection.commit()

    # ------------------------------------------------------------------ #
    # Settings (simple global key/value store)
    # ------------------------------------------------------------------ #

    async def get_setting(self, key: str) -> str | None:
        cursor = await self.connection.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        )
        row = await cursor.fetchone()
        return row["value"] if row else None

    async def set_setting(self, key: str, value: str) -> None:
        await self.connection.execute(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        await self.connection.commit()

    # ------------------------------------------------------------------ #
    # Logs (persisted audit trail, separate from file logging)
    # ------------------------------------------------------------------ #

    async def add_log(
        self, level: str, message: str, bot_id: int | None = None
    ) -> None:
        await self.connection.execute(
            "INSERT INTO logs (level, message, bot_id, created_at) VALUES (?, ?, ?, ?)",
            (level, message, bot_id, utc_now_iso()),
        )
        await self.connection.commit()

    async def get_recent_logs(self, limit: int = 20) -> list[dict[str, Any]]:
        cursor = await self.connection.execute(
            "SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
