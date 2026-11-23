"""All models, imported here so that Base.metadata (and Alembic) knows every table."""

from bot.db.models.cards import Arcana, Card, CardDescription, Deck, DeckCardImage, Suit
from bot.db.models.daily_cards import DailyCard, DailyCardSource
from bot.db.models.users import User

__all__ = [
    "Arcana",
    "Card",
    "CardDescription",
    "DailyCard",
    "DailyCardSource",
    "Deck",
    "DeckCardImage",
    "Suit",
    "User",
]
