import enum
import random
import uuid

from pydantic import BaseModel, Field

from app.models.telegram_user import DonateStatus


class TelegramUserEntity(BaseModel):
    """Модель пользователя"""

    user_id: int = Field(title="ID пользователя")
    username: str | None = Field(title="Username", default=None)
    first_name: str | None = Field(title="Имя", default=None)
    last_name: str | None = Field(title="Фамилия", default=None)
    sponsor_user_id: int | None = Field(title="ID спонсора", default=None)
    status: DonateStatus | str = Field(
        title="Статус", default=DonateStatus.NOT_ACTIVE
    )
    invites_count: int = Field(title="Число приглашений", default=0)
    donates_sum: int = Field(title="Сумма донатов", default=0)
    bill_for_activation: int = Field(title="Счет для активации", default=0)
    bill_for_withdraw: int = Field(title="Счет для вывода", default=0)
    is_bot: bool = Field(title="Бот", default=False)
    is_admin: bool = Field(title="Супер пользователь", default=False)
    depth_level: int = Field(title="Уровень глубины")
    is_banned: bool = Field(title="Заблокирован", default=False)


class BillType(enum.Enum):
    ACTIVATION = "activation"
    WITHDRAW = "withdraw"


def generate_random_user():
    return TelegramUserEntity(
        user_id=random.randint(1, 100000000),
        username=f"user_{random.randint(1, 100000000)}",
        first_name=f"User{random.randint(1, 100)}",
        last_name=f"LastName{random.randint(1, 100)}",
        depth_level=0,
    )

