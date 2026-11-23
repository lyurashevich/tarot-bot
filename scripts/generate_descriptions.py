"""Generate the card-of-the-day descriptions: 78 cards x 2 positions.

Only missing descriptions are generated; each one is saved right away, so an
interrupted run can simply be started again.

    uv run python -m scripts.generate_descriptions                  # all missing
    uv run python -m scripts.generate_descriptions --card major_17  # one card, both positions
    uv run python -m scripts.generate_descriptions --force          # regenerate everything
    uv run python -m scripts.generate_descriptions --fix            # regenerate bad ones

Every answer is checked: it must fit into a photo caption, contain only Russian words
and end with the advice. A bad answer is asked for again, up to --attempts times.
"""

import argparse
import asyncio
import logging
import re

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from bot.ai import AIUnavailableError, build_ai_client
from bot.ai.prompts import card_description_prompt
from bot.config import AISettings, get_database_settings
from bot.daily_card_message import build_daily_card_message
from bot.db import create_engine, create_session_factory
from bot.db.models import Card, CardDescription

_LATIN = re.compile(r"[A-Za-z]")
# A letter that is neither Cyrillic nor Latin: Chinese, Arabic, ...
_OTHER_SCRIPT = re.compile(r"[^\W\d_A-Za-zА-Яа-яЁё]")


def description_problems(card_name: str, is_reversed: bool, text: str) -> list[str]:
    problems = []
    if build_daily_card_message(card_name, is_reversed, text).rest is not None:
        problems.append(f"не влезает в подпись ({len(text)} символов)")
    if _LATIN.search(text):
        problems.append("латиница")
    if _OTHER_SCRIPT.search(text):
        problems.append("буквы других алфавитов")
    if "Совет дня" not in text:
        problems.append("нет совета дня")
    return problems


async def generate(card_codes: list[str] | None, force: bool, fix: bool, attempts: int) -> int:
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

            existing = {
                (card_id, is_reversed): text
                for card_id, is_reversed, text in (
                    await session.execute(
                        select(
                            CardDescription.card_id,
                            CardDescription.is_reversed,
                            CardDescription.text,
                        )
                    )
                )
            }

            def needed(card: Card, is_reversed: bool) -> bool:
                text = existing.get((card.id, is_reversed))
                if text is None or force:
                    return True
                return fix and bool(description_problems(card.name_ru, is_reversed, text))

            todo = [
                (card, is_reversed)
                for card in cards
                for is_reversed in (False, True)
                if needed(card, is_reversed)
            ]
            if not todo:
                print(
                    "Нечего генерировать: все описания на месте (и в порядке, если указан --fix)."
                )
                return 0

            for index, (card, is_reversed) in enumerate(todo, start=1):
                position = "перевёрнутая" if is_reversed else "прямая"
                label = f"[{index}/{len(todo)}] {card.name_ru}, {position}"
                text = None
                for attempt in range(1, attempts + 1):
                    try:
                        completion = await ai.generate(
                            card_description_prompt(card.name_ru, is_reversed)
                        )
                    except AIUnavailableError:
                        print(
                            f"Ни один ИИ-провайдер не ответил. Готово {index - 1} из "
                            f"{len(todo)}; запустите скрипт позже — он продолжит с того же места."
                        )
                        return 1
                    problems = description_problems(card.name_ru, is_reversed, completion.text)
                    if not problems:
                        text = completion.text
                        break
                    print(f"{label}: попытка {attempt} — {', '.join(problems)}")
                if text is None:
                    if (card.id, is_reversed) in existing:
                        print(f"{label}: оставлено прежнее описание")
                        continue
                    text = completion.text  # better a flawed description than none
                statement = insert(CardDescription).values(
                    card_id=card.id, is_reversed=is_reversed, text=text
                )
                await session.execute(
                    statement.on_conflict_do_update(
                        index_elements=[CardDescription.card_id, CardDescription.is_reversed],
                        set_={"text": statement.excluded.text},
                    )
                )
                await session.commit()
                print(f"{label}: {len(text)} символов ({completion.provider})")
        print("Готово.")
        return 0
    finally:
        await ai.close()
        await engine.dispose()


async def check() -> int:
    engine = create_engine(get_database_settings().url)
    try:
        async with create_session_factory(engine)() as session:
            rows = await session.execute(
                select(Card.code, Card.name_ru, CardDescription.is_reversed, CardDescription.text)
                .join(CardDescription, CardDescription.card_id == Card.id)
                .order_by(Card.id, CardDescription.is_reversed)
            )
            bad = 0
            for code, name, is_reversed, text in rows:
                if problems := description_problems(name, is_reversed, text):
                    bad += 1
                    position = "перевёрнутая" if is_reversed else "прямая"
                    print(f"{code} {name}, {position}: {', '.join(problems)}")
            print(f"Плохих описаний: {bad}")
            return 0
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate card-of-the-day descriptions.")
    parser.add_argument("--card", action="append", help="card code, e.g. major_17; repeatable")
    parser.add_argument("--force", action="store_true", help="regenerate existing descriptions")
    parser.add_argument(
        "--fix", action="store_true", help="regenerate descriptions that fail the checks"
    )
    parser.add_argument(
        "--check", action="store_true", help="only list descriptions that fail the checks"
    )
    parser.add_argument("--attempts", type=int, default=3, help="tries per bad answer")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    if args.check:
        raise SystemExit(asyncio.run(check()))
    raise SystemExit(asyncio.run(generate(args.card, args.force, args.fix, args.attempts)))


if __name__ == "__main__":
    main()
