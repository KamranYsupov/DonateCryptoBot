from sqlalchemy import Column, UUID, ForeignKey, BigInteger

from .mixins import UUIDMixin, TimestampedMixin
from app.db.base import Base
from app.models.telegram_user import DonateStatus, MatrixBuildType


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