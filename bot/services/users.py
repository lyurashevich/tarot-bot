from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import User


async def register_user(
    session: AsyncSession, *, telegram_id: int, first_name: str, username: str | None
) -> User:
    """Return the user with this Telegram id, creating it or refreshing its name if needed.

    Usually this is a single SELECT: the ORM only writes when the name or username changed.
    """
    user = await _find_by_telegram_id(session, telegram_id)
    if user is None:
        # ON CONFLICT DO NOTHING: two updates from a new user may arrive at the same time.
        await session.execute(
            insert(User)
            .values(telegram_id=telegram_id, first_name=first_name, username=username)
            .on_conflict_do_nothing(index_elements=[User.telegram_id])
        )
        user = await _find_by_telegram_id(session, telegram_id)
        assert user is not None
    else:
        user.first_name = first_name
        user.username = username
    await session.commit()
    return user


async def _find_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    return await session.scalar(select(User).where(User.telegram_id == telegram_id))
