from sqlalchemy import (
    Column,
    UUID,
    Float,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.mixins import TimestampedMixin, UUIDMixin


class Transaction(UUIDMixin, TimestampedMixin, Base):
    """Модель транзакции"""

    __tablename__ = "transactions"

    amount = Column(Float)
    telegram_user_id = Column(UUID, ForeignKey("telegram_users.id"))

    telegram_user = relationship("TelegramUser", back_populates="transactions")

    def __repr__(self) -> str:
        return f"Транзакция: {self.id}"

    __table_args__ = {"extend_existing": True}
