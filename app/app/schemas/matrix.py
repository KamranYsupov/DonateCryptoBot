import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.telegram_user import DonateStatus, MatrixBuildType


class MatrixEntity(BaseModel):
    """Модель пользователя"""

    owner_id: uuid.UUID = Field(title="ID владельца")
    status: DonateStatus | str = Field(title="Статус доната")


class AddBotToMatrixTaskEntity(BaseModel):
    execute_at: datetime
    is_executed: bool = False
    donate_sum: int
    matrix_id: uuid.UUID