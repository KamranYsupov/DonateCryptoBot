import copy
from typing import Any
from collections import deque
import uuid

from aiogram import html
from dependency_injector.wiring import inject, Provide

from app.models.telegram_user import (
    DonateStatus,
    status_list,
    status_emoji_list,
    statuses_colors_data,
)
from app.models.telegram_user import TelegramUser
from app.models.matrix import Matrix
from app.utils.matrix import find_free_place_in_matrix, get_matrix_levels, get_sorted_matrices, insert_into_matrices
from app.utils.pagination import Paginator
from app.models.telegram_user import MatrixBuildType
from app.core.config import Settings, settings
from app.models.matrix import Matrix
from app.core.config import Settings
from app.models.matrix import Matrix
from app.models.withdrawal_request import WithdrawalRequest
from app.core.container import Container
from app.models.donate import DonateTransactionType
from app.services.donate_service import DonateService


def get_donate_confirm_message(
        donate_sum: int,
        donate_status: DonateStatus,
) -> str | None:
    if donate_status not in list(statuses_colors_data.keys()):
        return
    status = (
        f"{statuses_colors_data.get(donate_status)} - {donate_status.value.split()[0]}"
    )

    message_text = (
        f"💌 Участник получил 🎁 ${donate_sum}\n\n"
        f"🛗 Уровень: {status}\n\n"
        "🤝 Будем «НА СВЯЗИ»"
    )

    return message_text


def get_user_statuses_statistic_message(
        users: list[TelegramUser],
) -> str:
    status_emoji_data = {
        status_list[i]: status_emoji_list[i]
        for i in range(len(status_list))
    }
    statuses_data = {"🆓": 0}
    statuses_data.update({status: 0 for status in status_emoji_list})

    for user in users:
        if user.status == DonateStatus.NOT_ACTIVE:
            statuses_data["🆓"] += 1
            continue

        statuses_data[status_emoji_data[user.status]] += 1

    message = ""

    for status, count in list(statuses_data.items())[::-1]:
        message += f"{status}: {count}\n"

    return message


def get_user_info_message(user: TelegramUser) -> str:
    message = (
        f"ID: {html.bold(user.id)}\n\n"
        f"Telegram ID: {html.bold(user.user_id)}\n"
        f"Username: @{user.username}\n"
        f"Полное имя: {html.bold(user.full_name)}\n"
        f"Дата и время регистрации: "
        + html.bold(user.created_at.strftime("%d.%m.%Y %H:%M"))
    )
    return message


def get_withdrawal_request_info_message(
        withdrawal_request: WithdrawalRequest,
        withdrawal_request_user: TelegramUser,
) -> str:
    message = (
        f"ID: {html.bold(withdrawal_request.id)}\n\n"
        f"Адрес кошелька: {html.code(withdrawal_request.wallet_address)}\n"
        f"Сумма: ${html.code(withdrawal_request.tokens_count)}\n"
        f"Пользователь: @{html.bold(withdrawal_request_user.username)}\n"
        f"Подтвержден: " + html.bold("да" if withdrawal_request.is_paid else "нет") + "\n"
        f"Дата и время создания: "
        + html.bold(withdrawal_request.created_at.strftime("%d.%m.%Y %H:%M"))
    )
    return message


def get_my_team_message(
        matrices: list[Matrix],
        page_number: int,
        per_page: int = 1,
        callback_data_prefix: str = "team",
        previous_page_number: int | None = None,

):
    message = ""
    sorted_matrices = get_sorted_matrices(matrices, status_list)
    paginator = Paginator(
        sorted_matrices,
        page_number=page_number,
        per_page=per_page
    )
    buttons = {}
    sizes = (1, 1)

    if len(paginator.get_page()):
        matrices = paginator.get_page()

        for matrix in matrices:
            message += get_matrix_info_message(matrix)
            message += "—————————\n\n" if matrix != matrices[-1] else ""
    else:
        message += "У вас нет активированных уровней"

    pagination_button_data = (
            f"{callback_data_prefix}_"
            + "{page_number}"
            + (f"_{previous_page_number}" if previous_page_number else "")
    )

    if paginator.has_previous():
        buttons |= {"◀ Пред.": pagination_button_data.format(page_number=page_number - 1)}
    if paginator.has_next():
        buttons |= {"След. ▶": pagination_button_data.format(page_number=page_number + 1)}

    if len(buttons) == 2:
        sizes = (2, 1)

    return message, page_number, buttons, sizes


def get_matrix_info_message(
        matrix: Matrix,
        level_length: int = settings.level_length,
):
    """
    Выводит бинарное дерево матрицы.
    """
    lines = [f"<b>Уровень {matrix.id.hex[0:5]}: {matrix.status.value}</b>"]
    if not matrix.matrices:
        lines.append("\nВсе места свободны\n")

        return "\n".join(lines)
    counter = 1

    matrices = copy.deepcopy(matrix.matrices)

    matrix_len = len(matrix.telegram_users)
    while matrix_len != settings.matrix_max_length:
        free_place_path = find_free_place_in_matrix(matrices, level_length)
        free_place_level = len(free_place_path) + 1

        insert_into_matrices(
            matrices, 
            free_place_path,
            free_place_level,
            f"none_{uuid.uuid4()}"
        )
        matrix_len += 1

    levels_data = get_matrix_levels(matrices)
    for level_number in sorted(levels_data.keys()):
        if level_number > settings.matrix_max_level:
            break
        level = levels_data[level_number]

        lines.append(f"\n<b>{level_number} Уровень:</b>")
        for obj in level:
            value = "Свободно" if obj is None else "Занято"
            lines.append(f"{counter}) {value}")
            counter += 1


    lines.append(f"\nВсего участников: <b>{len(matrix.telegram_users)}</b>\n")

    return "\n".join(lines)

def get_transaction_message(
        quantity: float | int,
        type_: DonateTransactionType,
        sender: TelegramUser,
        status: DonateStatus,
) -> str:
    if type_ == DonateTransactionType.SYSTEM:
        return f"Системный аккаунт <b>${quantity}</b>."

    template = "Вам подарок <b>${0}</b> {1}площадка {2}."

    sponsor_text = (
        f"от партнера первой линии @{sender.username} "
        if type_ == DonateTransactionType.SPONSOR else ""
    )

    return template.format(quantity, sponsor_text, status.value)

