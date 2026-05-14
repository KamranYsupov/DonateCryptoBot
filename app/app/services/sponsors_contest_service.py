import uuid
from collections import Counter

import loguru

from app.repositories.telegram_user import RepositoryTelegramUser
from app.repositories.contest import RepositorySponsorsContest, RepositorySponsorsContestPoint
from app.models.contest import SponsorsContest, SponsorsContestPoint
from app.utils.datetime import get_start_of_week
from app.models.telegram_user import TelegramUser


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

    async def contest_exists(self, *args, **kwargs) -> bool:
        return self._repository_sponsors_contest.exists(*args, **kwargs)

    async def get_contest(self, *args, **kwargs):
        return self._repository_sponsors_contest.get(*args, **kwargs)

    async def get_contests_list(self, *args, **kwargs):
        return self._repository_sponsors_contest.get_ordered_list(*args, **kwargs)

    async def get_ids(self, *args, **kwargs):
        return self._repository_sponsors_contest.get_ordered_ids(*args, **kwargs)

    async def get_last_contest(self, *args, **kwarg):
        return self._repository_sponsors_contest.get_last(*args, **kwarg)

    async def get_current_contest(self):
        start_of_week = get_start_of_week()
        return self._repository_sponsors_contest.get(
            start_date=start_of_week
        )

    async def get_or_create_current_contest(self) -> tuple[SponsorsContest, bool]:
        current_contest = await self.get_current_contest()
        if current_contest:
            return current_contest, False

        start_of_week = get_start_of_week()
        current_contest = self._repository_sponsors_contest.create(
            {"start_date": start_of_week}
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

    async def update_results(self, contest_id: uuid.UUID):
        contest = self._repository_sponsors_contest.get(id=contest_id)
        if not contest:
            return

        points = await self.get_contests_points(contest_id=contest.id)
        if not points:
            return

        sponsor_ids = {p.sponsor_user_id for p in points}
        sponsors = self._repository_telegram_user.list(
            TelegramUser.user_id.in_(sponsor_ids)
        ) if sponsor_ids else []
        sponsors_map = {s.user_id: s for s in sponsors}
        points_counts = Counter(p.sponsor_user_id for p in points)

        results = {}
        for sponsor_user_id, points_count in points_counts.items():
            sponsor = sponsors_map.get(sponsor_user_id)
            if not sponsor:
                continue
            results[sponsor.user_id] = {
                "points": points_count,
                "full_name": sponsor.full_name,
            }

        sorted_items = sorted(
            results.items(),
            key=lambda x: x[1]["points"],
            reverse=True
        )
        top_10_rating = []
        for place, (sponsor_user_id, sponsor_result) in enumerate(sorted_items, start=1):
            results[sponsor_user_id]["place"] = place

            if place <= 10:
                top_10_rating.append(
                    (sponsor_result["full_name"], sponsor_result["points"])
                )

        update_kwargs = {}

        points_sum = self._repository_sponsors_contest_point.get_count(
            contest_id=contest.id
        )

        updated_prize_fund = contest.init_prize_fund + (points_sum // 10) * 10
        if contest.prize_fund != updated_prize_fund:
            update_kwargs["prize_fund"] = updated_prize_fund

        if contest.top_10_rating != top_10_rating:
            update_kwargs["top_10_rating"] = top_10_rating

        if contest.results != results:
            update_kwargs["results"] = results

        self._repository_sponsors_contest.update(
            obj_id=contest.id,
            obj_in=update_kwargs
        )






