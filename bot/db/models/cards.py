from enum import StrEnum

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base
from bot.db.models.mixins import CreatedAtMixin, str_enum


class Arcana(StrEnum):
    MAJOR = "major"
    MINOR = "minor"


class Suit(StrEnum):
    WANDS = "wands"
    CUPS = "cups"
    SWORDS = "swords"
    PENTACLES = "pentacles"


class Card(Base):
    """One of the 78 tarot cards. Its meaning does not depend on the deck."""

    __tablename__ = "cards"
    __table_args__ = (
        CheckConstraint(
            "(arcana = 'major' AND suit IS NULL) OR (arcana = 'minor' AND suit IS NOT NULL)",
            name="suit_matches_arcana",
        ),
        # Major: 0 (the Fool) .. 21 (the World).
        # Minor: 1 (ace) .. 10, 11 page, 12 knight, 13 queen, 14 king.
        CheckConstraint(
            "(arcana = 'major' AND number BETWEEN 0 AND 21)"
            " OR (arcana = 'minor' AND number BETWEEN 1 AND 14)",
            name="number_in_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Stable identifier used by seed data and image files, e.g. "major_00", "cups_14".
    code: Mapped[str] = mapped_column(String, unique=True)
    name_ru: Mapped[str] = mapped_column(String)
    arcana: Mapped[Arcana] = mapped_column(str_enum(Arcana, "arcana"))
    suit: Mapped[Suit | None] = mapped_column(str_enum(Suit, "suit"))
    number: Mapped[int] = mapped_column(SmallInteger)


class Deck(Base):
    __tablename__ = "decks"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String)


class DeckCardImage(Base):
    """The picture of a card in a particular deck, stored on Telegram's servers.

    The images are uploaded once by scripts/import_deck.py to the storage channel.
    Telegram file_ids belong to one bot: after a bot token change, run the import again.
    """

    __tablename__ = "deck_card_images"

    deck_id: Mapped[int] = mapped_column(
        ForeignKey("decks.id", ondelete="CASCADE"), primary_key=True
    )
    card_id: Mapped[int] = mapped_column(
        ForeignKey("cards.id", ondelete="CASCADE"), primary_key=True
    )
    file_id_upright: Mapped[str] = mapped_column(String)
    file_id_reversed: Mapped[str] = mapped_column(String)


class CardDescription(CreatedAtMixin, Base):
    """Pre-generated AI text for the card of the day, one per card and position.

    Generated once by scripts/generate_descriptions.py; the meaning does not depend on the deck.
    """

    __tablename__ = "card_descriptions"

    card_id: Mapped[int] = mapped_column(
        ForeignKey("cards.id", ondelete="CASCADE"), primary_key=True
    )
    is_reversed: Mapped[bool] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text)
