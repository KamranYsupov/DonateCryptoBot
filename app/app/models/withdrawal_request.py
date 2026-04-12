import uuid

from sqlalchemy import (
    Column,
    Integer,
    Float,
    ForeignKey,
    Enum,
    UUID,
    Boolean,
    BigInteger,
    UniqueConstraint,
    String,
)

from app.db.base import Base
from app.models.mixins import TimestampedMixin, UUIDMixin


class WithdrawalRequest(UUIDMixin, TimestampedMixin, Base):
    """Модель заявки вывода токенов"""

    __tablename__ = "withdrawal_requests"

    telegram_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("telegram_users.id"),
        index=True,
    )
    wallet_address = Column(String)
    tokens_count = Column(Integer)
    is_paid = Column(Boolean, default=False, index=True)


    __table_args__ = {"extend_existing": True}
