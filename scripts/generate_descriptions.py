"""Generate the card-of-the-day descriptions: 78 cards x 2 positions.

Only missing descriptions are generated; each one is saved right away, so an
interrupted run can simply be started again.

    uv run python -m scripts.generate_descriptions                  # all missing
    uv run python -m scripts.generate_descriptions --card major_17  # one card, both positions
    uv run python -m scripts.generate_descriptions --force          # regenerate everything
"""

import argparse
import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from bot.ai import AIUnavailableError, build_ai_client
from bot.ai.prompts import card_description_prompt
from bot.config import AISettings, get_database_settings
from bot.db import create_engine, create_session_factory
from bot.db.models import Card, CardDescription


async def generate(card_codes: list[str] | None, force: bool) -> int:
    engine = create_engine(get_database_settings().url)
    session_factory = create_session_factory(engine)
    ai = build_ai_client(AISettings())
    try:
        async with session_factory() as session:
            query = select(Card).order_by(Card.id)
            if card_codes:
                query = query.where(Card.code.in_(card_codes))
            cards = list(await session.scalars(query))
            if card_codes and len(cards) != len(set(card_codes)):
                found = {card.code for card in cards}
                print("Нет таких карт:", ", ".join(sorted(set(card_codes) - found)))
                return 1

            existing = set(
                (
                    await session.execute(
                        select(CardDescription.card_id, CardDescription.is_reversed)
                    )
                )
                .tuples()
                .all()
            )
            todo = [
                (card, is_reversed)
                for card in cards
                for is_reversed in (False, True)
                if force or (card.id, is_reversed) not in existing
            ]
            if not todo:
                print("Все описания уже есть. Чтобы перегенерировать, добавьте --force.")
                return 0

            for index, (card, is_reversed) in enumerate(todo, start=1):
                position = "перевёрнутая" if is_reversed else "прямая"
                try:
                    completion = await ai.generate(
                        card_description_prompt(card.name_ru, is_reversed)
                    )
                except AIUnavailableError:
                    print(
                        f"Ни один ИИ-провайдер не ответил. Готово {index - 1} из {len(todo)}; "
                        "запустите скрипт позже — он продолжит с того же места."
                    )
                    return 1
                statement = insert(CardDescription).values(
                    card_id=card.id, is_reversed=is_reversed, text=completion.text
                )
                await session.execute(
                    statement.on_conflict_do_update(
                        index_elements=[CardDescription.card_id, CardDescription.is_reversed],
                        set_={"text": statement.excluded.text},
                    )
                )
                await session.commit()
                print(
                    f"[{index}/{len(todo)}] {card.name_ru}, {position}: "
                    f"{len(completion.text)} символов ({completion.provider})"
                )
        print("Готово.")
        return 0
    finally:
        await ai.close()
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate card-of-the-day descriptions.")
    parser.add_argument("--card", action="append", help="card code, e.g. major_17; repeatable")
    parser.add_argument("--force", action="store_true", help="regenerate existing descriptions")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    raise SystemExit(asyncio.run(generate(args.card, args.force)))


if __name__ == "__main__":
    main()
