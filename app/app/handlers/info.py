import loguru
from aiogram import Router, F, html
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from dependency_injector.wiring import inject, Provide

from app.core.container import Container
from app.services.telegram_user_service import TelegramUserService
from app.keyboards.donate import get_donate_keyboard
from app.core.config import settings
from app.services.matrix_service import MatrixService
from app.utils.sponsor import get_callback_value
from app.utils.pagination import Paginator
from app.utils.matrix import get_matrices_length
from app.utils.matrix import get_active_matrices, get_archived_matrices
from app.models.telegram_user import status_list, status_emoji_list
from app.db.commit_decorator import commit_and_close_session
from app.utils.texts import get_my_team_message, get_matrix_info_message
from app.models.telegram_user import MatrixBuildType
from app.models.telegram_user import TelegramUser

info_router = Router()


@info_router.message(F.text == "KOD💵DENEG")
@inject
async def about_handler(
        message: Message,
) -> None:
    base_photo = FSInputFile("app/media/base_photo.jpg")

    presentation_keyboard = InlineKeyboardBuilder()
    presentation_keyboard.add(
        InlineKeyboardButton(
            text="🎬 Фильм «KOD 💵 DENEG»",
            url="https://t.me/kod_deneg_film/15"
        ),
        InlineKeyboardButton(
            text="📎 Инструкция к фильму",
            url="https://t.me/kod_deneg_film/12"
        ),
        InlineKeyboardButton(
            text="📌 Канал сообщества",
            url=settings.channel_link
        ),
        InlineKeyboardButton(
            text="💬 Чат сообщества",
            url=settings.chat_link
        ),
    )
    presentation_keyboard.add()

    await message.answer_photo(
        photo=base_photo,
        reply_markup=presentation_keyboard.adjust(1).as_markup(),
    )


@info_router.callback_query(F.data.startswith("team_"))
@info_router.callback_query(F.data.startswith("archive_team_"))
@inject
async def team_inline_handler(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        matrix_service: MatrixService = Provide[Container.matrix_service],
) -> None:
    callback_data_list = callback.data.split("_")
    is_archive = callback_data_list[0] == "archive"


    current_user = await telegram_user_service.get_telegram_user(
        user_id=callback.from_user.id
    )
    matrices = await matrix_service.get_user_matrices(
        owner_id=current_user.id,
    )
    archived_matrices = get_archived_matrices(matrices)

    if is_archive:
        matrices = archived_matrices
        title_text = "АРХИВ УРОВНЕЙ:"
        page_number, previous_page_number = \
            map(int, callback.data.split("_")[-2:])
        callback_data_prefix = f"archive_team"
        back_button_data = f"team_{previous_page_number}"
    else:
        matrices = get_active_matrices(matrices)
        title_text = "АКТИВНЫЕ ПЛОЩАДКИ:"
        page_number = int(callback.data.split("_")[-1])
        previous_page_number = None
        callback_data_prefix = f"team"
        back_button_data = f"donations"


    message, page_number, buttons, sizes = get_my_team_message(
        matrices=matrices,
        page_number=page_number,
        previous_page_number=previous_page_number,
        callback_data_prefix=callback_data_prefix
    )
    message = f"<b>{title_text}</b>\n\n" + message


    if not is_archive and archived_matrices:
        buttons["АРХИВ УРОВНЕЙ 🗄"] = f"archive_team_1_{page_number}"

    buttons["🔙 Назад"] = back_button_data

    await callback.message.edit_text(
        message,
        reply_markup=get_donate_keyboard(buttons=buttons, sizes=sizes),
        parse_mode="HTML",
    )


@info_router.callback_query(F.data.startswith("detail_matrix_"))
@inject
async def team_inline_handler(
        callback: CallbackQuery,
        matrix_service: MatrixService = Provide[Container.matrix_service],
) -> None:
    matrix_id = callback.data.split("_")[-1]
    matrix = await matrix_service.get_matrix(
        id=matrix_id
    )

    message_text = get_matrix_info_message(matrix)
    await callback.message.edit_text(text=message_text)



@info_router.message(F.text == "🚀 Продвижение")
async def referral_message_handler(message: Message):
    photo = FSInputFile("app/media/base_photo.jpg")
    keyboard = InlineKeyboardBuilder()
    registration_link = f"{settings.bot_link}?start={message.from_user.id}"
    registration_button = InlineKeyboardButton(
        text="🔑 Получить доступ",
        url=registration_link
    )
    keyboard.add(registration_button)
    await message.answer_photo(
        photo=photo,
        caption=(
            "🎬 «Код Денег» — нейронаучный фильм. Никаких сложных техник. "
            "Просто берёшь бумагу, пишешь желаемую сумму. И смотришь видео.\n\n"
            "🧠 Без магии. Без усилий. Твой мозг сам переключается из дефицита в изобилие."
            " Ты начинаешь замечать деньги там, где раньше видел стены.\n\n"
            "📎 Всё, что нужно — фильм, инструкция и чат. Внутри бота."
        ),
        reply_markup=keyboard.as_markup(),
    )
    await message.answer(
        f"Ваша реферальная ссылка: {registration_link}",
    )



@inject
async def referral_handler(
        current_user: TelegramUser,
        page_number=1,
        per_page=20,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> tuple[str | None, InlineKeyboardMarkup | None]:
    invited_users = await telegram_user_service.get_invited_users(
        sponsor_user_id=current_user.user_id
    )
    default_buttons = {}

    if not invited_users:
        return "У вас пока нет реферралов.", get_donate_keyboard(buttons=default_buttons)

    paginator = Paginator(
        invited_users,
        page_number=page_number,
        per_page=per_page
    )

    buttons = {}
    message_text = f"<b>Ваши рефералы (страница {page_number}):</b>\n\n"
    status_emoji_data = {
        status_list[i]: status_emoji_list[i]
        for i in range(len(status_list))
    }

    if paginator.has_previous():
        buttons |= {"◀ Пред.": f"referrals_{page_number - 1}"}
    if paginator.has_next():
        buttons |= {"След. ▶": f"referrals_{page_number + 1}"}

    if current_user.is_admin:
        buttons.update({
            "Отправить рассылку рефералам 📨": f"referral_message_0_{page_number}",
            "Отправить рассылку всем пользователям 👥📨": f"referral_message_1_{page_number}",
        })
    else:
        buttons.update({"Отправить рассылку 📨": f"referral_message_0_{page_number}"})

    if len(list(buttons.keys())) == 3:
        sizes = (2, 1, 1)
    else:
        sizes = (1, 1, 1)

    buttons.update(default_buttons)


    start_count = per_page * page_number - per_page + 1
    for user in paginator.get_page():
        user_status_emoji = status_emoji_data.get(user.status, "🆓",)
        message_text += f"{start_count}. @{user.username}: {user_status_emoji}\n"
        start_count += 1

    reply_markup = get_donate_keyboard(
        buttons=buttons,
        sizes=sizes
    )

    return message_text, reply_markup


@info_router.message(F.text == "⚙️ Настройки")
@info_router.callback_query(F.data.startswith("send_referrals_"))
@inject
async def send_referral_message_handler(
        aiogram_type: Message | CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> None:
    if isinstance(aiogram_type, Message):
        telegram_method = aiogram_type.answer
    else:
        callback = aiogram_type
        telegram_method = callback.message.edit_text

    current_user = await telegram_user_service.get_telegram_user(
        user_id=aiogram_type.from_user.id
    )
    if not current_user:
        return

    message_text, reply_markup = await referral_handler(
        current_user=current_user,
    )

    await telegram_method(
        text=message_text,
        reply_markup=reply_markup,
    )



