"""Bot entrypoint (long polling)."""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from bot.config import get_settings
from bot.handlers import commands, stars

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

BOT_COMMANDS = {
    "uz": [
        BotCommand(command="start", description="Boshlash / asosiy menyu"),
        BotCommand(command="menu", description="Menyu"),
        BotCommand(command="profile", description="Profil"),
        BotCommand(command="servers", description="Serverlar ro'yxati"),
        BotCommand(command="invite", description="Do'st taklif qilish (bonus)"),
        BotCommand(command="help", description="Yordam"),
        BotCommand(command="support", description="Qo'llab-quvvatlash"),
    ],
    "ru": [
        BotCommand(command="start", description="Старт / главное меню"),
        BotCommand(command="menu", description="Меню"),
        BotCommand(command="profile", description="Профиль"),
        BotCommand(command="servers", description="Список серверов"),
        BotCommand(command="invite", description="Пригласить друга (бонус)"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="support", description="Поддержка"),
    ],
    "en": [
        BotCommand(command="start", description="Start / main menu"),
        BotCommand(command="menu", description="Menu"),
        BotCommand(command="profile", description="Profile"),
        BotCommand(command="servers", description="Server list"),
        BotCommand(command="invite", description="Invite a friend (bonus)"),
        BotCommand(command="help", description="Help"),
        BotCommand(command="support", description="Support"),
    ],
}


async def main() -> None:
    settings = get_settings()
    if not settings.bot_token:
        raise SystemExit("BOT_TOKEN is not set")

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(stars.router)   # payment updates must win over generic text handlers
    dp.include_router(commands.router)

    # Uzbek is the default; ru/en users see localized command hints.
    await bot.set_my_commands(BOT_COMMANDS["uz"])
    await bot.set_my_commands(BOT_COMMANDS["ru"], language_code="ru")
    await bot.set_my_commands(BOT_COMMANDS["en"], language_code="en")
    logger.info("bot started (polling)")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
