"""Issuing the card of the day: at most one per user per day."""

import random
import secrets
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Card, DailyCard, DailyCardSource

_random = secrets.SystemRandom()


@dataclass(frozen=True)
class DrawnCard:
    card: Card
    is_reversed: bool
    # False: the user already had a card for that day, and this is that card.
    is_new: bool


async def draw_daily_card(
    session: AsyncSession,
    *,
    user_id: int,
    issue_date: date,
    source: DailyCardSource,
    rng: random.Random = _random,
) -> DrawnCard:
    """Pick a random card and position for the day, or return the one already issued.

    The new card is only flushed, not committed: the caller commits once the user has it.
    Two simultaneous requests are safe: the second waits on the (user_id, issue_date)
    unique key and then gets the card the first one issued.
    """
    card_ids = list(await session.scalars(select(Card.id).order_by(Card.id)))
    card_id = rng.choice(card_ids)
    is_reversed = rng.random() < 0.5

    inserted = await session.scalar(
        insert(DailyCard)
        .values(
            user_id=user_id,
            issue_date=issue_date,
            card_id=card_id,
            is_reversed=is_reversed,
            source=source,
        )
        .on_conflict_do_nothing(index_elements=[DailyCard.user_id, DailyCard.issue_date])
        .returning(DailyCard.id)
    )
    if inserted is not None:
        return DrawnCard(await session.get_one(Card, card_id), is_reversed, is_new=True)

    existing = await session.scalar(
        select(DailyCard).where(DailyCard.user_id == user_id, DailyCard.issue_date == issue_date)
    )
    return DrawnCard(
        await session.get_one(Card, existing.card_id), existing.is_reversed, is_new=False
    )
