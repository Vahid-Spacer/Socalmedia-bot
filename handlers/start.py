"""Handlers for the /start command and returning to the main menu."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import Config
from keyboards import MenuCallback, main_menu_keyboard

router = Router(name="start")

WELCOME_TEXT = (
    "👋 به پنل مدیریت ربات‌های تلگرام خوش آمدید.\n\n"
    "از منوی زیر یکی از گزینه‌ها را انتخاب کنید:"
)

ACCESS_DENIED_TEXT = "⛔ شما اجازه دسترسی به این پنل مدیریت را ندارید."


@router.message(Command("start"))
async def cmd_start(message: Message, config: Config, state: FSMContext) -> None:
    """Entry point. Shows the main menu to admins, rejects everyone else."""
    if not message.from_user or message.from_user.id not in config.admin_ids:
        await message.answer(ACCESS_DENIED_TEXT)
        return
    await state.clear()
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_keyboard())


@router.callback_query(MenuCallback.filter(F.action == "back"))
async def cb_back_to_menu(
    callback: CallbackQuery, config: Config, state: FSMContext
) -> None:
    """Return to the main menu from anywhere in the panel."""
    if not callback.from_user or callback.from_user.id not in config.admin_ids:
        await callback.answer(ACCESS_DENIED_TEXT, show_alert=True)
        return
    await state.clear()
    if callback.message:
        await callback.message.edit_text(WELCOME_TEXT, reply_markup=main_menu_keyboard())
    await callback.answer()
