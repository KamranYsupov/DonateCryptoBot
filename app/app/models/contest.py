import enum

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
    Date,
    text,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import relationship
from sqlalchemy_json import mutable_json_type

from app.db.base import Base
from app.models.mixins import TimestampedMixin, UUIDMixin


class SponsorsContest(Base, UUIDMixin):

    __tablename__ = "sponsors_contests"

    start_date = Column(Date, unique=True, index=True)
    prize_fund = Column(Integer, default=100, server_default=text("100"))
    init_prize_fund = Column(Integer, default=100, server_default=text("100"))
    top_10_rating = Column(MutableList.as_mutable(JSONB), default=list)
    results = Column(MutableDict.as_mutable(JSONB), index=True, default=dict)
    is_archived = Column(Boolean, default=False)


class SponsorsContestPoint(Base, TimestampedMixin, UUIDMixin):

    __tablename__ = "sponsors_contest_points"

    sponsor_user_id = Column(
        BigInteger,
        ForeignKey("telegram_users.user_id"),
        index=True,
    )
    contest_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sponsors_contests.id"),
        index=True,
    )

    contest = relationship(
        "SponsorsContest",
        remote_side="SponsorsContest.id",
        backref="points"
    )



