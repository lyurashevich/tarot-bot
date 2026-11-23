"""All user-facing texts. Messages use Telegram HTML markup."""

# Main menu buttons. Handlers match incoming messages against these exact strings.
BUTTON_DAILY_CARD = "🃏 Карта дня"
BUTTON_SPREAD = "🔮 Расклад"
BUTTON_SUBSCRIPTION = "🔔 Подписка"

WELCOME = (
    "Добро пожаловать в «Шёпот Арканов» 🌙\n"
    "\n"
    "Карты не решают за тебя — они помогают услышать то, что ты уже чувствуешь.\n"
    "\n"
    "🃏 <b>Карта дня</b> — одна карта-подсказка на сегодня.\n"
    "🔮 <b>Расклад</b> — задай вопрос, и три карты ответят на него вместе.\n"
    "🔔 <b>Подписка</b> — карта дня будет приходить к тебе сама каждый день.\n"
    "\n"
    "<i>Трактовки карт — повод задуматься, а не руководство к действию.</i>\n"
    "\n"
    "С чего начнём? 👇"
)

USE_MENU = "Выбери, что тебе нужно, в меню ниже 👇"

DAILY_CARD_ALREADY_DRAWN = (
    "Карта дня на сегодня у тебя уже есть, приходи завтра 🌟"
)
SOMETHING_WENT_WRONG = "Что-то пошло не так 😔 Попробуй чуть позже."


def daily_card_header(card_name_html: str, is_reversed: bool) -> str:
    position = " (перевёрнутая)" if is_reversed else ""
    return f"🃏 <b>Карта дня: {card_name_html}</b>{position}"


# Placeholders until stages 6–7.
SPREAD_SOON = "🔮 Расклады скоро появятся — карты ещё раскладываются ✨"
SUBSCRIPTION_SOON = "🔔 Подписка на ежедневную карту скоро появится ✨"

# Shown in Telegram before the user presses "Start" (up to 512 characters).
BOT_DESCRIPTION = (
    "Шёпот Арканов — бот для гаданий на таро 🌙\n"
    "\n"
    "🃏 Карта дня — одна подсказка на сегодня\n"
    "🔮 Расклад из трёх карт — ответ на твой вопрос\n"
    "🔔 Ежедневная карта по подписке\n"
    "\n"
    "Нажми «Запустить», чтобы начать."
)
# Shown in the bot's profile and in shared links (up to 120 characters).
BOT_SHORT_DESCRIPTION = "Карта дня и расклады на таро с трактовкой 🌙"

COMMAND_START = "Главное меню"
