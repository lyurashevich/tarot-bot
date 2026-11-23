from aiogram import Router

from bot.handlers import daily_card, menu, start


def build_router() -> Router:
    """Collect all handler routers into one root router."""
    router = Router(name="root")
    router.include_router(start.router)
    router.include_router(daily_card.router)
    # Last: its catch-all handler answers any message the routers above did not handle.
    router.include_router(menu.router)
    return router
