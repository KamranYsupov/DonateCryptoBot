import uuid
import enum

from sqlalchemy import Column, UUID, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import relationship
from sqlalchemy_json import mutable_json_type

from .mixins import UUIDMixin, TimestampedMixin
from app.db.base import Base
from app.models.telegram_user import DonateStatus, MatrixBuildType


class Matrix(UUIDMixin, TimestampedMixin, Base):
    __tablename__ = "matrices"

    owner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("telegram_users.id"),
        default=uuid.uuid4,
        index=True,
    )
    status = Column(Enum(DonateStatus), default=DonateStatus.NOT_ACTIVE, index=True)
    matrices = Column(mutable_json_type(dbtype=JSONB, nested=True), index=True, default={})
    matrix_telegram_usernames = Column(
        mutable_json_type(dbtype=JSONB, nested=True), index=True, default={}
    )
    telegram_users = Column(MutableList.as_mutable(JSONB), index=True, default=[])

    __table_args__ = {"extend_existing": True}


