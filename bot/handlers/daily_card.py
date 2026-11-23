import logging

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import clock, texts
from bot.config import BotSettings
from bot.daily_card_message import build_daily_card_message
from bot.db.models import DailyCardSource, User
from bot.services.daily_card import draw_daily_card
from bot.services.deck import get_card_content

logger = logging.getLogger(__name__)

router = Router(name="daily_card")


@router.message(F.text == texts.BUTTON_DAILY_CARD)
async def handle_daily_card(
    message: Message, session: AsyncSession, user: User, settings: BotSettings
) -> None:
    drawn = await draw_daily_card(
        session,
        user_id=user.id,
        issue_date=clock.today(settings.timezone),
        source=DailyCardSource.MANUAL,
    )
    if not drawn.is_new:
        await message.answer(texts.DAILY_CARD_ALREADY_DRAWN)
        return

    content = await get_card_content(
        session,
        deck_code=settings.default_deck_code,
        card_id=drawn.card.id,
        is_reversed=drawn.is_reversed,
    )
    if content is None:
        await session.rollback()  # do not count a card the user never saw
        logger.error(
            "No image or description for %s (reversed=%s) in deck %r",
            drawn.card.code,
            drawn.is_reversed,
            settings.default_deck_code,
        )
        await message.answer(texts.SOMETHING_WENT_WRONG)
        return

    reply = build_daily_card_message(drawn.card.name_ru, drawn.is_reversed, content.description)
    # If Telegram does not take the photo, the error propagates and the session closes
    # without a commit: the card is not issued, and the user can press the button again.
    await message.answer_photo(content.file_id, caption=reply.caption)
    await session.commit()
    if reply.rest:
        await message.answer(reply.rest)
