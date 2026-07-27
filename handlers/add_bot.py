"""Handler flow for adding a new managed bot via its token."""

from __future__ import annotations

import logging

import aiosqlite
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot_manager import BotAPIClient, BotManager
from config import Config
from database import Database
from keyboards import MenuCallback, cancel_keyboard, main_menu_keyboard
from utils.helpers import IsAdmin, mask_token
from utils.validators import is_valid_token_format

router = Router(name="add_bot")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


class AddBotStates(StatesGroup):
    waiting_for_token = State()


@router.callback_query(MenuCallback.filter(F.action == "add"))
async def cb_add_bot_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Ask the admin to send the token of the bot they want to add."""
    await state.set_state(AddBotStates.waiting_for_token)
    if callback.message:
        await callback.message.edit_text(
            "🔑 توکن ربات موردنظر را ارسال کنید.\n\n"
            "توکن را می‌توانید از @BotFather دریافت کنید.",
            reply_markup=cancel_keyboard(),
        )
    await callback.answer()


@router.message(AddBotStates.waiting_for_token)
async def process_token(
    message: Message,
    state: FSMContext,
    database: Database,
    bot_manager: BotManager,
    config: Config,
    logger: logging.Logger,
) -> None:
    """Validate, verify and persist a new bot token."""
    token = (message.text or "").strip()

    if not is_valid_token_format(token):
        await message.answer(
            "❌ فرمت توکن نامعتبر است. لطفاً توکن صحیح را ارسال کنید یا لغو کنید.",
            reply_markup=cancel_keyboard(),
        )
        return

    if await database.token_exists(token):
        await message.answer(
            "⚠️ این ربات قبلاً در سیستم ثبت شده است.",
            reply_markup=cancel_keyboard(),
        )
        return

    status_message = await message.answer("⏳ در حال بررسی توکن با سرور تلگرام...")

    try:
        bot_info = await BotAPIClient.get_me(token)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to verify token via getMe: %s", exc)
        await status_message.edit_text(
            "❌ ارتباط با سرور تلگرام برقرار نشد. لطفاً دوباره تلاش کنید.",
            reply_markup=cancel_keyboard(),
        )
        return

    if bot_info is None:
        await status_message.edit_text(
            "❌ توکن نامعتبر است. تلگرام این توکن را نپذیرفت.",
            reply_markup=cancel_keyboard(),
        )
        return

    if await database.get_bot_by_bot_id(bot_info.bot_id) is not None:
        await status_message.edit_text(
            "⚠️ این ربات قبلاً در سیستم ثبت شده است.",
            reply_markup=cancel_keyboard(),
        )
        return

    try:
        record = await database.add_bot(
            bot_id=bot_info.bot_id,
            token=token,
            username=bot_info.username,
            first_name=bot_info.first_name,
            emoji=config.default_emoji,
        )
    except aiosqlite.IntegrityError:
        await status_message.edit_text(
            "⚠️ این ربات قبلاً در سیستم ثبت شده است.",
            reply_markup=cancel_keyboard(),
        )
        return

    started = await bot_manager.start_bot(record.bot_id, record.token, record.emoji)
    await database.add_log(
        "INFO",
        f"Bot @{record.username} added by admin {message.from_user.id if message.from_user else 'unknown'}.",
        bot_id=record.bot_id,
    )
    logger.info("Added new bot @%s (%s).", record.username, mask_token(record.token))

    await state.clear()
    start_note = "" if started else "\n⚠️ ربات ثبت شد اما راه‌اندازی خودکار آن ناموفق بود."
    await status_message.edit_text(
        "✅ ربات با موفقیت اضافه شد!\n\n"
        f"👤 نام: {record.first_name}\n"
        f"🔗 یوزرنیم: @{record.username}\n"
        f"😊 ایموجی ری‌اکشن پیش‌فرض: {record.emoji}"
        f"{start_note}",
        reply_markup=main_menu_keyboard(),
    )
