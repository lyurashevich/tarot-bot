from sqlalchemy import BigInteger, String, false
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base
from bot.db.models.mixins import TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Telegram ids do not fit into a 32-bit integer.
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    first_name: Mapped[str] = mapped_column(String)
    username: Mapped[str | None] = mapped_column(String)
    is_subscribed: Mapped[bool] = mapped_column(default=False, server_default=false())
