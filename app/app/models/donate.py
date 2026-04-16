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
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.mixins import TimestampedMixin, UUIDMixin, AbstractTelegramUser
from app.models.telegram_user import MatrixBuildType


class Donate(UUIDMixin, TimestampedMixin, Base):
    """Модель доната"""

    __tablename__ = "donates"

    telegram_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("telegram_users.id"),
        default=None,
        index=True,
    )
    quantity = Column(
        Float,
        default=0,
    )
    matrix_id = Column(
        UUID(as_uuid=True),
        ForeignKey("matrices.id"),
        default=None,
        index=True,
    )

    __table_args__ = {"extend_existing": True}


class DonateTransactionType(enum.Enum):
    SYSTEM = "system"
    SPONSOR = "sponsor"
    MATRIX = "matrix"


class DonateTransaction(UUIDMixin, TimestampedMixin, Base):
    """Модель подтверждения получения доната спонсором"""

    __tablename__ = "donate_transactions"

    sponsor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("telegram_users.id"),
        default=None,
        index=True,
    )
    donate_id = Column(
        UUID(as_uuid=True),
        ForeignKey("donates.id"),
        default=None,
        index=True,
    )
    quantity = Column(
        Float,
        default=0,
    )
    type_ = Column(Enum(DonateTransactionType, name="donate_transaction_enum"))

    __table_args__ = {"extend_existing": True}
