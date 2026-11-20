from aiogram import Router, html
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot import keyboards, texts
from bot.db.models import User

router = Router(name="start")


@router.message(CommandStart())
async def handle_start(message: Message, user: User) -> None:
    # UserMiddleware has already registered the user by this point.
    await message.answer(
        texts.WELCOME.format(name=html.quote(user.first_name)),
        reply_markup=keyboards.main_menu(),
    )
