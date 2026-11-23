"""The card-of-the-day message: a photo whose caption holds the description.

Telegram allows 1024 characters in a photo caption. A description that does not fit
is split between paragraphs, and the rest is sent as a separate message.
"""

import html
import re
from dataclasses import dataclass

from bot import texts
from bot.ai.formatting import to_telegram_html

CAPTION_LIMIT = 1024

_TAG = re.compile(r"<[^>]+>")
_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")


@dataclass(frozen=True)
class DailyCardMessage:
    caption: str
    # The part of the description that did not fit into the caption.
    rest: str | None = None


def visible_length(telegram_html: str) -> int:
    """Length as Telegram counts it: text without tags, in UTF-16 code units."""
    text = html.unescape(_TAG.sub("", telegram_html))
    return len(text.encode("utf-16-le")) // 2


def build_daily_card_message(
    card_name: str, is_reversed: bool, description: str
) -> DailyCardMessage:
    header = texts.daily_card_header(html.escape(card_name, quote=False), is_reversed)
    # Converted paragraph by paragraph, so that splitting never cuts through a tag.
    paragraphs = [
        to_telegram_html(paragraph)
        for paragraph in _PARAGRAPH_BREAK.split(description.strip())
        if paragraph.strip()
    ]

    caption = header
    for index, paragraph in enumerate(paragraphs):
        candidate = f"{caption}\n\n{paragraph}"
        if visible_length(candidate) > CAPTION_LIMIT:
            return DailyCardMessage(caption=caption, rest="\n\n".join(paragraphs[index:]))
        caption = candidate
    return DailyCardMessage(caption=caption)
