import asyncio
import datetime
import uuid

import loguru
from aiogram.exceptions import TelegramAPIError
from dependency_injector.wiring import Provide, inject

from app.models.matrix import Matrix
from app.models.telegram_user import TelegramUser, statuses_colors_data
from app.services.donate_confirm_service import DonateConfirmService
from app.services.telegram_user_service import TelegramUserService
from app.keyboards.donate import get_donate_keyboard
from app.loader import bot
from app.models.telegram_user import DonateStatus, MatrixBuildType
from app.core.config import settings
from app.models.matrix import Matrix
from app.schemas.telegram_user import generate_random_user
from app.core.container import Container
from app.services.donate_service import DonateService
from app.services.matrix_service import MatrixService
from app.services.matrix_service import AddBotToMatrixTaskModelService
from app.db.commit_decorator import commit_and_close_session
from app.core.container import Container
from app.models.matrix import AddBotToMatrixTaskModel
from app.models.donate import DonateTransactionType
from app.utils.bot import send_message_or_pass, send_transaction_messages


@inject
@commit_and_close_session
async def add_bot_to_matrix(
        matrix_id: uuid.UUID,
        donate_sum: int,
        matrix_service: MatrixService = Provide[Container.matrix_service],
        telegram_user_service: TelegramUserService = Provide[Container.telegram_user_service],
        donate_service: DonateService = Provide[Container.donate_service],
        donate_confirm_service: DonateConfirmService = Provide[Container.donate_confirm_service],
) -> None:

    matrix = await matrix_service.get_matrix(id=matrix_id)
    if len(matrix.matrices) >= 2:
        return

    current_user = await telegram_user_service.get_telegram_user(id=matrix.owner_id)


    bot_user = None
    bot_user_schema = generate_random_user()

    while not bot_user:
        bot_user_schema.sponsor_user_id = current_user.user_id
        bot_user_schema.depth_level = current_user.depth_level + 1
        bot_user_schema.is_bot = True

        try:
            bot_user = await telegram_user_service.create_telegram_user(
                user=bot_user_schema,
            )
        except Exception:
            bot_user_schema = generate_random_user()
            continue

    donations_data = []

    await donate_service.handle_matrix_activation(
        current_user,
        bot_user,
        donate_sum,
        donations_data,
        matrix.status,
        found_matrix=matrix,
    )

    donate = await donate_confirm_service.create_donate(
        telegram_user_id=bot_user.id,
        donate_data=donations_data,
        matrix_id=matrix.id,
        quantity=donate_sum,
    )
    bot_user.status = matrix.status

    transactions_data = await donate_confirm_service.get_donate_transactions_by_donate_id(
        donate_id=donate.id, return_data=True,
    )

    for transaction in transactions_data:
        if transaction["type_"] == DonateTransactionType.SYSTEM:
            continue

        sponsor = await telegram_user_service.get_telegram_user(
            id=transaction["sponsor_id"]
        )
        await telegram_user_service.update(
            obj_id=sponsor.id,
            obj_in={
                "donates_sum": sponsor.donates_sum + transaction["quantity"],
                "bill_for_withdraw": sponsor.bill_for_withdraw + transaction["quantity"]
            },
        )

    admin_user = await telegram_user_service.get_telegram_user(is_admin=True)
    admin_telegram_id = admin_user.user_id
    status = matrix.status

    for data in donations_data:
        quantity = data["quantity"]
        await send_transaction_messages(
            bot=bot,
            chat_id=data["receiver_chat_id"],
            quantity=quantity,
            type_=data["type_"],
            sender_username=bot_user_schema.username,
            status=status,
            sponsor_depth=data.get("sponsor_depth"),
            matrix_length=data.get("matrix_length"),
        )

        await send_message_or_pass(
            bot=bot,
            text=f"<b><em>-{quantity} от системного баланса.</em></b>\n",
            chat_id=admin_telegram_id,
        )


@inject
async def execute_bot_matrix_tasks(
    add_bot_to_matrix_task_service: AddBotToMatrixTaskModelService = Provide[
        Container.add_bot_to_matrix_task_service
    ]
):
    now = datetime.datetime.now()
    tasks = await add_bot_to_matrix_task_service.get_list(
        AddBotToMatrixTaskModel.execute_at <= now + datetime.timedelta(minutes=1),
        is_executed=False,
    )
    tasks_data = [
        {
            "id": task.id,
            "matrix_id": task.matrix_id,
            "donate_sum": task.donate_sum,
         }
        for task in tasks
    ]
    tasks_ids = []

    for task in tasks_data:
        await add_bot_to_matrix(
            matrix_id=task["matrix_id"],
            donate_sum=task["donate_sum"],
        )
        tasks_ids.append(task["id"])

    await add_bot_to_matrix_task_service.set_is_executed(tasks_ids, commit=True)
