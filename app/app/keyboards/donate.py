import loguru
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

from app.models.telegram_user import DonateStatus, MatrixBuildType, TelegramUser


def get_donate_keyboard(*, buttons: dict[str, str], sizes: tuple = (1, 1)):
    keyboard = InlineKeyboardBuilder()

    for text, data in buttons.items():
        keyboard.add(InlineKeyboardButton(text=text, callback_data=data))

    return keyboard.adjust(*sizes).as_markup()

def get_donations_keyboard(
        current_status: DonateStatus,
        status_list: list[DonateStatus],
) -> dict:
    buttons = {}
    if current_status.value == DonateStatus.NOT_ACTIVE.value:
        first_status = status_list[0]
        first_donate_sum = first_status.get_status_donate_value()
        first_button_text = (
            f"🟢{first_status.value} - ${first_donate_sum}🟢"
        )

        buttons[first_button_text] = f"confirm_donate_🟢_{first_donate_sum}"
        for status in status_list[1:]:
            donate_sum = status.get_status_donate_value()
            button_text = \
                f"🔴{status.value} - ${donate_sum}🔴"
            buttons[button_text] = \
                f"confirm_donate_🔴_{donate_sum}"


        return buttons

    if current_status.value == DonateStatus.GOLD.value:
        for status in status_list:
            emoji = "🟢" if status not in DonateStatus.get_status_list()[-2:] \
                else "🔴"

            donate_sum = status.get_status_donate_value()
            button_text = \
                f"{emoji}{status.value} - ${donate_sum}{emoji}"
            buttons[button_text] = \
                f"confirm_donate_{emoji}_{donate_sum}"

        return buttons

    if current_status.value == DonateStatus.get_status_list()[-1].value:
        for status in status_list:
            donate_sum = status.get_status_donate_value()
            button_text = \
                f"🟢{status.value} - ${donate_sum}🟢"
            buttons[button_text] = \
                f"confirm_donate_🟢_{donate_sum}"

        return buttons

    count = 0
    for status in status_list:
        if current_status.value == status.value:
            for i in status_list[: status_list.index(status)]:
                button_text = (
                    f"🟢{i.value} - "
                    f"${i.get_status_donate_value()}🟢"
                )
                buttons[button_text] = \
                    f"confirm_donate_🟢_{i.get_status_donate_value()}"
                count += 1

            button_text = (
                f"🔴{status.value} - "
                f"${status.get_status_donate_value()}🔴"
            )
            buttons[button_text] = \
                f"confirm_donate_🔴_{status.get_status_donate_value()}"

            donations_data = DonateStatus.get_donations_data()

            buttons[(
                f"🟢{status_list[count + 1].value} - "
                f"${donations_data.get((status_list[count + 1]))}🟢"
            )] = (
                f"confirm_donate_🟢_"
                f"{donations_data.get((status_list[count + 1]))}"
            )

            for i in status_list[status_list.index(status) + 2 :]:
                buttons[
                    f"🔴{i.value} - "
                    f"${i.get_status_donate_value()}🔴"
                ] = (
                    f"confirm_donate_🔴_"
                    f"{i.get_status_donate_value()}"
                )
        else:
            continue

    return buttons
