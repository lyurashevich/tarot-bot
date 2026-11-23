from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot import keyboards, texts

router = Router(name="start")


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    # UserMiddleware has already registered the user by this point.
    await message.answer(texts.WELCOME, reply_markup=keyboards.main_menu())
