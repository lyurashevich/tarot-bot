"""Turn AI text into safe Telegram HTML.

The model is asked for plain text with **bold**. Everything else is escaped, so whatever
the model writes cannot break Telegram's HTML parser.
"""

import html
import re

_BOLD = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
_HEADING = re.compile(r"^#{1,6}[ \t]*(.+?)[ \t]*$", re.MULTILINE)
# *italic* within one line. "* item" (a list bullet) is left alone: no space after the opening *.
_ITALIC = re.compile(r"(?<![*\w])\*(?![\s*])([^*\n]+?)(?<!\s)\*(?![*\w])")


def to_telegram_html(text: str) -> str:
    result = html.escape(text.strip(), quote=False)
    result = _BOLD.sub(r"<b>\1</b>", result)
    result = result.replace("**", "")  # an unpaired marker
    result = _ITALIC.sub(r"<i>\1</i>", result)
    # Models sometimes add headings despite the instructions: show them as bold lines.
    result = _HEADING.sub(r"<b>\1</b>", result)
    return result
