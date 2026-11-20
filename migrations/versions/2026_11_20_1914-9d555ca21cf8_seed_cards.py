"""seed cards

Revision ID: 9d555ca21cf8
Revises: 545157bc0a96
Create Date: 2026-11-20 19:14:00

The 78 cards are reference data that never change, so they live in a migration:
every new database gets them with `alembic upgrade head`.
The data is written out here instead of imported from the app, so this migration
keeps producing the same rows even if the app code changes later.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9d555ca21cf8"
down_revision: str | Sequence[str] | None = "545157bc0a96"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Rider–Waite order: Strength is 8, Justice is 11.
MAJOR_ARCANA = [
    "Шут",
    "Маг",
    "Верховная Жрица",
    "Императрица",
    "Император",
    "Иерофант",
    "Влюблённые",
    "Колесница",
    "Сила",
    "Отшельник",
    "Колесо Фортуны",
    "Справедливость",
    "Повешенный",
    "Смерть",
    "Умеренность",
    "Дьявол",
    "Башня",
    "Звезда",
    "Луна",
    "Солнце",
    "Суд",
    "Мир",
]

# Suit code -> suit name in the genitive case ("Туз Кубков").
SUITS = {
    "wands": "Жезлов",
    "cups": "Кубков",
    "swords": "Мечей",
    "pentacles": "Пентаклей",
}

# Card number -> rank name. 11-14 are the court cards.
RANKS = {
    1: "Туз",
    2: "Двойка",
    3: "Тройка",
    4: "Четвёрка",
    5: "Пятёрка",
    6: "Шестёрка",
    7: "Семёрка",
    8: "Восьмёрка",
    9: "Девятка",
    10: "Десятка",
    11: "Паж",
    12: "Рыцарь",
    13: "Королева",
    14: "Король",
}

cards_table = sa.table(
    "cards",
    sa.column("code", sa.String),
    sa.column("name_ru", sa.String),
    sa.column("arcana", sa.String),
    sa.column("suit", sa.String),
    sa.column("number", sa.SmallInteger),
)


def _cards() -> list[dict]:
    rows = [
        {
            "code": f"major_{number:02d}",
            "name_ru": name,
            "arcana": "major",
            "suit": None,
            "number": number,
        }
        for number, name in enumerate(MAJOR_ARCANA)
    ]
    rows += [
        {
            "code": f"{suit}_{number:02d}",
            "name_ru": f"{rank} {suit_name}",
            "arcana": "minor",
            "suit": suit,
            "number": number,
        }
        for suit, suit_name in SUITS.items()
        for number, rank in RANKS.items()
    ]
    return rows


def upgrade() -> None:
    op.bulk_insert(cards_table, _cards())


def downgrade() -> None:
    codes = [card["code"] for card in _cards()]
    op.execute(cards_table.delete().where(cards_table.c.code.in_(codes)))
