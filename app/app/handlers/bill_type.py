from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from dependency_injector.wiring import Provide, inject

from app.keyboards.donate import get_donate_keyboard
from app.schemas.telegram_user import BillType
from app.core.container import Container
from app.services.telegram_user_service import TelegramUserService

bill_type_router = Router()


@bill_type_router.message(Command("transfer"))
@bill_type_router.callback_query(F.data.startswith("confirm_donate_"))
@inject
async def bill_type_handler(
        aiogram_type: Message | CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> None:
    async def send_bill_type_choice(add_back_button: bool = True):
        current_user = await telegram_user_service.get_telegram_user(
            user_id=aiogram_type.from_user.id
        )
        buttons = {
            f"Для вывода ({current_user.bill_for_withdraw})":
                f"{callback_data}_{BillType.WITHDRAW.value}",
            f"Для активации ({current_user.bill_for_activation})":
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
    if "🔴" in callback_data:
        return

    callback_data = "send_" + "_".join(callback_data[1:])
    telegram_method = callback.message.edit_text

    await send_bill_type_choice()


