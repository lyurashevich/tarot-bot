"""Card images and pre-generated descriptions."""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Card, CardDescription, Deck, DeckCardImage


@dataclass(frozen=True)
class CardContent:
    file_id: str
    description: str


async def get_card_content(
    session: AsyncSession, *, deck_code: str, card_id: int, is_reversed: bool
) -> CardContent | None:
    """The card's image in the deck and its description; None if either is missing."""
    file_id_column = (
        DeckCardImage.file_id_reversed if is_reversed else DeckCardImage.file_id_upright
    )
    row = (
        await session.execute(
            select(file_id_column, CardDescription.text)
            .select_from(DeckCardImage)
            .join(Deck, Deck.id == DeckCardImage.deck_id)
            .join(
                CardDescription,
                (CardDescription.card_id == DeckCardImage.card_id)
                & (CardDescription.is_reversed == is_reversed),
            )
            .where(Deck.code == deck_code, DeckCardImage.card_id == card_id)
        )
    ).first()
    return CardContent(file_id=row[0], description=row[1]) if row else None


@dataclass(frozen=True)
class MissingContent:
    images: int
    descriptions: int


async def find_missing_content(session: AsyncSession, deck_code: str) -> MissingContent:
    """How many card images (in the deck) and descriptions are missing."""
    cards = await session.scalar(select(func.count()).select_from(Card))
    images = await session.scalar(
        select(func.count())
        .select_from(DeckCardImage)
        .join(Deck, Deck.id == DeckCardImage.deck_id)
        .where(Deck.code == deck_code)
    )
    descriptions = await session.scalar(select(func.count()).select_from(CardDescription))
    return MissingContent(images=cards - images, descriptions=cards * 2 - descriptions)
