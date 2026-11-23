"""Send one prompt to the real AI and print the answer, to compare providers and tune prompts.

    uv run python -m scripts.try_prompt daily major_17 --reversed
    uv run python -m scripts.try_prompt spread "что меня ждёт в любви?"            # random cards
    uv run python -m scripts.try_prompt spread "вопрос" --cards major_01 cups_03 swords_10r
    uv run python -m scripts.try_prompt daily major_13 --provider mistral      # one provider only

In --cards, an "r" at the end means the card is reversed.
Nothing is saved anywhere.
"""

import argparse
import asyncio
import logging
import random

from sqlalchemy import select

from bot.ai import AIUnavailableError, Prompt, build_ai_client
from bot.ai.prompts import SpreadCard, card_description_prompt, spread_prompt
from bot.config import AISettings, get_database_settings
from bot.db import create_engine, create_session_factory
from bot.db.models import Card


async def load_card_names() -> dict[str, str]:
    engine = create_engine(get_database_settings().url)
    try:
        async with create_session_factory(engine)() as session:
            return {card.code: card.name_ru for card in await session.scalars(select(Card))}
    finally:
        await engine.dispose()


def build_prompt(args: argparse.Namespace, names: dict[str, str]) -> Prompt:
    if args.mode == "daily":
        return card_description_prompt(names[args.card], args.reversed)

    if args.cards:
        cards = []
        for item in args.cards:
            is_reversed = item.endswith("r") and item[:-1] in names
            cards.append(SpreadCard(names[item[:-1] if is_reversed else item], is_reversed))
    else:
        rng = random.SystemRandom()
        cards = [SpreadCard(names[code], rng.random() < 0.5) for code in rng.sample(list(names), 3)]
    return spread_prompt(args.question, cards)


async def run(args: argparse.Namespace) -> int:
    names = await load_card_names()
    prompt = build_prompt(args, names)
    print(prompt.user, end="\n\n")

    settings = AISettings(ai_providers=args.provider) if args.provider else AISettings()
    ai = build_ai_client(settings)
    try:
        completion = await ai.generate(prompt)
    except AIUnavailableError:
        print("Ни один ИИ-провайдер не ответил, подробности в логе выше.")
        return 1
    finally:
        await ai.close()
    print(f"--- {completion.provider} / {completion.model}, {len(completion.text)} символов ---")
    print(completion.text)
    return 0


def main() -> None:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--provider", help="use only this provider, e.g. groq")
    parser = argparse.ArgumentParser(description="Try a prompt on the real AI.")
    modes = parser.add_subparsers(dest="mode", required=True)
    daily = modes.add_parser("daily", parents=[common], help="card of the day description")
    daily.add_argument("card", help="card code, e.g. major_17")
    daily.add_argument("--reversed", action="store_true")
    spread = modes.add_parser("spread", parents=[common], help="three-card spread")
    spread.add_argument("question")
    spread.add_argument("--cards", nargs=3, help="three card codes; add r for reversed")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
