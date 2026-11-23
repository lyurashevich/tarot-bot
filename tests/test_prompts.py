from bot.ai.formatting import to_telegram_html
from bot.ai.prompts import SpreadCard, card_description_prompt, spread_prompt


def test_card_description_prompt_has_card_and_position() -> None:
    upright = card_description_prompt("Звезда", is_reversed=False)
    reversed_ = card_description_prompt("Звезда", is_reversed=True)

    assert "Звезда" in upright.user
    assert "прямое" in upright.user
    assert "перевёрнутое" in reversed_.user
    assert "карты дня" in upright.system


def test_spread_prompt_has_question_and_all_cards() -> None:
    prompt = spread_prompt(
        "  Что меня ждёт в любви?  ",
        [
            SpreadCard("Шут", is_reversed=False),
            SpreadCard("Туз Кубков", is_reversed=True),
            SpreadCard("Смерть", is_reversed=False),
        ],
    )

    assert "«Что меня ждёт в любви?»" in prompt.user
    assert "1. Шут — прямое положение" in prompt.user
    assert "2. Туз Кубков — перевёрнутое положение" in prompt.user
    assert "3. Смерть — прямое положение" in prompt.user
    assert "самоубийств" in prompt.system  # crisis rule is in place


def test_formatting_converts_bold_and_escapes_html() -> None:
    text = "**Совет дня:** не бойтесь <перемен> & слушайте себя"

    assert to_telegram_html(text) == (
        "<b>Совет дня:</b> не бойтесь &lt;перемен&gt; &amp; слушайте себя"
    )


def test_formatting_drops_unpaired_markers_and_turns_headings_bold() -> None:
    text = "## Итог\n\nВсё **будет хорошо"

    assert to_telegram_html(text) == "<b>Итог</b>\n\nВсё будет хорошо"


def test_formatting_converts_italic_but_not_list_bullets() -> None:
    text = "*P.S. Карты показывают ситуацию.*\n* пункт списка\nвремя 2*3*4"

    assert to_telegram_html(text) == (
        "<i>P.S. Карты показывают ситуацию.</i>\n* пункт списка\nвремя 2*3*4"
    )


def test_formatting_bold_and_italic_together() -> None:
    assert to_telegram_html("**Совет дня:** *просто* выдохни") == (
        "<b>Совет дня:</b> <i>просто</i> выдохни"
    )
