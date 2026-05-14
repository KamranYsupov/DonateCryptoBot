from dependency_injector.wiring import inject, Provide

from app.core.container import Container
from app.core.config import settings
from app.db.commit_decorator import commit_and_close_session
from app.models.contest import SponsorsContest
from app.services.sponsors_contest_service import SponsorsContestService


@inject
@commit_and_close_session
async def update_contest_task(
        sponsors_contests_service: SponsorsContestService = Provide[
            Container.sponsors_contests_service
        ],
) -> None:
    current_contest, created = await sponsors_contests_service.get_or_create_current_contest()
    await sponsors_contests_service.update_results(current_contest.id)

    if not created:
        return

    previous_contest = await sponsors_contests_service.get_last_contest(
        SponsorsContest.id != current_contest.id,
        is_archived=False,
    )
    if previous_contest:
        await sponsors_contests_service.update_results(previous_contest.id)
        previous_contest.is_archived = True

