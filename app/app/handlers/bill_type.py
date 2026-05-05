from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from dependency_injector.wiring import Provide, inject

from app.keyboards.donate import get_donate_keyboard
from app.schemas.telegram_user import BillType
from app.core.container import Container
from app.services.telegram_user_service import TelegramUserService
from app.models.telegram_user import status_list
from app.services.donate_service import DonateService

bill_type_router = Router()


@bill_type_router.message(Command("transfer"))
@bill_type_router.callback_query(F.data.startswith("confirm_donate_"))
@bill_type_router.callback_query(F.data == "start_transfer")
@inject
async def bill_type_handler(
        aiogram_type: Message | CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        donate_service: DonateService = Provide[Container.donate_service],
) -> None:
    async def send_bill_type_choice(add_back_button: bool = True):
        current_user = await telegram_user_service.get_telegram_user(
            user_id=aiogram_type.from_user.id
        )
        buttons = {
            f"Для вывода ({current_user.bill_for_withdraw} USDT)":
                f"{callback_data}_{BillType.WITHDRAW.value}",
            f"Для активации ({current_user.bill_for_activation} USDT)":
                f"{callback_data}_{BillType.ACTIVATION.value}",
        }

        if add_back_button:
            buttons["🔙 Назад"] = "donations"

        await telegram_method(
            "Выберите баланс для перевода:",
            reply_markup=get_donate_keyboard(
                buttons=buttons, sizes=(1, 1, 1)
        ))


    if isinstance(aiogram_type, Message):
        telegram_method = aiogram_type.answer
        callback_data = "transfer"
        await send_bill_type_choice(add_back_button=False)
        return

    callback = aiogram_type
    callback_data = callback.data.split("_")
    telegram_method = callback.message.edit_text

    if callback.data.startswith("confirm_donate_"):
        donate_sum = float(callback_data[-1])
        status = donate_service.get_donate_status(donate_sum)
        callback_data = "send_" + "_".join(callback_data[1:])

    elif callback.data.startswith("start_transfer"):
        callback_data = "transfer"
        

    await send_bill_type_choice()


