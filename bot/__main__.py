import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.config import get_settings
from bot.db import create_engine, create_session_factory
from bot.handlers import build_router


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    engine = create_engine(settings.database_url)
    # aiogram passes Dispatcher keyword arguments to handlers that ask for them by name.
    session_factory = create_session_factory(engine)

    bot = Bot(token=settings.bot_token.get_secret_value())
    dispatcher = Dispatcher(session_factory=session_factory)
    dispatcher.include_router(build_router())

    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
