import random
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.clock import today
from bot.daily_card_message import CAPTION_LIMIT, build_daily_card_message, visible_length
from bot.db.models import Card, CardDescription, DailyCard, DailyCardSource, Deck, DeckCardImage
from bot.services.daily_card import draw_daily_card
from bot.services.deck import find_missing_content, get_card_content
from bot.services.users import register_user

MINSK = ZoneInfo("Europe/Minsk")
DAY = date(2026, 11, 23)


@pytest.fixture
async def user_id(session: AsyncSession) -> int:
    user = await register_user(session, telegram_id=7_100_000_001, first_name="Лиза", username=None)
    return user.id


async def _draw(session: AsyncSession, user_id: int, day: date = DAY, seed: int = 1):
    return await draw_daily_card(
        session,
        user_id=user_id,
        issue_date=day,
        source=DailyCardSource.MANUAL,
        rng=random.Random(seed),
    )


async def _count_daily_cards(session: AsyncSession) -> int:
    return await session.scalar(select(func.count()).select_from(DailyCard))


# --- today() ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("utc_time", "expected"),
    [
        (datetime(2026, 11, 22, 20, 59, tzinfo=UTC), date(2026, 11, 22)),  # 23:59 in Minsk
        (datetime(2026, 11, 22, 21, 0, tzinfo=UTC), date(2026, 11, 23)),  # 00:00 in Minsk
    ],
    ids=["23:59", "00:00"],
)
def test_day_changes_at_midnight_in_minsk(utc_time: datetime, expected: date) -> None:
    assert today(MINSK, now=utc_time) == expected


# --- draw_daily_card --------------------------------------------------------


async def test_draws_and_stores_a_card(session: AsyncSession, user_id: int) -> None:
    drawn = await _draw(session, user_id)

    assert drawn.is_new
    stored = await session.scalar(select(DailyCard).where(DailyCard.user_id == user_id))
    assert (stored.issue_date, stored.card_id, stored.is_reversed) == (
        DAY,
        drawn.card.id,
        drawn.is_reversed,
    )
    assert stored.source == DailyCardSource.MANUAL


async def test_second_draw_on_the_same_day_returns_the_first_card(
    session: AsyncSession, user_id: int
) -> None:
    first = await _draw(session, user_id, seed=1)
    second = await _draw(session, user_id, seed=2)

    assert not second.is_new
    assert (second.card.id, second.is_reversed) == (first.card.id, first.is_reversed)
    assert await _count_daily_cards(session) == 1


async def test_next_day_gives_a_new_card(session: AsyncSession, user_id: int) -> None:
    await _draw(session, user_id, day=DAY)
    next_day = await _draw(session, user_id, day=date(2026, 11, 24))

    assert next_day.is_new
    assert await _count_daily_cards(session) == 2


async def test_any_card_and_both_positions_can_be_drawn(
    session: AsyncSession, user_id: int
) -> None:
    rng = random.Random(42)
    seen_cards, seen_positions = set(), set()
    for offset in range(300):
        drawn = await draw_daily_card(
            session,
            user_id=user_id,
            issue_date=date.fromordinal(DAY.toordinal() + offset),
            source=DailyCardSource.MANUAL,
            rng=rng,
        )
        seen_cards.add(drawn.card.id)
        seen_positions.add(drawn.is_reversed)

    assert len(seen_cards) > 60
    assert seen_positions == {False, True}


# --- deck content -----------------------------------------------------------


async def _add_content(session: AsyncSession, card: Card) -> None:
    deck = Deck(code="test_deck", name="Тестовая")
    session.add(deck)
    await session.flush()
    session.add(
        DeckCardImage(
            deck_id=deck.id, card_id=card.id, file_id_upright="up", file_id_reversed="down"
        )
    )
    session.add(CardDescription(card_id=card.id, is_reversed=True, text="перевёрнутая"))
    await session.flush()


async def test_card_content_matches_position(session: AsyncSession) -> None:
    card = await session.scalar(select(Card).where(Card.code == "major_17"))
    await _add_content(session, card)

    reversed_ = await get_card_content(
        session, deck_code="test_deck", card_id=card.id, is_reversed=True
    )
    upright = await get_card_content(
        session, deck_code="test_deck", card_id=card.id, is_reversed=False
    )

    assert (reversed_.file_id, reversed_.description) == ("down", "перевёрнутая")
    assert upright is None  # no upright description


async def test_missing_content_is_counted(session: AsyncSession) -> None:
    card = await session.scalar(select(Card).where(Card.code == "major_17"))
    await _add_content(session, card)

    missing = await find_missing_content(session, "test_deck")

    assert (missing.images, missing.descriptions) == (77, 155)


# --- message ----------------------------------------------------------------


def test_message_has_header_and_formatted_description() -> None:
    message = build_daily_card_message(
        "Звезда", True, "Сегодня <день> & ночь.\n\n**Совет дня:** выпей воды."
    )

    assert message.caption == (
        "🃏 <b>Карта дня: Звезда</b> (перевёрнутая)\n\n"
        "Сегодня &lt;день&gt; &amp; ночь.\n\n"
        "<b>Совет дня:</b> выпей воды."
    )
    assert message.rest is None


def test_upright_card_has_no_position_note() -> None:
    message = build_daily_card_message("Звезда", False, "Текст.")

    assert message.caption.startswith("🃏 <b>Карта дня: Звезда</b>\n\n")


def test_long_description_continues_in_a_second_message() -> None:
    paragraphs = ["а" * 400, "б" * 400, "в" * 400, "**Совет дня:** г"]

    message = build_daily_card_message("Звезда", False, "\n\n".join(paragraphs))

    assert visible_length(message.caption) <= CAPTION_LIMIT
    assert message.caption.endswith("б" * 400)
    assert message.rest == "в" * 400 + "\n\n<b>Совет дня:</b> г"


def test_visible_length_counts_like_telegram() -> None:
    # Tags do not count, entities count as one character, emoji as two UTF-16 units.
    assert visible_length("<b>a&amp;b</b> 🃏") == 6
