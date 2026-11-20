from aiogram import Bot
from aiogram.types import BotCommand

from bot import texts


async def update_bot_profile(bot: Bot) -> None:
    """Sync the bot's description and command menu in Telegram with the texts in code.

    Runs on every start: the calls are idempotent, so the profile always matches the code.
    """
    await bot.set_my_description(texts.BOT_DESCRIPTION)
    await bot.set_my_short_description(texts.BOT_SHORT_DESCRIPTION)
    await bot.set_my_commands([BotCommand(command="start", description=texts.COMMAND_START)])
