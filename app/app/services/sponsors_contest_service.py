import time
import uuid
from copy import copy
from datetime import datetime, timedelta
from typing import Tuple, Any, Sequence, Optional
from datetime import date, timedelta
from collections import defaultdict

import loguru
from dependency_injector.wiring import inject

from app.repositories.telegram_user import RepositoryTelegramUser
from app.repositories.contest import RepositorySponsorsContest, RepositorySponsorsContestPoint
from app.models.contest import SponsorsContest, SponsorsContestPoint
from app.utils.datetime import get_start_of_week

from app.app.models.telegram_user import TelegramUser


class SponsorsContestService:
    def __init__(
            self,
            repository_telegram_user: RepositoryTelegramUser,
            repository_sponsors_contest: RepositorySponsorsContest,
            repository_sponsors_contest_point: RepositorySponsorsContestPoint,
    ) -> None:
        self._repository_telegram_user = repository_telegram_user
        self._repository_sponsors_contest = repository_sponsors_contest
        self._repository_sponsors_contest_point = repository_sponsors_contest_point

    async def get_contest(self, *args, **kwargs):
        return self._repository_sponsors_contest.get(*args, **kwargs)

    async def get_contests_list(self, *args, **kwargs):
        return self._repository_sponsors_contest.get_ordered_list(*args, **kwargs)

    async def get_last_contest(self):
        return self._repository_sponsors_contest.get_last()

    async def get_or_create_current_contest(self) -> tuple[SponsorsContest, bool]:
        start_of_week = get_start_of_week()
        current_contest = self._repository_sponsors_contest.get(
            start_at=start_of_week
        )
        if current_contest:
            return current_contest, False

        current_contest = await self._repository_sponsors_contest.create(
            {"start_at": start_of_week}
        )
        return current_contest, True

    async def create_contest_point(self, sponsor_user_id: int) -> SponsorsContestPoint:
        current_contest, _ = await self.get_or_create_current_contest()
        return self._repository_sponsors_contest_point.create({
            "sponsor_user_id": sponsor_user_id,
            "contest_id": current_contest.id,
        })

    async def get_contests_points(self, *args, **kwargs):
        return self._repository_sponsors_contest_point.list(*args, **kwargs)

    async def update_results(self):
        start_of_week = get_start_of_week()
        current_contest = self._repository_sponsors_contest.get(start_at=start_of_week)

        points = await self.get_contests_points(contest_id=current_contest.id)
        if not points:
            return

        sponsor_ids = {p.sponsor_user_id for p in points}
        sponsors = (
            self._repository_telegram_user.list(TelegramUser.user_id.in_(sponsor_ids))
            if sponsor_ids else []
        )
        sponsors_map = {s.user_id: s for s in sponsors}

        results = defaultdict(int)
        for point in points:
            sponsor = sponsors_map.get(point.sponsor_user_id)
            key = f"{sponsor.full_name} ({sponsor.id})"
            results[key] += 1

        results = dict(results)
        self._repository_sponsors_contest.update(obj_id=current_contest.id, obj_in={"results": results})






