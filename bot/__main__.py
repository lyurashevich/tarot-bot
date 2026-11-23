import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.bot_profile import update_bot_profile
from bot.config import get_bot_settings, get_database_settings
from bot.db import create_engine, create_session_factory
from bot.handlers import build_router
from bot.middlewares import DbSessionMiddleware, UserMiddleware
from bot.services.deck import find_missing_content

logger = logging.getLogger(__name__)


async def warn_about_missing_content(
    session_factory: async_sessionmaker[AsyncSession], deck_code: str
) -> None:
    async with session_factory() as session:
        missing = await find_missing_content(session, deck_code)
    if missing.images:
        logger.warning(
            "Deck %r lacks %d card images: run scripts/import_deck.py", deck_code, missing.images
        )
    if missing.descriptions:
        logger.warning(
            "%d card descriptions are missing: run scripts/generate_descriptions.py",
            missing.descriptions,
        )


async def main() -> None:
    settings = get_bot_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    engine = create_engine(get_database_settings().url)
    session_factory = create_session_factory(engine)

    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    # Workflow data: handlers can ask for `settings` as an argument.
    dispatcher = Dispatcher(settings=settings)
    # Outer middlewares run for every update, in this order: session first, then the user.
    dispatcher.update.outer_middleware(DbSessionMiddleware(session_factory))
    dispatcher.update.outer_middleware(UserMiddleware())
    dispatcher.include_router(build_router())

    try:
        await warn_about_missing_content(session_factory, settings.default_deck_code)
        await update_bot_profile(bot)
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
