from sqlalchemy import Column, UUID, ForeignKey, BigInteger
from sqlalchemy.orm import relationship

from .mixins import UUIDMixin, TimestampedMixin
from app.db.base import Base


class Transfer(UUIDMixin, TimestampedMixin, Base):
    __tablename__ = "transfers"

    from_id = Column(
        UUID(as_uuid=True),
        ForeignKey("telegram_users.id"),
        index=True,
    )
    to_id = Column(
        UUID(as_uuid=True),
        ForeignKey("telegram_users.id"),
        index=True,
    )
    amount = Column(BigInteger, index=True)

    sender = relationship(
        "TelegramUser",
        foreign_keys=[from_id],
        back_populates="sent_transfers",
        lazy="joined",
    )
    receiver = relationship(
        "TelegramUser",
        foreign_keys=[to_id],
        back_populates="received_transfers",
        lazy="joined",
    )