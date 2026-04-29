from io import BytesIO

import pandas as pd
from dependency_injector.wiring import inject, Provide

from app.core.container import Container
from app.models.telegram_user import TelegramUser
from app.services.telegram_user_service import TelegramUserService
from openpyxl.utils import get_column_letter


@inject
async def export_users_to_excel(
        file_name: str,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
):
    """
    Экспортирует данные пользователй в Excel.
    """
    data = []

    users: list[TelegramUser] = await telegram_user_service.get_list(
        is_bot=False,
        join_sponsor=True
    )
    count = 1

    for user in users:
        data.append({
            "Порядок": count,
            "Уровень глубины": user.depth_level,
            "Логин ТГ": user.username,
            "Имя фамилия": user.full_name,
            "Логин тг пригласителя": user.sponsor,
            "Статус": user.status.value,
            "Кол-во приглашенных": user.invites_count,
            "Баланс для активации": user.bill_for_activation,
            "Баланс для вывода": user.bill_for_withdraw,
            "Всего заработано": user.donates_sum,
            "Tg ID": user.user_id,
            "Дата время регистрации": \
                user.created_at.strftime("%d.%m.%Y %H:%M")
        })
        count += 1

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

        # Получаем активный лист
        worksheet = writer.sheets['Sheet1']

        # Устанавливаем ширину столбцов
        for idx, col in enumerate(df.columns):
            max_length = max(df[col].astype(str).map(len).max(), len(col))  # Максимальная длина
            adjusted_width = (max_length + 2)  # Добавляем немного пространства
            worksheet.column_dimensions[get_column_letter(idx + 1)].width = adjusted_width

    with open(file_name, 'wb') as f:
        f.write(output.getvalue())