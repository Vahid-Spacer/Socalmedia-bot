"""Handlers for listing managed bots and viewing a single bot's detail page."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot_manager import BotManager
from database import Database
from keyboards import (
    BotCallback,
    MenuCallback,
    bot_detail_keyboard,
    bots_list_keyboard,
    main_menu_keyboard,
)
from utils.helpers import IsAdmin, format_datetime, mask_token

router = Router(name="list_bots")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


def _bot_detail_text(bot, running: bool) -> str:
    status = "✅ فعال" if bot.enabled else "🚫 غیرفعال"
    runtime = "🟢 در حال اجرا" if running else "🔴 متوقف"
    return (
        f"🤖 <b>{bot.first_name}</b> (@{bot.username})\n\n"
        f"🆔 شناسه: <code>{bot.bot_id}</code>\n"
        f"🔑 توکن: <code>{mask_token(bot.token)}</code>\n"
        f"📌 وضعیت: {status}\n"
        f"⚙️ اجرا: {runtime}\n"
        f"😊 ایموجی ری‌اکشن: {bot.emoji}\n"
        f"📅 تاریخ افزودن: {format_datetime(bot.created_at)}"
    )


@router.callback_query(MenuCallback.filter(F.action == "list"))
async def cb_list_bots(callback: CallbackQuery, database: Database) -> None:
    """Show the list of every managed bot."""
    bots = await database.get_all_bots()
    if not bots:
        text = "📭 هنوز هیچ رباتی اضافه نشده است."
        markup = main_menu_keyboard()
    else:
        text = f"📋 لیست ربات‌های مدیریت‌شده ({len(bots)} ربات):"
        markup = bots_list_keyboard(bots)

    if callback.message:
        await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


@router.callback_query(BotCallback.filter(F.action == "view"))
async def cb_view_bot(
    callback: CallbackQuery,
    callback_data: BotCallback,
    database: Database,
    bot_manager: BotManager,
) -> None:
    """Show detail/settings for a single managed bot."""
    bot = await database.get_bot_by_bot_id(callback_data.bot_id)
    if bot is None:
        await callback.answer("این ربات دیگر وجود ندارد.", show_alert=True)
        return

    running = bot_manager.is_running(bot.bot_id)
    if callback.message:
        await callback.message.edit_text(
            _bot_detail_text(bot, running), reply_markup=bot_detail_keyboard(bot)
        )
    await callback.answer()
