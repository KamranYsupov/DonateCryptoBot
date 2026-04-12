from aiogram import Router, F
from aiogram.exceptions import TelegramAPIError
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

transfer_router = Router()

class TransferState(StatesGroup):
    receiver_username = State()
    tokens_count = State()
    confirm = State()


@transfer_router.message(Command("transfer"))
async def transfer_command_handler(
        message: CallbackQuery,
        state: FSMContext,
) -> None:
    await state.set_state(TransferState.receiver_username)
    await message.answer(
        "Отправьте username получателя.",
        reply_markup=reply_cancel_keyboard,
    )


@transfer_router.message(F.text, TransferState.receiver_username)
@inject
async def process_receiver_username(
        message: Message,
        state: FSMContext,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> None:
    username = message.text[1:] if message.text[0] == "@" else message.text

    receiver = await telegram_user_service.get_telegram_user(username=username)
    if not receiver:
        await state.clear()
        await message.answer(
            "Пользователь не найден.",
            reply_markup=get_reply_keyboard(None)
        )
        return

    await state.update_data(receiver_username=username)
    await state.set_state(TransferState.tokens_count)
    await message.answer(
        f"Отправьте количество токенов для перевода."
    )



@transfer_router.message(F.text, TransferState.tokens_count)
@inject
async def process_tokens_count(
        message: Message,
        state: FSMContext,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> None:

    try:
        tokens_count = int(message.text)
    except ValueError:
        await message.answer(
            "❌ Некорректный ввод. Отправьте положительное, целое число."
        )
        return

    telegram_user = await telegram_user_service.get_telegram_user(
        user_id=message.from_user.id
    )

    if tokens_count > telegram_user.bill:
        await message.answer(
            "❌ Некорректный ввод. Число превышает сумму на счетё."
        )
        return

    state_data = await state.update_data(tokens_count=tokens_count)
    receiver_username = state_data["receiver_username"]

    receiver_username = "@" + receiver_username \
        if receiver_username[0] != "@" else receiver_username

    await message.answer(
        f"Перевод {tokens_count} токенов на счёт пользователя {receiver_username}.\n\n"
        "Вы уверены?",
        reply_markup=get_donate_keyboard(
            buttons={
                "Да": f"transfer",
                "Нет": "cancel",
            },
            sizes=(1, 1)
        )
    )

    await state.set_state(TransferState.confirm)


@transfer_router.callback_query(F.data == "transfer", TransferState.confirm)
@inject
@commit_and_close_session
async def transfer_tokens_handler(
        callback: CallbackQuery,
        state: FSMContext,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> None:
    state_data = await state.get_data()
    tokens_count = state_data["tokens_count"]

    sender = await telegram_user_service.get_telegram_user(user_id=callback.from_user.id)
    receiver = await telegram_user_service.get_telegram_user(username=state_data["receiver_username"])

    await state.clear()

    if tokens_count > sender.bill:
        await callback.message.edit_text(
            "❌ Число превышает сумму на счетё.",
            reply_markup=get_reply_keyboard(sender),
        )
        return

    sender.bill -= tokens_count
    receiver.bill += tokens_count

    await callback.message.delete()
    await callback.message.answer(
        "Перевод успешно выполнен ✅",
        reply_markup=get_reply_keyboard(sender),
    )

    try:
        await callback.bot.send_message(
            chat_id=receiver.user_id,
            text=f"Пользователь @{sender.username} перевел {tokens_count} токенов на ваш счёт."
        )
    except TelegramAPIError:
        pass




