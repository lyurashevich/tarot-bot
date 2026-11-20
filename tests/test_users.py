from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import User
from bot.services.users import register_user


async def _count_users(session: AsyncSession) -> int:
    return await session.scalar(select(func.count()).select_from(User))


async def test_creates_new_user(session: AsyncSession) -> None:
    user = await register_user(
        session, telegram_id=7_000_000_001, first_name="Лиза", username="liza"
    )

    assert user.id is not None
    assert user.telegram_id == 7_000_000_001
    assert user.first_name == "Лиза"
    assert user.username == "liza"
    assert user.is_subscribed is False
    assert await _count_users(session) == 1


async def test_user_without_username(session: AsyncSession) -> None:
    user = await register_user(session, telegram_id=7_000_000_002, first_name="Аня", username=None)

    assert user.username is None


async def test_second_call_returns_same_user(session: AsyncSession) -> None:
    first = await register_user(session, telegram_id=7_000_000_003, first_name="Оля", username="o")
    second = await register_user(session, telegram_id=7_000_000_003, first_name="Оля", username="o")

    assert second.id == first.id
    assert await _count_users(session) == 1


async def test_second_call_updates_name_and_username(session: AsyncSession) -> None:
    first = await register_user(session, telegram_id=7_000_000_004, first_name="Катя", username="k")
    second = await register_user(
        session, telegram_id=7_000_000_004, first_name="Екатерина", username=None
    )

    assert second.id == first.id
    session.expunge_all()  # read back from the database, not from the session cache
    stored = await session.scalar(select(User).where(User.telegram_id == 7_000_000_004))
    assert stored.first_name == "Екатерина"
    assert stored.username is None
    assert await _count_users(session) == 1
