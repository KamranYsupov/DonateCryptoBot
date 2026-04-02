import uuid
from pydantic import BaseModel, Field

from app.models.telegram_user import DonateStatus, MatrixBuildType


class MatrixEntity(BaseModel):
    """Модель пользователя"""

    owner_id: uuid.UUID = Field(title="ID владельца")
    status: DonateStatus | str = Field(title="Статус доната")
