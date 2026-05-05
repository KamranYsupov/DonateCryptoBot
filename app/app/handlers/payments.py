import os
from datetime import datetime, timedelta
import uuid
import json

import loguru
from aiogram import Router, F, Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from dependency_injector.wiring import inject, Provide

from app.core.container import Container
from app.services.telegram_user_service import TelegramUserService
from app.keyboards.donate import get_donate_keyboard
from app.core.config import settings
from app.keyboards.donate import get_donations_keyboard
from app.db.commit_decorator import commit_and_close_session
from app.services.crypto_bot_api_service import CryptoBotAPIService
from app.keyboards.reply import reply_cancel_keyboard, get_reply_keyboard
from app.loader import bot

payment_router = Router()

class BuyTokensState(StatesGroup):
    tokens_count = State()


@payment_router.callback_query(F.data.startswith("start_buy_tokens_state"))
async def start_buy_tokens_state_handler(
        callback: CallbackQuery,
        state: FSMContext,
) -> None:
    await state.set_state(BuyTokensState.tokens_count)
    await callback.message.delete()
    await callback.message.answer(
        "Для пополнения баланса отправьте в сообщении боту число.\n\n"
        "Пример: 175",
        reply_markup=reply_cancel_keyboard,
    )


@payment_router.message(F.text, BuyTokensState.tokens_count)
@inject
async def process_tokens_count(
        message: Message,
        state: FSMContext,
) -> None:
    try:
        tokens_count = int(message.text)
    except ValueError:
        await message.answer(
            "❌ Некорректный ввод. Отправьте положительное, целое число."
        )
        return

    await state.clear()
    message = await message.answer(
        f"Будет создан счет на сумму <b>{tokens_count} USDT</b>",
        reply_markup=get_reply_keyboard(None)
    )
    await message.answer(
        "<b>Продолжить ?</b>",
        reply_markup=get_donate_keyboard(
            buttons={
                "Да": f"buy_tokens_{message.message_id}_{tokens_count}",
                "Нет": f"donations",
            },
            sizes=(1, 1),
        )
    )


@payment_router.callback_query(F.data.startswith("buy_tokens_"))
@inject
async def buy_tokens_handler(
        callback: CallbackQuery,
        crypto_bot_api_service: CryptoBotAPIService = Provide[
            Container.crypto_bot_api_service
        ],
) -> None:
    messages_to_delete_ids = [callback.message.message_id]
    try:
        previous_message_id = int(callback.data.split("_")[-2])
        messages_to_delete_ids.append(previous_message_id)
    except ValueError:
        pass

    tokens_count = int(callback.data.split("_")[-1])

    payload = {
        "telegram_id": callback.from_user.id,
        "tokens_count": tokens_count,
        "messages_to_delete_ids": messages_to_delete_ids,
    }
    response = await crypto_bot_api_service.create_invoice(
        amount=tokens_count,
        payload=json.dumps(payload),
        description=f"Пополнение {tokens_count} USDT.",
        asset="USDT",
    )
    if not response.get("ok"):
        loguru.logger.info(response["error"])
        await callback.message.edit_text(
            "Произошла ошибка при создании платежа. Попробуйте позже."
        )
        return
    result = response["result"]

    payment_app_keyboard = InlineKeyboardBuilder()
    payment_app_keyboard.add(
        InlineKeyboardButton(
            text="Оплатить 💸",
            url=result["mini_app_invoice_url"]
        )
    )
    reply_markup = payment_app_keyboard.adjust(1, 1).as_markup()

    await callback.message.edit_text(
        "Оплатите счет в приложении ⤵️",
        reply_markup=reply_markup

    )

