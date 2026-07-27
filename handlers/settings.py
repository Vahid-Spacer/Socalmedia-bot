"""Handlers for the settings menu and enabling/disabling a managed bot."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot_manager import BotManager
from database import Database
from keyboards import BotCallback, MenuCallback, bot_detail_keyboard, settings_menu_keyboard
from utils.helpers import IsAdmin

router = Router(name="settings")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.callback_query(MenuCallback.filter(F.action == "settings"))
async def cb_settings_menu(callback: CallbackQuery) -> None:
    """Show the top-level settings entry point."""
    if callback.message:
        await callback.message.edit_text(
            "⚙️ تنظیمات\n\nبرای تغییر تنظیمات یک ربات، ابتدا آن را از لیست انتخاب کنید.",
            reply_markup=settings_menu_keyboard(),
        )
    await callback.answer()


@router.callback_query(BotCallback.filter(F.action == "toggle"))
async def cb_toggle_bot(
    callback: CallbackQuery,
    callback_data: BotCallback,
    database: Database,
    bot_manager: BotManager,
    logger: logging.Logger,
) -> None:
    """Enable or disable a managed bot, starting/stopping its live instance."""
    bot = await database.get_bot_by_bot_id(callback_data.bot_id)
    if bot is None:
        await callback.answer("این ربات دیگر وجود ندارد.", show_alert=True)
        return

    new_enabled = not bot.enabled
    await database.set_bot_enabled(bot.bot_id, new_enabled)

    if new_enabled:
        await bot_manager.start_bot(bot.bot_id, bot.token, bot.emoji)
        action_text = "فعال"
    else:
        await bot_manager.stop_bot(bot.bot_id)
        action_text = "غیرفعال"

    await database.add_log(
        "INFO",
        f"Bot @{bot.username} set to {action_text} by admin "
        f"{callback.from_user.id if callback.from_user else 'unknown'}.",
        bot_id=bot.bot_id,
    )
    logger.info("Bot @%s toggled to %s.", bot.username, action_text)

    bot = await database.get_bot_by_bot_id(callback_data.bot_id)
    if bot is not None and callback.message:
        await callback.message.edit_text(
            f"✅ ربات @{bot.username} {action_text} شد.",
            reply_markup=bot_detail_keyboard(bot),
        )
    await callback.answer(f"ربات {action_text} شد.")
