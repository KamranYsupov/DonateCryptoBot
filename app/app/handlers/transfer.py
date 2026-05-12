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
from app.schemas.telegram_user import BillType
from app.schemas.transfer import TransferCreateSchema
from app.services.transfer_service import TransferService
from app.utils.pagination import Paginator, get_pagination_buttons
from app.utils.datetime import to_main_tz

transfer_router = Router()

class TransferState(StatesGroup):
    bill_type = State()
    receiver_username = State()
    amount = State()
    confirm = State()


@transfer_router.callback_query(F.data.startswith("transfer_"))
@inject
async def transfer_callback_handler(
        callback: CallbackQuery,
        state: FSMContext,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> None:
    bill_type = callback.data.split("_")[-1]

    telegram_user = await telegram_user_service.get_telegram_user(
        user_id=callback.from_user.id
    )
    bill_value = getattr(telegram_user, f"bill_for_{bill_type}")

    if not bill_value:
        await callback.message.edit_text("Баланс равен нулю.",)
        return

    await state.update_data(bill_type=bill_type)
    await state.set_state(TransferState.receiver_username)

    await callback.message.delete()
    await callback.message.answer(
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
    await state.set_state(TransferState.amount)
    await message.answer(
        f"Напишите количество USDT для перевода."
    )


@transfer_router.message(F.text, TransferState.amount)
@inject
async def process_amount(
        message: Message,
        state: FSMContext,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> None:

    try:
        amount = int(message.text)
    except ValueError:
        await message.answer(
            "❌ Некорректный ввод. Отправьте положительное, целое число."
        )
        return

    state_data = await state.get_data()
    bill_type = state_data["bill_type"]

    telegram_user = await telegram_user_service.get_telegram_user(
        user_id=message.from_user.id
    )
    bill_value = getattr(telegram_user, f"bill_for_{bill_type}")

    if not bill_value:
        await state.clear()
        await message.answer(
            "❌ Некорректный ввод. Баланс равен нулю.",
            reply_markup=get_reply_keyboard(telegram_user),
        )
        return
    if amount > bill_value:
        await message.answer(
            "❌ Некорректный ввод. Число превышает сумму на балансе."
        )
        return

    state_data = await state.update_data(amount=amount)
    receiver_username = state_data["receiver_username"]

    receiver_username = "@" + receiver_username \
        if receiver_username[0] != "@" else receiver_username

    await message.answer(
        f"Перевод {amount} USDT пользователю {receiver_username}.\n\n"
        "Вы уверены?",
        reply_markup=get_donate_keyboard(
            buttons={
                "Да": f"confirm_transfer",
                "Нет": "cancel",
            },
            sizes=(1, 1)
        )
    )

    await state.set_state(TransferState.confirm)


@transfer_router.callback_query(F.data == "confirm_transfer", TransferState.confirm)
@inject
@commit_and_close_session
async def transfer_tokens_handler(
        callback: CallbackQuery,
        state: FSMContext,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        transfer_service: TransferService = Provide[
            Container.transfer_service
        ],
) -> None:
    state_data = await state.get_data()
    amount = state_data["amount"]
    bill_type = state_data["bill_type"]
    bill_field = f"bill_for_{bill_type}"

    sender = await telegram_user_service.get_telegram_user(user_id=callback.from_user.id)
    receiver = await telegram_user_service.get_telegram_user(username=state_data["receiver_username"])

    sender_bill_value = getattr(sender, bill_field)
    await state.clear()

    if amount > sender_bill_value:
        await callback.message.edit_text(
            "❌ Число превышает сумму на балансе.",
            reply_markup=get_reply_keyboard(sender),
        )
        return

    setattr(sender, bill_field, sender_bill_value - amount)
    receiver.bill_for_activation += amount
    transfer_schema = TransferCreateSchema(
        amount=amount,
        from_id=sender.id,
        to_id=receiver.id,
    )
    await transfer_service.create_transfer(transfer_schema)

    await callback.message.delete()
    await callback.message.answer(
        "Перевод успешно выполнен ✅",
        reply_markup=get_reply_keyboard(sender),
    )

    try:
        await callback.bot.send_message(
            chat_id=receiver.user_id,
            text=f"Получен перевод {amount} USDT от @{sender.username}."
        )
    except TelegramAPIError:
        pass


@transfer_router.callback_query(F.data.startswith("transfer-list_"))
@inject
@commit_and_close_session
async def transfer_list_handler(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        transfer_service: TransferService = Provide[
            Container.transfer_service
        ],
):
    current_user = await telegram_user_service.get_telegram_user(
        user_id=callback.from_user.id
    )
    if not current_user.is_admin:
        return

    callback_data = callback.data.split("_")
    base_callback_data = "_".join(callback_data[0:-1])
    page_number = int(callback_data[-1])
    default_buttons = {"🔙 Назад": "donations",}
    buttons = {}
    sizes = tuple()

    transfer_list = await transfer_service.get_list(
        join_sender=True,
        join_receiver=True,
    )

    paginator = Paginator(
        transfer_list,
        page_number=page_number,
        per_page=10
    )
    page = paginator.get_page()
    if not page:
        buttons.update(default_buttons)
        sizes += (1, ) * len(buttons)
        await callback.message.edit_text(
            "Список пуст.",
            reply_markup=get_donate_keyboard(buttons=buttons, sizes=sizes)
        )
        return 
    message_text = []
    for transfer in page:
        transfer_str = (
            f"ID: {transfer.id}\n"
            f"Сумма: ${transfer.amount}\n"
            f"От кого: @{transfer.sender.username} \n"
            f"Кому: @{transfer.receiver.username} \n"
            f"Дата и время: " +
            to_main_tz(transfer.created_at).strftime("%d.%m.%Y %H:%M") + "\n"
        )
        message_text.append(transfer_str)

    pagination_buttons = get_pagination_buttons(
        paginator,
        base_callback_data,
    )

    buttons.update(pagination_buttons)
    if pagination_buttons:
        sizes += (len(pagination_buttons),)

    buttons.update(default_buttons)
    sizes += (1,) * len(default_buttons)

    await callback.message.edit_text(
        "\n".join(message_text),
        reply_markup=get_donate_keyboard(buttons=buttons, sizes=sizes),
    )


