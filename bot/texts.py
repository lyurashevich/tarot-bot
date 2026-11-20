"""All user-facing texts. Messages use Telegram HTML markup."""

# Main menu buttons. Handlers match incoming messages against these exact strings.
BUTTON_DAILY_CARD = "🃏 Карта дня"
BUTTON_SPREAD = "🔮 Расклад"
BUTTON_SUBSCRIPTION = "🔔 Подписка"

# {name} must be HTML-escaped by the caller.
WELCOME = (
    "{name}, добро пожаловать в «Шёпот Арканов» 🌙\n"
    "\n"
    "Карты не решают за вас — они помогают услышать то, что вы уже чувствуете.\n"
    "\n"
    "🃏 <b>Карта дня</b> — одна карта-подсказка на сегодня.\n"
    "🔮 <b>Расклад</b> — задайте вопрос, и три карты ответят на него вместе.\n"
    "🔔 <b>Подписка</b> — карта дня будет приходить к вам сама каждый день.\n"
    "\n"
    "С чего начнём? 👇"
)

USE_MENU = "Выберите, что вам нужно, в меню ниже 👇"

# Placeholders until stages 5–7.
DAILY_CARD_SOON = "🃏 Карта дня скоро появится — колода ещё тасуется ✨"
SPREAD_SOON = "🔮 Расклады скоро появятся — карты ещё раскладываются ✨"
SUBSCRIPTION_SOON = "🔔 Подписка на ежедневную карту скоро появится ✨"

# Shown in Telegram before the user presses "Start" (up to 512 characters).
BOT_DESCRIPTION = (
    "Шёпот Арканов — бот для гаданий на таро 🌙\n"
    "\n"
    "🃏 Карта дня — одна подсказка на сегодня\n"
    "🔮 Расклад из трёх карт — ответ на ваш вопрос\n"
    "🔔 Ежедневная карта по подписке\n"
    "\n"
    "Нажмите «Запустить», чтобы начать."
)
# Shown in the bot's profile and in shared links (up to 120 characters).
BOT_SHORT_DESCRIPTION = "Карта дня и расклады на таро с трактовкой 🌙"

COMMAND_START = "Главное меню"
