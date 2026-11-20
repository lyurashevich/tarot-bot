from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from bot import texts


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=texts.BUTTON_DAILY_CARD),
                KeyboardButton(text=texts.BUTTON_SPREAD),
            ],
            [KeyboardButton(text=texts.BUTTON_SUBSCRIPTION)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
