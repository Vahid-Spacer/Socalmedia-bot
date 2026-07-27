"""Inline keyboard builders and typed callback-data factories."""

from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import BotRecord


class MenuCallback(CallbackData, prefix="menu"):
    """Callback data for the main-menu buttons."""

    action: str  # add | list | settings | back


class BotCallback(CallbackData, prefix="bot"):
    """Callback data for actions targeting a specific managed bot."""

    action: str  # view | toggle | emoji | delete
    bot_id: int


class ConfirmCallback(CallbackData, prefix="confirm"):
    """Callback data for a yes/no confirmation step."""

    action: str  # delete_yes | delete_no
    bot_id: int


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Build the root management panel menu."""
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ افزودن ربات", callback_data=MenuCallback(action="add"))
    builder.button(text="📋 لیست ربات‌ها", callback_data=MenuCallback(action="list"))
    builder.button(text="⚙️ تنظیمات", callback_data=MenuCallback(action="settings"))
    builder.adjust(1)
    return builder.as_markup()


def cancel_keyboard() -> InlineKeyboardMarkup:
    """Build a single 'cancel current operation' keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ لغو و بازگشت", callback_data=MenuCallback(action="back"))
    return builder.as_markup()


def bots_list_keyboard(bots: list[BotRecord]) -> InlineKeyboardMarkup:
    """Build a keyboard listing every managed bot, one button per row."""
    builder = InlineKeyboardBuilder()
    for bot in bots:
        status_icon = "✅" if bot.enabled else "🚫"
        builder.button(
            text=f"{status_icon} @{bot.username}",
            callback_data=BotCallback(action="view", bot_id=bot.bot_id),
        )
    builder.button(text="⬅️ بازگشت", callback_data=MenuCallback(action="back"))
    builder.adjust(1)
    return builder.as_markup()


def bot_detail_keyboard(bot: BotRecord) -> InlineKeyboardMarkup:
    """Build the detail/settings keyboard for a single managed bot."""
    toggle_text = "🚫 غیرفعال کردن" if bot.enabled else "✅ فعال کردن"
    builder = InlineKeyboardBuilder()
    builder.button(
        text=toggle_text,
        callback_data=BotCallback(action="toggle", bot_id=bot.bot_id),
    )
    builder.button(
        text="😊 تغییر ایموجی ری‌اکشن",
        callback_data=BotCallback(action="emoji", bot_id=bot.bot_id),
    )
    builder.button(
        text="❌ حذف ربات",
        callback_data=BotCallback(action="delete", bot_id=bot.bot_id),
    )
    builder.button(text="⬅️ بازگشت به لیست", callback_data=MenuCallback(action="list"))
    builder.adjust(1)
    return builder.as_markup()


def confirm_delete_keyboard(bot_id: int) -> InlineKeyboardMarkup:
    """Build a yes/no confirmation keyboard for bot deletion."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ بله، حذف کن",
        callback_data=ConfirmCallback(action="delete_yes", bot_id=bot_id),
    )
    builder.button(
        text="❌ انصراف",
        callback_data=ConfirmCallback(action="delete_no", bot_id=bot_id),
    )
    builder.adjust(2)
    return builder.as_markup()


def settings_menu_keyboard() -> InlineKeyboardMarkup:
    """Build the top-level settings menu (choose a bot to configure)."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 انتخاب ربات برای تنظیمات", callback_data=MenuCallback(action="list"))
    builder.button(text="⬅️ بازگشت", callback_data=MenuCallback(action="back"))
    builder.adjust(1)
    return builder.as_markup()
