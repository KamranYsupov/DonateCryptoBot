from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from app.core.config import settings

local_server = TelegramAPIServer.from_base(settings.telegram_server_url)
session = AiohttpSession(api=local_server)
bot = Bot(
    settings.bot_token,
    default=DefaultBotProperties(parse_mode="HTML"),
    session=session,
)
dp = Dispatcher()
