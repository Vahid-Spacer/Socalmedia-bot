"""Entry point for the Telegram Bot Manager.

Wires together configuration, database, logging, the bot manager runtime
and the management bot's dispatcher, then runs everything with asyncio.
"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot_manager import BotManager
from config import config
from database import Database
from handlers import get_routers
from utils.logger import setup_logger


async def run() -> None:
    """Configure and run the management bot until interrupted."""
    logger: logging.Logger = setup_logger("bot_manager", log_dir=config.log_dir)
    logger.info("Starting Telegram Bot Manager...")

    database = Database(db_path=config.db_path, logger=logger)
    await database.connect()

    bot_manager = BotManager(database=database, logger=logger)

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher(storage=MemoryStorage())

    for router in get_routers():
        dispatcher.include_router(router)

    try:
        await bot_manager.load_all_enabled()
        logger.info(
            "Startup complete. %d managed bot(s) running.",
            bot_manager.running_count(),
        )
        await dispatcher.start_polling(
            bot,
            database=database,
            bot_manager=bot_manager,
            config=config,
            logger=logger,
        )
    finally:
        logger.info("Shutting down...")
        await bot_manager.stop_all()
        await bot.session.close()
        await database.close()
        logger.info("Shutdown complete.")


def main() -> None:
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()
