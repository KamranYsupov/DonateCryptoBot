import copy
from datetime import date, timedelta
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
from app.utils.datetime import to_main_tz


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


def get_matrices_statuses_statistic_message(
        matrices: list[Matrix],
) -> str:
    message = ""
    status_emoji_data = {
        status_list[i]: status_emoji_list[i]
        for i in range(len(status_list))
    }
    statuses_data = {status: 0 for status in status_emoji_list}

    for matrix in matrices:
        if matrix.status == DonateStatus.NOT_ACTIVE:
            continue

        statuses_data[status_emoji_data[matrix.status]] += 1

    for status, count in list(statuses_data.items())[::-1]:
        message += f"{status}: {count}\n"

    return message

def get_matrices_length_statistic_message(
        matrices: list[Matrix],
) -> str:
    message = ""
    sorted_matrices = get_sorted_matrices(matrices, status_list)

    for matrix in sorted_matrices[::-1]:
        if matrix.status == DonateStatus.NOT_ACTIVE:
            continue

        emoji = statuses_colors_data.get(matrix.status)
        message += (
            f"<b>{emoji} {matrix.status.value.upper()}</b>: "
            f"{len(matrix.telegram_users)}/{settings.matrix_max_length}\n"
        )

    return message

def get_user_info_message(user: TelegramUser) -> str:
    created_at_str = to_main_tz(user.created_at).strftime("%d.%m.%Y %H:%M")
    message = (
        f"ID: {html.bold(user.id)}\n\n"
        f"Telegram ID: {html.bold(user.user_id)}\n"
        f"Username: @{user.username}\n"
        f"Полное имя: {html.bold(user.full_name)}\n"
        f"Дата и время регистрации: "
        + html.bold(created_at_str)
    )
    return message


def get_withdrawal_request_info_message(
        withdrawal_request: WithdrawalRequest,
        withdrawal_request_user: TelegramUser,
) -> str:
    created_at_str = \
        to_main_tz(withdrawal_request.created_at).strftime("%d.%m.%Y %H:%M")

    message = (
        f"ID: {html.bold(withdrawal_request.id)}\n\n"
        f"Адрес кошелька: {html.code(withdrawal_request.wallet_address)}\n"
        f"Сеть: {html.bold(withdrawal_request.network.value)}\n"
        f"Сумма: ${html.code(withdrawal_request.tokens_count)}\n"
        f"Пользователь: @{html.bold(withdrawal_request_user.username)}\n"
        f"Подтвержден: " + html.bold("да" if withdrawal_request.is_paid else "нет") + "\n"
        f"Дата и время создания: "
        + html.bold(created_at_str)
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
    color = statuses_colors_data.get(matrix.status)
    lines = [f"<b>{color} {matrix.status.value}: {matrix.id.hex[0:5]}</b>"]
    if not matrix.matrices:
        lines.append(f"\nМест занято: <b>{len(matrix.telegram_users)} из {settings.matrix_max_length}\n</b>")

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

        lines.append(f"\n<b>{level_number}️⃣ Уровень:</b>")
        for obj in level:
            value = "Свободно" if obj is None else "Занято"
            lines.append(f"{counter}) {value}")
            counter += 1

    lines.append(f"\nМест занято: <b>{len(matrix.telegram_users)} из {settings.matrix_max_length}\n</b>")

    return "\n".join(lines)


def get_period_message(
        start_date: date,
        period_days: int,
) -> str:
    end_date = start_date + timedelta(days=period_days - 1)
    start_date_str = start_date.strftime("%d.%m.%Y")
    end_date_str = end_date.strftime("%d.%m.%Y")

    return f"{start_date_str} - {end_date_str}"


def get_sponsors_contest_top_10_rating_message(
        top_10_rating: list[tuple[str, int]],
        start_date: date,
        prize_fund: int,
) -> str:
    lines = []
    if not top_10_rating:
        lines.append("В конкурсе пока нет результатов.")
    else:
        lines.append("<b>🏆 Топ‑10 кураторов</b>\n")

    for place, (full_name, points) in enumerate(top_10_rating):
        try:
            place_emoji = places_emoji_list[place]
        except IndexError:
            break

        lines.append(f"{place_emoji} {full_name} — {points}")

        if place == 2:
            lines.append("")

    period_str = get_period_message(start_date, period_days=7)

    lines.append(f"\n🗓 Период: <b>{period_str}</b>")
    lines.append(f"💰 Призовой фонд: <b>${prize_fund}</b>")

    return "\n".join(lines)

places_emoji_list = (
    "🥇",
    "🥈",
    "🥉",
    "4⃣",
    "5⃣",
    "6⃣",
    "7⃣",
    "8⃣",
    "9⃣",
    "🔟",
)
