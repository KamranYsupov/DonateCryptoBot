import enum
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


class WalletAddressType(enum.Enum):
    TON = "TON"
    BEP20 = "BEP20"
    SOLANA = "SOLANA"


class WithdrawalRequest(UUIDMixin, TimestampedMixin, Base):
    """Модель заявки вывода токенов"""

    __tablename__ = "withdrawal_requests"

    telegram_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("telegram_users.id"),
        index=True,
    )
    wallet_address = Column(String)
    wallet_address_type = Column(
        Enum(WalletAddressType),
        default=WalletAddressType.TON,
        server_default=WalletAddressType.TON.value,
        nullable=False,
    )
    tokens_count = Column(Integer)
    is_paid = Column(Boolean, default=False, index=True)


    __table_args__ = {"extend_existing": True}
