from aiogram import Router

from bot.handlers import start


def build_router() -> Router:
    """Collect all handler routers into one root router."""
    router = Router(name="root")
    router.include_router(start.router)
    return router
