import asyncio
import uuid

import loguru
from aiogram.exceptions import TelegramAPIError

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
from app.models.matrix import Matrix
from app.schemas.telegram_user import generate_random_user


async def add_bot_to_matrix(
        matrix_id: uuid.UUID,
        donate_sum: int,
) -> None:
    from app.core.container import Container

    container = Container()
    matrix_service = container.matrix_service()
    telegram_user_service = container.telegram_user_service()
    donate_service = container.donate_service()
    donate_confirm_service = container.donate_confirm_service()

    matrix = await matrix_service.get_matrix(id=matrix_id)
    if len(matrix.telegram_users) >= 2:
        return

    current_user = await telegram_user_service.get_telegram_user(id=matrix.owner_id)

    bot_user_schema = generate_random_user()
    bot_user_schema.sponsor_user_id = current_user.user_id
    bot_user_schema.depth_level = current_user.depth_level + 1
    bot_user_schema.is_bot = True

    bot_user = await telegram_user_service.create_telegram_user(
        user=bot_user_schema,
    )
    donations_data = {}

    await donate_service.handle_matrix_activation(
        current_user,
        bot_user,
        donate_sum,
        donations_data,
        matrix.status,
        found_matrix=matrix,
    )

    donate = await donate_confirm_service.create_donate(
        telegram_user_id=current_user.id,
        donate_data=donations_data,
        matrix_id=matrix.id,
        quantity=donate_sum,
    )
    bot_user.status = matrix.status

    transactions = await donate_confirm_service.get_donate_transactions_by_donate_id(
        donate_id=donate.id
    )

    for transaction in transactions:
        sponsor = await telegram_user_service.get_telegram_user(
            id=transaction.sponsor_id
        )
        sponsor.bill += transaction.quantity
        # блок отправки сообщений спонсорам
        try:
            await bot.send_message(
                text=f"Вам подарок в размере <b>${int(transaction.quantity)}</b>\n",
                chat_id=sponsor.user_id,
            )
        except TelegramAPIError:
            pass

@celery_app.task
def add_bot_to_matrix_task(
        matrix_id: uuid.UUID,
        donate_sum: int,
) -> None:
    loop.run_until_complete(
        add_bot_to_matrix(
            matrix_id,
            donate_sum,
        )
    )

