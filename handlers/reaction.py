"""Handler flow for changing a managed bot's reaction emoji."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot_manager import BotManager
from database import Database
from keyboards import BotCallback, bot_detail_keyboard, cancel_keyboard
from utils.helpers import IsAdmin
from utils.validators import is_valid_emoji

router = Router(name="reaction")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


class ReactionStates(StatesGroup):
    waiting_for_emoji = State()


@router.callback_query(BotCallback.filter(F.action == "emoji"))
async def cb_change_emoji_start(
    callback: CallbackQuery,
    callback_data: BotCallback,
    database: Database,
    state: FSMContext,
) -> None:
    """Ask the admin to send the new reaction emoji for a bot."""
    bot = await database.get_bot_by_bot_id(callback_data.bot_id)
    if bot is None:
        await callback.answer("این ربات دیگر وجود ندارد.", show_alert=True)
        return

    await state.set_state(ReactionStates.waiting_for_emoji)
    await state.update_data(bot_id=bot.bot_id)

    if callback.message:
        await callback.message.edit_text(
            f"😊 ایموجی ری‌اکشن جدید برای @{bot.username} را ارسال کنید.\n\n"
            f"ایموجی فعلی: {bot.emoji}",
            reply_markup=cancel_keyboard(),
        )
    await callback.answer()


@router.message(ReactionStates.waiting_for_emoji)
async def process_new_emoji(
    message: Message,
    state: FSMContext,
    database: Database,
    bot_manager: BotManager,
    logger: logging.Logger,
) -> None:
    """Validate and persist the new reaction emoji, updating the live instance."""
    data = await state.get_data()
    bot_id = data.get("bot_id")
    emoji = (message.text or "").strip()

    if bot_id is None:
        await state.clear()
        await message.answer("خطای داخلی رخ داد. لطفاً دوباره از منو شروع کنید.")
        return

    if not is_valid_emoji(emoji):
        await message.answer(
            "❌ لطفاً فقط یک ایموجی معتبر ارسال کنید.",
            reply_markup=cancel_keyboard(),
        )
        return

    bot = await database.get_bot_by_bot_id(bot_id)
    if bot is None:
        await state.clear()
        await message.answer("⚠️ این ربات دیگر وجود ندارد.")
        return

    await database.set_bot_emoji(bot_id, emoji)
    await bot_manager.update_emoji(bot_id, emoji)
    await database.add_log(
        "INFO",
        f"Reaction emoji for @{bot.username} changed to {emoji} by admin "
        f"{message.from_user.id if message.from_user else 'unknown'}.",
        bot_id=bot_id,
    )
    logger.info("Emoji for bot @%s updated to %s.", bot.username, emoji)

    await state.clear()
    bot = await database.get_bot_by_bot_id(bot_id)
    if bot is not None:
        await message.answer(
            f"✅ ایموجی ری‌اکشن @{bot.username} به {emoji} تغییر کرد.",
            reply_markup=bot_detail_keyboard(bot),
        )
