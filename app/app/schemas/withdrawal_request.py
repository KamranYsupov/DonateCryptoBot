from uuid import UUID

from pydantic import BaseModel, Field

from app.models.withdrawal_request import WithdrawalRequest

class WithdrawalRequestEntity(BaseModel):
    telegram_user_id: UUID | str = Field(title="ID пользователя")
    wallet_address: str
    tokens_count: int
    is_paid: bool = False