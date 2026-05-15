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
from aiogram.types import CallbackQuery, ReplyKeyboardRemove
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
from app.keyboards.reply import get_reply_keyboard, reply_cancel_keyboard
from app.services.withdrawal_request import WithdrawalRequestService
from app.schemas.withdrawal_request import WithdrawalRequestEntity
from app.models.withdrawal_request import WithdrawalRequest
from app.utils.pagination import Paginator, get_pagination_buttons
from app.utils.texts import get_withdrawal_request_info_message
from app.validators.crypto_wallets import ValidateWalletAddress
from app.models.withdrawal_request import CryptoNetworkType
from app.utils.bot import send_message_or_pass

withdrawal_requests_router = Router()

class WithdrawalRequestState(StatesGroup):
    network = State()
    wallet_address = State()
    tokens_count = State()
    confirm_sending = State()


@withdrawal_requests_router.callback_query(F.data == "withdrawal_request")
async def withdrawal_request_handler(
        callback: CallbackQuery,
        state: FSMContext,
) -> None:
    await state.set_state(WithdrawalRequestState.network)

    buttons = {
        f"USDT {network.value}": f"network_{network.value}"
        for network in CryptoNetworkType.__members__.values()
    }

    await callback.message.delete()
    await callback.message.answer(
        "Выберите в какой сети вы хотите совершить вывод:",
        reply_markup=get_donate_keyboard(
            buttons=buttons,
            sizes=(1,) * len(buttons),
        ),
    )

@withdrawal_requests_router.callback_query(
    F.data.startswith("network_"),
    WithdrawalRequestState.network,
)
async def network_withdrawal_request_handler(
        callback: CallbackQuery,
        state: FSMContext,
) -> None:
    network = callback.data.split("_")[-1].upper()
    await state.update_data(network=CryptoNetworkType[network])
    await state.set_state(WithdrawalRequestState.wallet_address)
    await callback.message.delete()
    await callback.message.answer(
        f"Отправьте адрес кошелька USDT в сети {network}.\n\n"
        "<b>Важно:</b> <em>при указании неверного адреса средства будут утеряны</em>.",
        reply_markup=reply_cancel_keyboard,
    )


@withdrawal_requests_router.message(F.text, WithdrawalRequestState.wallet_address)
@inject
async def process_wallet_address(
        message: Message,
        state: FSMContext,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> None:
    wallet_address = message.text
    state_data = await state.get_data()

    if not ValidateWalletAddress(wallet_address, network=state_data["network"])():
        await message.answer(
            "❌ Некорректный ввод."
        )
        return

    await state.update_data(wallet_address=wallet_address)
    await state.set_state(WithdrawalRequestState.tokens_count)

    telegram_user = await telegram_user_service.get_telegram_user(
        user_id=message.from_user.id
    )
    await message.answer(
        f"Отправьте количесто USDT для вывода(всего <b>{int(telegram_user.bill_for_withdraw)}</b>)."
    )


@withdrawal_requests_router.message(F.text, WithdrawalRequestState.tokens_count)
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

    if tokens_count < settings.withdrawal_min_tokens_count:
        await message.answer(
            f"Минимальная сумма для вывода {int(settings.withdrawal_min_tokens_count)}"
        )
        return

    telegram_user = await telegram_user_service.get_telegram_user(
        user_id=message.from_user.id
    )

    if tokens_count > telegram_user.bill_for_withdraw:
        await message.answer(
            "❌ Некорректный ввод. Число превышает сумму на балансе."
        )
        return

    await state.update_data(tokens_count=tokens_count)
    await state.set_state(WithdrawalRequestState.confirm_sending)

    await message.answer("✍️", reply_markup=get_reply_keyboard(telegram_user))
    await message.answer(
        "Вы уверены? "
        "После создания заявки указанное число спишется с вашего баланса.",
        reply_markup=get_donate_keyboard(
            buttons={
                "Да": f"send_withdrawal_request",
                "Нет": "cancel",
            },
            sizes=(1, 1)
        )
    )


@withdrawal_requests_router.callback_query(
    F.data == "send_withdrawal_request",
    WithdrawalRequestState.confirm_sending
)
@inject
@commit_and_close_session
async def send_withdrawal_request_handler(
        callback: CallbackQuery,
        state: FSMContext,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        withdrawal_request_service: WithdrawalRequestService = Provide[
            Container.withdrawal_request_service
        ],
) -> None:
    telegram_user = await telegram_user_service.get_telegram_user(
        user_id=callback.from_user.id
    )

    state_data = await state.get_data()

    if state_data["tokens_count"] > telegram_user.bill_for_withdraw:
        await callback.message.edit_text(
            "❌ Число превышает сумму на балансе.",
        )
        await state.clear()
        return

    await withdrawal_request_service.create_withdrawal_request(
        WithdrawalRequestEntity(
            telegram_user_id=telegram_user.id,
            **state_data,
        )
    )
    telegram_user.bill_for_withdraw -= state_data["tokens_count"]
    await state.clear()
    await callback.message.edit_text(
        "Заявка на вывод средств отправлена ✅. Средства поступят в течение 24 часов.",
    )


@withdrawal_requests_router.callback_query(F.data.startswith("withdrawal_requests_"))
async def withdrawal_requests_handler(
        callback: CallbackQuery,
) -> None:
    return await get_withdrawal_requests_message(callback, archive=False)


@withdrawal_requests_router.callback_query(F.data.startswith("archive_withdrawal_requests_"))
async def archive_withdrawal_requests_handler(
        callback: CallbackQuery,
) -> None:
    return await get_withdrawal_requests_message(callback, archive=True)


@inject
async def get_withdrawal_requests_message(
        callback: CallbackQuery,
        archive: bool = False,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        withdrawal_request_service: WithdrawalRequestService = Provide[
            Container.withdrawal_request_service
        ],
) -> None:
    callback_data = callback.data.split("_")
    base_callback_data = "_".join(callback_data[0:-1])
    page_number = int(callback_data[-1])

    buttons = {}
    order_by = []
    default_buttons = {}

    if archive:
        is_paid = True
        order_by.append(WithdrawalRequest.created_at.desc())
        back_button_data = "_".join(callback.data.split("_")[1:-1])
        sizes = tuple()
    else:
        is_paid = False
        order_by.append(WithdrawalRequest.created_at)
        back_button_data = "donations"
        default_buttons["АРХИВ"] = f"archive_{callback.data}_1"
        sizes = (1, )

    default_buttons["🔙 Назад"] = back_button_data

    withdrawal_requests_exists = await withdrawal_request_service.withdrawal_requests_exists(
        is_paid=is_paid,
    )
    if not withdrawal_requests_exists:
        buttons.update(default_buttons)
        sizes = (1,) * len(buttons)
        await callback.message.edit_text(
            "Список пуст.",
            reply_markup=get_donate_keyboard(
                buttons=buttons,
                sizes=sizes
            ),
        )
        return

    withdrawal_requests = await withdrawal_request_service.get_withdrawal_requests(
        order_by=order_by,
        is_paid=is_paid,
    )
    paginator = Paginator(
        withdrawal_requests,
        page_number=page_number,
        per_page=1
    )
    withdrawal_request = paginator.get_page()[0]
    withdrawal_request_user = await telegram_user_service.get_telegram_user(
        id=withdrawal_request.telegram_user_id
    )
    page_message_text = get_withdrawal_request_info_message(
        withdrawal_request,
        withdrawal_request_user
    )

    if not withdrawal_request.is_paid:
        buttons["Подтвердить ☑️"] = f"pay_withdrawal_{withdrawal_request.id}_{page_number}"

    pagination_buttons = get_pagination_buttons(
        paginator,
        base_callback_data,
    )
    buttons.update(pagination_buttons)

    buttons.update(pagination_buttons)
    if pagination_buttons:
        sizes += (len(pagination_buttons),)

    buttons.update(default_buttons)
    sizes += (1, ) * len(default_buttons)

    await callback.message.edit_text(
        page_message_text,
        reply_markup=get_donate_keyboard(buttons=buttons, sizes=sizes),
        parse_mode="HTML",
    )



@withdrawal_requests_router.callback_query(F.data.startswith("pay_withdrawal_"))
@inject
async def pay_withdrawal_callback_handler(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        withdrawal_request_service: WithdrawalRequestService = Provide[
            Container.withdrawal_request_service
        ],
) -> None:
    withdrawal_request_id = callback.data.split('_')[-2]
    page_number = int(callback.data.split('_')[-1])
    other_page_number = page_number - 1 if page_number > 1 else page_number

    await callback.message.edit_text(
        text="<b>Вы уверенны?</b>",
        reply_markup=get_donate_keyboard(
            buttons={
                "Да": f"conf_withdrawal_{withdrawal_request_id}_{other_page_number}",
                "Нет": f"withdrawal_requests_{page_number}",
            },
            sizes=(1, 1)
        )
    )


@withdrawal_requests_router.callback_query(F.data.startswith("conf_withdrawal_"))
@inject
@commit_and_close_session
async def confirm_withdrawal_callback_handler(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        withdrawal_request_service: WithdrawalRequestService = Provide[
            Container.withdrawal_request_service
        ],
) -> None:
    withdrawal_request_id, page_number = callback.data.split('_')[-2:]

    withdrawal_request = await withdrawal_request_service.get_withdrawal_request(
        id=withdrawal_request_id
    )
    reply_markup = get_donate_keyboard(
        buttons={"🔙 Назад": f"withdrawal_requests_{page_number}"}
    )

    if withdrawal_request.is_paid:
        await callback.message.edit_text(
            f"Запрос на вывод уже подтвежден.",
            reply_markup=reply_markup,
        )
        return


    withdrawal_request.is_paid = True
    await callback.message.edit_text(
        f"Запрос на вывод успешно подтвежден ✅",
        reply_markup=reply_markup,
    )

    telegram_user = await telegram_user_service.get_telegram_user(
        id=withdrawal_request.telegram_user_id,
    )
    await send_message_or_pass(
        bot=callback.bot,
        chat_id=telegram_user.user_id,
        text=f"{withdrawal_request.tokens_count} USDT отправлены на указанный вами счет."
    )
