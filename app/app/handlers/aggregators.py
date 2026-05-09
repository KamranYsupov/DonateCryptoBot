import loguru
from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, CommandObject, Command
from dependency_injector.wiring import inject, Provide

from app.core.container import Container
from app.services.telegram_user_service import TelegramUserService
from app.core.config import settings
from app.db.commit_decorator import commit_and_close_session
from app.services.donate_confirm_service import DonateConfirmService
from app.models.donate import DonateTransaction, DonateTransactionType

aggregators_router = Router()


@aggregators_router.message(Command("aggregate_donates_sum"))
@inject
@commit_and_close_session
async def aggregate_donates_sum_handler(
        message: Message,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
):
    await message.answer("Start donates_sum aggregation.")
    telegram_users_ids = await telegram_user_service.get_ids(
        is_bot=False,
        is_admin=False,
    )
    for user_id in telegram_users_ids:
        donates_sum = await donate_confirm_service.get_transactions_sum(
            sponsor_id=user_id,
        )
        await telegram_user_service.update(
            obj_id=user_id,
            obj_in={"donates_sum": donates_sum},
        )

    admin = await telegram_user_service.get_admin()
    admin_donates_sum = await donate_confirm_service.get_transactions_sum(
        DonateTransaction.type_ != DonateTransactionType.SYSTEM,
        sponsor_id=admin.id,
    )
    await telegram_user_service.update(
        obj_id=admin.id,
        obj_in={"donates_sum": admin_donates_sum},
    )

    await message.answer("donates_sum aggregation completed.")


@aggregators_router.message(Command("aggregate_invites_count"))
@inject
@commit_and_close_session
async def aggregate_invites_count_handler(
        message: Message,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
):
    await message.answer("Start invites_count aggregation.")
    telegram_users = await telegram_user_service.get_list(
        is_bot=False,
    )
    updated_count = 0
    for user in telegram_users:
        invites_count = await telegram_user_service.get_count(
            sponsor_user_id=user.user_id,
        )
        if invites_count != user.invites_count:
            updated_count += 1
            await telegram_user_service.update(
                obj_id=user.id,
                obj_in={"invites_count": invites_count},
            )

    await message.answer(f"objects updated: {updated_count}.")
    await message.answer("invites_count aggregation completed.")