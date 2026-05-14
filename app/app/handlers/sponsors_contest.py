from datetime import timedelta, datetime

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
from app.utils.datetime import to_main_tz
from app.utils.pagination import Paginator, get_pagination_buttons
from app.utils.texts import get_period_message

sponsors_contest_router = Router()

@sponsors_contest_router.callback_query(F.data.startswith("sponsors_contest_"))
@sponsors_contest_router.callback_query(F.data == "sponsors_contest")
@inject
@commit_and_close_session
async def current_contest_callback_handler(
        callback: CallbackQuery,
        sponsors_contests_service: SponsorsContestService = Provide[
            Container.sponsors_contests_service
        ],
) -> None:
    buttons = {}
    sizes = tuple()

    try:
        previous_page_number, detail_page_number = map(
            int, callback.data.split("_")[-2:]
        )
        contests_ids = await sponsors_contests_service.get_ids(
            is_archived=True,
        )
        paginator = Paginator(
            contests_ids,
            page_number=detail_page_number,
            per_page=1
        )
        contest_id = paginator.get_page()[0]
        contest = await sponsors_contests_service.get_contest(id=contest_id)
        pagination_buttons = get_pagination_buttons(
            paginator,
            f"sponsors_contest_{previous_page_number}",
        )
        buttons.update(pagination_buttons)
        if pagination_buttons:
            sizes += (len(pagination_buttons),)

        buttons["🔙 Назад"] = f"archive_sponsors_contests_{previous_page_number}"
        sizes += (1, )

        telegram_method = callback.message.edit_text
    except ValueError:
        contest = await sponsors_contests_service.get_current_contest()
        buttons.update({"АРХИВ 🗄": "archive_sponsors_contests_1"})
        telegram_method = callback.message.answer
        await callback.message.delete()


    message_text = get_sponsors_contest_top_10_rating_message(
        contest.top_10_rating,
        contest.start_date
    )

    await telegram_method(
        text=message_text,
        reply_markup=get_donate_keyboard(
            buttons=buttons,
            sizes=sizes,
        ),
    )


@sponsors_contest_router.callback_query(F.data.startswith("archive_sponsors_contests_"))
@inject
@commit_and_close_session
async def archive_contest_callback_handler(
        callback: CallbackQuery,
        sponsors_contests_service: SponsorsContestService = Provide[
            Container.sponsors_contests_service
        ],
) -> None:
    callback_data = callback.data.split("_")
    base_callback_data = "_".join(callback_data[0:-1])
    page_number = int(callback_data[-1])
    per_page = 10
    default_buttons = {"🔙 Назад": "sponsors_contest"}
    buttons = {}
    sizes = tuple()

    contests = await sponsors_contests_service.get_contests_list(
        is_archived=True,
    )
    paginator = Paginator(
        contests,
        page_number=page_number,
        per_page=per_page
    )
    page = paginator.get_page()
    if not page:
        buttons.update(default_buttons)
        sizes += (1,) * len(buttons)
        await callback.message.edit_text(
            "Список пуст.",
            reply_markup=get_donate_keyboard(buttons=buttons, sizes=sizes)
        )
        return

    detail_page_number = contests.index(page[0])
    for contest in page:
        button_text = get_period_message(
            contest.start_date,
            period_days=7
        )
        detail_page_number += 1
        buttons[button_text] = f"sponsors_contest_{page_number}_{detail_page_number}"

    sizes += (1, ) * len(page)

    pagination_buttons = get_pagination_buttons(
        paginator,
        base_callback_data,
    )

    buttons.update(pagination_buttons)
    if pagination_buttons:
        sizes += (len(pagination_buttons),)

    buttons.update(default_buttons)
    sizes += (1,) * len(default_buttons)

    await callback.message.edit_text(
        "Выберите конкурс.",
        reply_markup=get_donate_keyboard(buttons=buttons, sizes=sizes),
    )