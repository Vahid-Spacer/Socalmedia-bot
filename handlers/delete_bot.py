"""Handlers for safely deleting a managed bot (with confirmation)."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot_manager import BotManager
from database import Database
from keyboards import (
    BotCallback,
    ConfirmCallback,
    bot_detail_keyboard,
    confirm_delete_keyboard,
    main_menu_keyboard,
)
from utils.helpers import IsAdmin

router = Router(name="delete_bot")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.callback_query(BotCallback.filter(F.action == "delete"))
async def cb_delete_bot_confirm(
    callback: CallbackQuery, callback_data: BotCallback, database: Database
) -> None:
    """Ask the admin to confirm deletion before removing a bot."""
    bot = await database.get_bot_by_bot_id(callback_data.bot_id)
    if bot is None:
        await callback.answer("این ربات دیگر وجود ندارد.", show_alert=True)
        return

    if callback.message:
        await callback.message.edit_text(
            f"⚠️ آیا از حذف ربات @{bot.username} مطمئن هستید؟\n"
            "این عملیات غیرقابل بازگشت است.",
            reply_markup=confirm_delete_keyboard(bot.bot_id),
        )
    await callback.answer()


@router.callback_query(ConfirmCallback.filter(F.action == "delete_yes"))
async def cb_delete_bot_execute(
    callback: CallbackQuery,
    callback_data: ConfirmCallback,
    database: Database,
    bot_manager: BotManager,
    logger: logging.Logger,
) -> None:
    """Actually remove the bot from the database and stop its instance."""
    bot = await database.get_bot_by_bot_id(callback_data.bot_id)
    if bot is None:
        await callback.answer("این ربات قبلاً حذف شده است.", show_alert=True)
        return

    await bot_manager.stop_bot(bot.bot_id)
    await database.delete_bot(bot.bot_id)
    await database.add_log(
        "INFO",
        f"Bot @{bot.username} deleted by admin "
        f"{callback.from_user.id if callback.from_user else 'unknown'}.",
        bot_id=bot.bot_id,
    )
    logger.info("Deleted bot @%s (id=%s).", bot.username, bot.bot_id)

    if callback.message:
        await callback.message.edit_text(
            f"🗑️ ربات @{bot.username} با موفقیت حذف شد.",
            reply_markup=main_menu_keyboard(),
        )
    await callback.answer()


@router.callback_query(ConfirmCallback.filter(F.action == "delete_no"))
async def cb_delete_bot_cancel(
    callback: CallbackQuery, callback_data: ConfirmCallback, database: Database
) -> None:
    """Cancel the deletion and return to the bot's detail page."""
    bot = await database.get_bot_by_bot_id(callback_data.bot_id)
    if bot is None:
        await callback.answer("این ربات دیگر وجود ندارد.", show_alert=True)
        return

    if callback.message:
        await callback.message.edit_text(
            "عملیات حذف لغو شد.", reply_markup=bot_detail_keyboard(bot)
        )
    await callback.answer()
