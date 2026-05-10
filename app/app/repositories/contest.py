import uuid
from typing import List

from sqlalchemy import select, delete, update, func
from sqlalchemy.orm import selectinload

from .base import RepositoryBase
from app.models.contest import SponsorsContest, SponsorsContestPoint


class RepositorySponsorsContest(RepositoryBase[SponsorsContest]):
    """Репозиторий конкурса кураторов"""

    def get_ordered_list(self, *args, **kwargs):
        statement = (
            select(SponsorsContest)
            .filter(*args)
            .filter_by(**kwargs)
            .order_by(SponsorsContest.start_date)
        )
        return self._session.execute(statement).scalars().all()

    def get_last(self, *args, **kwargs):
        statement = (
            select(SponsorsContest)
            .filter(*args)
            .filter_by(**kwargs)
            .order_by(SponsorsContest.start_date)
        )

        return self._session.execute(statement).scalars().first()


class RepositorySponsorsContestPoint(RepositoryBase[SponsorsContestPoint]):
    """Репозиторий балла конкурса кураторов"""
