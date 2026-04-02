from aiogram.types import Message

from app.models.telegram_user import DonateStatus, status_list
from app.keyboards.donate import get_donate_keyboard
from app.models.telegram_user import TelegramUser


def get_callback_value(callback_data: str) -> str:
    callback_value = callback_data.split("_")[-1]
    return callback_value


def check_is_second_status_higher(status_1: DonateStatus, status_2: DonateStatus) -> bool:
    if status_1 == DonateStatus.NOT_ACTIVE:
        return True

    expression = (
        status_2.get_status_donate_value() > status_1.get_status_donate_value()
    )

    return expression




