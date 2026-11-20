from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.users import register_user


class UserMiddleware(BaseMiddleware):
    """Registers the sender on every update and passes the database user as `user`.

    Must run after DbSessionMiddleware, which provides `session`.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # aiogram puts the sender of any update here; there is none for e.g. channel posts.
        telegram_user: TelegramUser | None = data.get("event_from_user")
        if telegram_user is not None and not telegram_user.is_bot:
            session: AsyncSession = data["session"]
            data["user"] = await register_user(
                session,
                telegram_id=telegram_user.id,
                first_name=telegram_user.first_name,
                username=telegram_user.username,
            )
        return await handler(event, data)
