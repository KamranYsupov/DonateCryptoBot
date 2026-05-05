from uuid import UUID
from typing import Dict, Any

import loguru
from aiogram.exceptions import TelegramAPIError
from dependency_injector import providers
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Request
from starlette.responses import Response
from starlette import status

from app.core.container import Container
from app.handlers import send_donations_menu
from app.loader import bot
from app.api.schemas.crypto_bot import UpdateWebhookSchema, CryptoInvoiceSchema
from app.services.telegram_user_service import TelegramUserService
from app.keyboards.donate import get_donate_keyboard
from app.db.commit_decorator import commit_and_close_session

router = APIRouter(tags=['CryptoBot'], prefix='/crypto-bot')

@router.post(
    '/updates-webhook',
    status_code=status.HTTP_200_OK,
)
@inject
@commit_and_close_session
async def updates_webhook(
        body: UpdateWebhookSchema,
        telegram_user_service: TelegramUserService = Depends(
            Provide[Container.telegram_user_service]
        ),
) -> Response:
    if body.update_type != "invoice_paid":
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    invoice = CryptoInvoiceSchema(**body.payload)

    if invoice.status == "paid":
        telegram_id = invoice.payload.telegram_id
        tokens_count = invoice.payload.tokens_count

        telegram_user = await telegram_user_service.get_telegram_user(user_id=telegram_id)
        telegram_user.bill_for_activation += tokens_count


        for message_id in invoice.payload.messages_to_delete_ids:
            try:
                await bot.delete_message(
                chat_id=telegram_id,
                message_id=message_id,
            )
            except TelegramAPIError:
                pass

        await bot.send_message(
            chat_id=telegram_id,
            text="Оплата прошла успешно ✅\n\n"
                 f"На баланс зачислено {tokens_count} USDT.",
        )
        await send_donations_menu(
            from_user_id=telegram_id,
            telegram_method=bot.send_message
        )
        return Response(status_code=status.HTTP_200_OK)

    return Response(status_code=status.HTTP_400_BAD_REQUEST)

