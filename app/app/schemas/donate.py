import uuid

from pydantic import BaseModel, Field

from app.models.donate import DonateTransactionType


class DonateEntity(BaseModel):
    """Представление модели Donate"""

    telegram_user_id: uuid.UUID = Field(title="ID пользователя")
    quantity: float = Field(title="Размер доната")
    matrix_id: uuid.UUID = Field(title="ID матрицы")


class DonateTransactionEntity(BaseModel):
    sponsor_id: uuid.UUID = Field(title="ID спонсора")
    donate_id: uuid.UUID = Field(title="ID доната")
    quantity: float = Field(title="Размер доната")
    type_: DonateTransactionType
