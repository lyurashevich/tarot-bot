"""One-off import of a deck's card images.

For every card the script:
1. finds its image file by name (major_arcana_fool.png, minor_arcana_cups_queen.png, ...);
2. scales it down and converts to JPEG, and makes a reversed (rotated 180°) copy;
3. posts both to the private storage channel, which gives their Telegram file_ids;
4. saves the file_ids to deck_card_images.

Nothing is written to disk. Running it again re-uploads the images and overwrites the rows.

    uv run python -m scripts.import_deck --source ~/Downloads/tarot \\
        --deck rider_waite --name "Райдер–Уэйт"

    # Check file names and image processing only: no Telegram, no database.
    uv run python -m scripts.import_deck --source ~/Downloads/tarot --dry-run
"""

import argparse
import asyncio
import io
import re
from dataclasses import dataclass
from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import BufferedInputFile
from PIL import Image
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import DeckImportSettings, get_database_settings
from bot.db import create_engine, create_session_factory
from bot.db.models import Card, Deck, DeckCardImage

TARGET_HEIGHT = 1280  # Telegram does not show photos larger than this anyway.
JPEG_QUALITY = 90
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
# Telegram allows about 20 messages a minute in one channel; the script also
# waits whenever Telegram asks it to slow down.
DELAY_BETWEEN_MESSAGES = 3.0

MAJOR_ARCANA_SLUGS = [
    "fool",
    "magician",
    "priestess",
    "empress",
    "emperor",
    "hierophant",
    "lovers",
    "chariot",
    "strength",
    "hermit",
    "fortune",
    "justice",
    "hanged",
    "death",
    "temperance",
    "devil",
    "tower",
    "star",
    "moon",
    "sun",
    "judgement",
    "world",
]
MINOR_RANKS = {
    "ace": 1,
    **{str(number): number for number in range(2, 11)},
    "page": 11,
    "knight": 12,
    "queen": 13,
    "king": 14,
}
MAJOR_PATTERN = re.compile(r"major_arcana_(?P<slug>[a-z]+)")
MINOR_PATTERN = re.compile(
    r"minor_arcana_(?P<suit>wands|cups|swords|pentacles)_(?P<rank>[a-z0-9]+)"
)
EXPECTED_CODES = {f"major_{number:02d}" for number in range(len(MAJOR_ARCANA_SLUGS))} | {
    f"{suit}_{number:02d}"
    for suit in ("wands", "cups", "swords", "pentacles")
    for number in MINOR_RANKS.values()
}


class DeckImportError(Exception):
    """A problem with the source files; reported to the user without a traceback."""


@dataclass(frozen=True)
class ProcessedImage:
    upright: bytes
    reversed: bytes


def card_code_from_filename(stem: str) -> str | None:
    """major_arcana_fool -> major_00, minor_arcana_cups_queen -> cups_13."""
    if match := MAJOR_PATTERN.fullmatch(stem):
        slug = match["slug"]
        if slug in MAJOR_ARCANA_SLUGS:
            return f"major_{MAJOR_ARCANA_SLUGS.index(slug):02d}"
    elif match := MINOR_PATTERN.fullmatch(stem):
        number = MINOR_RANKS.get(match["rank"])
        if number is not None:
            return f"{match['suit']}_{number:02d}"
    return None


def find_card_files(source: Path) -> dict[str, Path]:
    """Map every card code to its file. Fails if any card is missing or a file is unknown."""
    files: dict[str, Path] = {}
    unknown: list[str] = []
    duplicates: list[str] = []
    for path in sorted(source.iterdir()):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        code = card_code_from_filename(path.stem)
        if code is None:
            unknown.append(path.name)
        elif code in files:
            duplicates.append(f"{files[code].name} / {path.name}")
        else:
            files[code] = path

    problems = []
    if unknown:
        problems.append("Не удалось определить карту по имени файла: " + ", ".join(unknown))
    if duplicates:
        problems.append("Несколько файлов для одной карты: " + ", ".join(duplicates))
    if missing := sorted(EXPECTED_CODES - files.keys()):
        problems.append("Нет файлов для карт: " + ", ".join(missing))
    if problems:
        raise DeckImportError("\n".join(problems))
    return files


def process_image(path: Path) -> ProcessedImage:
    with Image.open(path) as image:
        image = image.convert("RGB")
        if image.height > TARGET_HEIGHT:
            width = round(image.width * TARGET_HEIGHT / image.height)
            image = image.resize((width, TARGET_HEIGHT), Image.Resampling.LANCZOS)
        return ProcessedImage(
            upright=_to_jpeg(image),
            reversed=_to_jpeg(image.rotate(180)),
        )


def _to_jpeg(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buffer.getvalue()


async def upload_photo(bot: Bot, chat_id: int, data: bytes, filename: str, caption: str) -> str:
    """Post a photo to the storage channel and return its file_id."""
    while True:
        try:
            message = await bot.send_photo(
                chat_id, BufferedInputFile(data, filename=filename), caption=caption
            )
        except TelegramRetryAfter as error:
            print(f"  Telegram просит подождать {error.retry_after} с…")
            await asyncio.sleep(error.retry_after)
            continue
        await asyncio.sleep(DELAY_BETWEEN_MESSAGES)
        # The last size is the largest one.
        return message.photo[-1].file_id


async def get_or_create_deck(session: AsyncSession, code: str, name: str) -> Deck:
    deck = await session.scalar(select(Deck).where(Deck.code == code))
    if deck is None:
        deck = Deck(code=code, name=name)
        session.add(deck)
    else:
        deck.name = name
    await session.flush()
    return deck


async def save_image(
    session: AsyncSession, deck_id: int, card_id: int, upright: str, reversed_: str
) -> None:
    statement = insert(DeckCardImage).values(
        deck_id=deck_id, card_id=card_id, file_id_upright=upright, file_id_reversed=reversed_
    )
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[DeckCardImage.deck_id, DeckCardImage.card_id],
            set_={
                "file_id_upright": statement.excluded.file_id_upright,
                "file_id_reversed": statement.excluded.file_id_reversed,
            },
        )
    )


def dry_run(files: dict[str, Path]) -> None:
    total = 0
    for code, path in sorted(files.items()):
        processed = process_image(path)
        size = len(processed.upright) + len(processed.reversed)
        total += size
        print(f"{code:<14} {path.name:<40} {len(processed.upright) // 1024:>5} КБ")
    print(f"Все {len(files)} карт в порядке, всего {total / 1024 / 1024:.1f} МБ (обе ориентации).")


async def run_import(files: dict[str, Path], deck_code: str, deck_name: str) -> None:
    settings = DeckImportSettings()
    engine = create_engine(get_database_settings().url)
    session_factory = create_session_factory(engine)
    bot = Bot(token=settings.bot_token.get_secret_value())
    try:
        async with session_factory() as session:
            cards = {card.code: card for card in await session.scalars(select(Card))}
            if missing := sorted(EXPECTED_CODES - cards.keys()):
                raise DeckImportError(
                    f"В базе нет карт: {', '.join(missing)}. Выполните: uv run alembic upgrade head"
                )
            deck = await get_or_create_deck(session, deck_code, deck_name)
            await session.commit()

            for index, (code, path) in enumerate(sorted(files.items()), start=1):
                card = cards[code]
                print(f"[{index}/{len(files)}] {card.name_ru}")
                processed = process_image(path)
                upright = await upload_photo(
                    bot,
                    settings.storage_chat_id,
                    processed.upright,
                    f"{code}.jpg",
                    f"{card.name_ru} ({code})",
                )
                reversed_ = await upload_photo(
                    bot,
                    settings.storage_chat_id,
                    processed.reversed,
                    f"{code}_reversed.jpg",
                    f"{card.name_ru} ({code}), перевёрнутая",
                )
                # Commit card by card so an interrupted run keeps what it uploaded.
                await save_image(session, deck.id, card.id, upright, reversed_)
                await session.commit()
        print(f"Готово: колода «{deck_name}», {len(files)} карт.")
    finally:
        await bot.session.close()
        await engine.dispose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import a deck's card images into Telegram.")
    parser.add_argument("--source", type=Path, required=True, help="folder with card images")
    parser.add_argument("--deck", default="rider_waite", help="deck code (default: rider_waite)")
    parser.add_argument("--name", default="Райдер–Уэйт", help="deck name shown to users")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="only check file names and process images: no Telegram, no database",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = args.source.expanduser()
    if not source.is_dir():
        raise SystemExit(f"Папка не найдена: {source}")
    try:
        files = find_card_files(source)
        if args.dry_run:
            dry_run(files)
        else:
            asyncio.run(run_import(files, args.deck, args.name))
    except DeckImportError as error:
        raise SystemExit(str(error)) from None


if __name__ == "__main__":
    main()
