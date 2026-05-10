from aiogram import F, Router
from aiogram.types import CallbackQuery
from dependency_injector.wiring import inject, Provide

from app.core.container import Container
from app.db.commit_decorator import commit_and_close_session
from app.keyboards.donate import get_donate_keyboard
from app.models.contest import SponsorsContest
from app.services.sponsors_contest_service import SponsorsContestService
from app.services.telegram_user_service import TelegramUserService
from app.utils.texts import get_sponsors_contest_top_10_rating_message

sponsors_contest_router = Router()

@sponsors_contest_router.callback_query(F.data.startswith("current_sponsors_contest"))
@inject
@commit_and_close_session
async def current_contest_callback_handler(
        callback: CallbackQuery,
        sponsors_contests_service: SponsorsContestService = Provide[
            Container.sponsors_contests_service
        ],
) -> None:
    contest = await sponsors_contests_service.get_current_contest()
    is_archive_contests_exist = (
        await sponsors_contests_service.contest_exists(
            SponsorsContest.id != contest.id
        )
    )

    message_text = get_sponsors_contest_top_10_rating_message(contest.top_10_rating)
    reply_markup = get_donate_keyboard(
        buttons={
            "АРХИВ 🗄": "archive_sponsors_contests_1",
        }
    ) if is_archive_contests_exist else None

    await callback.message.delete()
    await callback.message.answer(
        text=message_text,
        reply_markup=reply_markup,
    )
