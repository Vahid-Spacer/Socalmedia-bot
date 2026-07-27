"""Runtime manager for the collection of child (managed) Telegram bots.

Each managed bot runs as its own ``aiogram.Bot`` + ``Dispatcher`` pair inside
an independent ``asyncio.Task``. The only behaviour the child bots implement
is reacting to incoming messages with a configurable emoji, which keeps the
scope well within Telegram's Bot API terms of service (no spam, no scraping,
no circumvention of platform limits).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError, TelegramUnauthorizedError
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, ReactionTypeEmoji

from database import Database


@dataclass(slots=True)
class BotInfo:
    """Metadata returned by a ``getMe`` call, used when adding a new bot."""

    bot_id: int
    username: str
    first_name: str


class BotAPIClient:
    """Thin helper around aiogram's ``Bot`` used purely for token verification."""

    @staticmethod
    async def get_me(token: str) -> BotInfo | None:
        """Verify a token via Telegram's ``getMe`` method.

        Args:
            token: The bot token to verify.

        Returns:
            ``BotInfo`` if the token is valid, ``None`` if Telegram rejects it.

        Raises:
            TelegramAPIError: For network/API errors other than an invalid token.
        """
        bot = Bot(token=token)
        try:
            me = await bot.get_me()
        except TelegramUnauthorizedError:
            return None
        finally:
            await bot.session.close()
        return BotInfo(bot_id=me.id, username=me.username or "", first_name=me.first_name)


def _build_reaction_router(emoji_holder: dict[str, str]) -> Router:
    """Build a router that reacts to every incoming message with an emoji.

    Args:
        emoji_holder: A mutable ``{"emoji": "..."}`` container so the emoji
            used by the running dispatcher can be updated live, without
            restarting the bot instance.
    """
    router = Router(name="child-bot-reaction")

    @router.message()
    async def react_to_message(message: Message) -> None:
        emoji = emoji_holder["emoji"]
        try:
            await message.bot.set_message_reaction(
                chat_id=message.chat.id,
                message_id=message.message_id,
                reaction=[ReactionTypeEmoji(emoji=emoji)],
            )
        except TelegramAPIError:
            # Reactions are best-effort (not every chat/message supports
            # them); failures here must never crash the child bot.
            pass

    return router


@dataclass(slots=True)
class RunningBot:
    """Bookkeeping for a live child-bot instance."""

    bot: Bot
    dispatcher: Dispatcher
    task: asyncio.Task
    emoji_holder: dict[str, str]


class BotManager:
    """Starts, stops and tracks all currently running child bot instances."""

    def __init__(self, database: Database, logger: logging.Logger) -> None:
        self._database = database
        self._logger = logger
        self._running: dict[int, RunningBot] = {}

    def is_running(self, bot_id: int) -> bool:
        return bot_id in self._running

    def running_count(self) -> int:
        return len(self._running)

    async def start_bot(self, bot_id: int, token: str, emoji: str) -> bool:
        """Start a child bot instance and begin polling for updates.

        Returns:
            True if the bot was started, False if it was already running.
        """
        if self.is_running(bot_id):
            return False

        bot = Bot(
            token=token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        dispatcher = Dispatcher(storage=MemoryStorage())
        emoji_holder = {"emoji": emoji}
        dispatcher.include_router(_build_reaction_router(emoji_holder))

        task = asyncio.create_task(
            self._run_polling_safely(bot_id, bot, dispatcher),
            name=f"child-bot-{bot_id}",
        )
        self._running[bot_id] = RunningBot(
            bot=bot, dispatcher=dispatcher, task=task, emoji_holder=emoji_holder
        )
        self._logger.info("Started child bot %s.", bot_id)
        return True

    async def _run_polling_safely(
        self, bot_id: int, bot: Bot, dispatcher: Dispatcher
    ) -> None:
        try:
            await dispatcher.start_polling(bot, handle_signals=False)
        except asyncio.CancelledError:
            raise
        except TelegramAPIError as exc:
            self._logger.error("Child bot %s stopped due to API error: %s", bot_id, exc)
            await self._database.add_log("ERROR", f"Polling error: {exc}", bot_id=bot_id)
        except Exception as exc:  # noqa: BLE001 - isolate failures per child bot
            self._logger.exception("Unexpected failure in child bot %s: %s", bot_id, exc)
            await self._database.add_log("ERROR", f"Unexpected error: {exc}", bot_id=bot_id)

    async def stop_bot(self, bot_id: int) -> bool:
        """Stop a running child bot instance and release its resources.

        Returns:
            True if a running bot was stopped, False if it was not running.
        """
        running = self._running.pop(bot_id, None)
        if running is None:
            return False

        running.task.cancel()
        try:
            await running.task
        except asyncio.CancelledError:
            pass
        finally:
            await running.bot.session.close()

        self._logger.info("Stopped child bot %s.", bot_id)
        return True

    async def update_emoji(self, bot_id: int, emoji: str) -> None:
        """Update the reaction emoji of a currently running bot in place."""
        running = self._running.get(bot_id)
        if running is not None:
            running.emoji_holder["emoji"] = emoji

    async def load_all_enabled(self) -> None:
        """Start every bot marked as enabled in the database (startup hook)."""
        bots = await self._database.get_enabled_bots()
        for bot in bots:
            try:
                await self.start_bot(bot.bot_id, bot.token, bot.emoji)
            except Exception as exc:  # noqa: BLE001
                self._logger.error(
                    "Failed to start bot %s (@%s) on startup: %s",
                    bot.bot_id,
                    bot.username,
                    exc,
                )

    async def stop_all(self) -> None:
        """Stop every currently running child bot (shutdown hook)."""
        for bot_id in list(self._running.keys()):
            await self.stop_bot(bot_id)
