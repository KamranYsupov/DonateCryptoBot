from typing import Any
from collections import deque

from aiogram import html

from app.models.telegram_user import (
    DonateStatus,
    status_list,
    status_emoji_list,
    statuses_colors_data,
)
from app.models.telegram_user import TelegramUser
from app.models.matrix import Matrix
from app.utils.matrix import get_sorted_matrices
from app.utils.pagination import Paginator
from app.models.telegram_user import MatrixBuildType
from app.core.config import Settings, settings
from app.models.matrix import Matrix
from app.core.config import Settings
from app.models.matrix import Matrix


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
        f"💌 Участник получил 🎁 ${int(donate_sum)}\n\n"
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
        level_length: int =settings.level_length,
        max_level=settings.matrix_max_level,
):
    """
    Выводит бинарное дерево матрицы.
    """
    lines = [f"<b>Уровень {matrix.id.hex[0:5]}: {matrix.status.value}</b>"]
    if not matrix.matrices:
        lines.append("\nВсе места свободны\n")

        return "\n".join(lines)
    queue = deque([(matrix.matrices, 1)])
    counter = 0
    current_level = 0

    while queue:
        node, level = queue.popleft()

        if level != current_level:
            current_level = level
            lines.append(f"\n<b>{level}) уровень:</b>")

        if node is None:
            counter += 1
            lines.append(f"{counter}) Свободно")
            if level < max_level:
                for _ in range(level_length):
                    queue.append((None, level + 1))
            continue

        if isinstance(node, dict):
            keys = list(node.keys())
            for i in range(level_length):
                if i < len(keys):
                    counter += 1
                    key = keys[i]
                    lines.append(f"{counter}) Занято")
                    queue.append((node[key], level + 1))
                else:
                    counter += 1
                    lines.append(f"{counter}) Свободно")
                    if level < max_level:
                        for _ in range(level_length):
                            queue.append((None, level + 1))

        elif isinstance(node, list):
            for val in node:
                counter += 1
                lines.append(f"{counter}) {val}")
            free_slots = level_length - len(node)
            for _ in range(free_slots):
                counter += 1
                lines.append(f"{counter}) Свободно")
                if level < max_level:
                    for _ in range(level_length):
                        queue.append((None, level + 1))

    lines.append(f"\nВсего участников: <b>{len(matrix.telegram_users)}</b>\n\n")

    return "\n".join(lines)
