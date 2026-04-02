import asyncio
import uuid
from datetime import timedelta, datetime
from typing import Optional

from aiogram import Bot
from aiogram.types import Message
from celery import shared_task
from dependency_injector.wiring import inject, Provide

from app.models.matrix import Matrix
from app.models.telegram_user import TelegramUser, statuses_colors_data
from app.services.donate_confirm_service import DonateConfirmService
from app.services.telegram_user_service import TelegramUserService
from app.core import celery_app
from app.keyboards.donate import get_donate_keyboard
from app.loader import bot
from app.tasks.const import (
    loop
)
from app.models.telegram_user import DonateStatus, MatrixBuildType
from app.core.config import settings


async def send_first_level_notification(
        matrix_id: uuid.UUID,
        matrix_owner_user_id: int | None = None,
) -> Message:
    from app.core.container import Container

    container = Container()
    matrix_service = container.matrix_service()
    telegram_user_service = container.telegram_user_service()

    matrix =  await matrix_service.get_matrix(id=matrix_id)

    if not matrix_owner_user_id:
        matrix_owner = await telegram_user_service.get_telegram_user(
            id=matrix.owner_id
        )
        matrix_owner_user_id = matrix_owner.user_id

    matrix_status_str = (
        f"{statuses_colors_data.get(matrix.status)} "
        f"{matrix.status.value.split()[0]}"
    )
    message_text = (
        f"На Ваш {matrix_status_str} уровень добавился агент, "
        f"Вы на шаг ближе к подаркам 🎁 "
    )
    reply_markup = get_donate_keyboard(
        buttons={"Посмотреть уровень": f"detail_matrix_{matrix.id}"},
    )
    return await bot.send_message(
        chat_id=matrix_owner_user_id,
        text=message_text,
        reply_markup=reply_markup
    )

@celery_app.task
def send_matrix_first_level_notification_task(
        matrix_id: uuid.UUID,
        matrix_owner_user_id: int | None = None,
) -> None:
    loop.run_until_complete(
        send_first_level_notification(
            matrix_id,
            matrix_owner_user_id
        )
    )

