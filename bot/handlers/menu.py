from aiogram import F, Router
from aiogram.types import Message

from bot import keyboards, texts

router = Router(name="menu")


@router.message(F.text == texts.BUTTON_DAILY_CARD)
async def handle_daily_card(message: Message) -> None:
    await message.answer(texts.DAILY_CARD_SOON)


@router.message(F.text == texts.BUTTON_SPREAD)
async def handle_spread(message: Message) -> None:
    await message.answer(texts.SPREAD_SOON)


@router.message(F.text == texts.BUTTON_SUBSCRIPTION)
async def handle_subscription(message: Message) -> None:
    await message.answer(texts.SUBSCRIPTION_SOON)


@router.message()
async def handle_anything_else(message: Message) -> None:
    """Any other message: point the user back to the menu (and restore it if it was hidden)."""
    await message.answer(texts.USE_MENU, reply_markup=keyboards.main_menu())
