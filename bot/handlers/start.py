from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router(name="start")


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    # Placeholder: user registration and the main menu come in stage 3.
    await message.answer("Привет! Я таро-бот. Скоро здесь появятся карта дня и расклады.")
