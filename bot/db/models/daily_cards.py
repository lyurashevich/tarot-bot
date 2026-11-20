from datetime import date
from enum import StrEnum

from sqlalchemy import Date, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base
from bot.db.models.mixins import CreatedAtMixin, str_enum


class DailyCardSource(StrEnum):
    MANUAL = "manual"
    BROADCAST = "broadcast"


class DailyCard(CreatedAtMixin, Base):
    """The card of the day a user received. At most one per user per day."""

    __tablename__ = "daily_cards"
    __table_args__ = (UniqueConstraint("user_id", "issue_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # The day in the bot's time zone (Minsk for the MVP), not in UTC.
    issue_date: Mapped[date] = mapped_column(Date)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"))
    is_reversed: Mapped[bool]
    # Empty while the AI has not produced a description.
    description: Mapped[str | None] = mapped_column(Text)
    source: Mapped[DailyCardSource] = mapped_column(str_enum(DailyCardSource, "daily_card_source"))
