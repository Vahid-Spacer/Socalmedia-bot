"""Handlers package: aggregates every router used by the management bot."""

from __future__ import annotations

from aiogram import Router

from handlers.add_bot import router as add_bot_router
from handlers.delete_bot import router as delete_bot_router
from handlers.list_bots import router as list_bots_router
from handlers.reaction import router as reaction_router
from handlers.settings import router as settings_router
from handlers.start import router as start_router


def get_routers() -> list[Router]:
    """Return every router that must be included in the main dispatcher.

    Order matters only where callback filters could overlap; here each
    router uses distinct callback-data prefixes/actions so registration
    order is not significant.
    """
    return [
        start_router,
        add_bot_router,
        list_bots_router,
        delete_bot_router,
        settings_router,
        reaction_router,
    ]
