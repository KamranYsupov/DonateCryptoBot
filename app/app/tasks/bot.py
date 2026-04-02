import asyncio
import uuid
from typing import Optional

from aiogram import Bot
from aiogram.types import Message
from celery import shared_task

from app.core.container import Container
from app.db.commit_decorator import commit_and_close_session
from app.models.donate import Donate
from app.models.telegram_user import TelegramUser
from app.services.donate_confirm_service import DonateConfirmService
from app.services.telegram_user_service import TelegramUserService
from app.core import celery_app
from app.loader import bot
from app.tasks.const import loop

@celery_app.task
def send_message_task(
        chat_id: int | str,
        text: str,
):
    loop.run_until_complete(
        bot.send_message(
            chat_id=chat_id,
            text=text
        )
    )

