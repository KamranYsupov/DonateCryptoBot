import loguru
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

from app.models.telegram_user import DonateStatus, MatrixBuildType, TelegramUser
from app.models.telegram_user import status_list, statuses_colors_data
from app.utils.sort import get_reversed_dict


def get_donate_keyboard(*, buttons: dict[str, str], sizes: tuple = (1, 1)):
    keyboard = InlineKeyboardBuilder()

    for text, data in buttons.items():
        keyboard.add(InlineKeyboardButton(text=text, callback_data=data))

    return keyboard.adjust(*sizes).as_markup()

def get_donations_keyboard() -> dict:
    buttons = {}
    for status in status_list:
        donate_sum = status.get_status_donate_value()
        status_color_emoji = statuses_colors_data.get(status)
        button_text = f"{status_color_emoji} {status.value} - ${donate_sum} {status_color_emoji}"
        buttons[button_text] = f"confirm_donate_🟢_{donate_sum}"


    return get_reversed_dict(buttons)
