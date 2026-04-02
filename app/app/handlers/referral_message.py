from typing import List

import loguru
from aiogram import Router, F, html
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, PhotoSize
from dependency_injector.wiring import inject, Provide

from app.core.container import Container
from app.services.telegram_user_service import TelegramUserService
from app.keyboards.donate import get_donate_keyboard
from app.keyboards.reply import reply_cancel_keyboard
from app.core.config import settings
from app.utils.sponsor import get_callback_value
from app.utils.pagination import Paginator
from app.utils.matrix import get_matrices_length
from app.utils.matrix import get_active_matrices, get_archived_matrices
from app.models.telegram_user import status_list, status_emoji_list
from app.db.commit_decorator import commit_and_close_session
from app.utils.bot import echo_message_with_media
from app.keyboards.reply import get_reply_keyboard
from app.utils.bot import send_assembled_message


class MessageForm(StatesGroup):
    photo = State()
    text = State()
    button_text = State()
    button_link = State()
    complete_message = State()
    confirm_referrals_send = State()
    to_everyone = State()

referral_router = Router()


def get_skip_keyboard():
    return get_donate_keyboard(
        buttons={"⏭ Пропустить": "skip_referrals_msg_state"},
    )

def get_confirm_referrals_send_keyboard():
    return get_donate_keyboard(
        buttons={
            "Да": f"confirm_referrals_send",
            "Нет": "cancel",
        },
        sizes=(2,)
    )

@referral_router.callback_query(
    F.data.startswith("referral_message_")
)
async def referral_message_callback_handler(
        callback: CallbackQuery,
        state: FSMContext
) -> None:
    to_everyone, page_number = map(int, callback.data.split("_")[-2:])
    await state.update_data(to_everyone=to_everyone)
    await callback.message.edit_reply_markup(
        reply_markup=get_donate_keyboard(
            buttons={
                "Отправить готовое 📩": "send_complete_message",
                "Создать с нуля 📝": "create_message",
                "🔙 Назад": f"referrals_{page_number}"
            },
            sizes=(2, )
        )
    )


@referral_router.callback_query(
    F.data == "create_message"
)
async def start_form(callback: CallbackQuery, state: FSMContext):
    await state.set_state(MessageForm.photo)
    await callback.message.delete()
    await callback.message.answer(
        "✍️",
        reply_markup=reply_cancel_keyboard
    )
    await callback.message.answer(
        "Отправьте фото сообщения:",
        reply_markup=get_skip_keyboard()
    )


@referral_router.message(MessageForm.photo)
async def process_photo_handler(message: Message, state: FSMContext):
    if not message.photo:
        await message.answer(
            "Отправьте фото или нажмите "
            + html.bold("⏭ Пропустить")
        )
        return

    await state.update_data(photo=message.photo[-1].file_id)
    await state.set_state(MessageForm.text)
    await message.answer(
        "Фото принято! Теперь отправьте текст сообщения:"
    )


@referral_router.message(MessageForm.text)
async def process_text_handler(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Отправьте текст сообщения")
        return

    await state.update_data(text=message.text)
    await state.set_state(MessageForm.button_text)
    await message.answer(
        "Текст сохранен! "
        "Отправьте текст кнопки(опционально):",
        reply_markup=get_skip_keyboard()
    )


@referral_router.message(MessageForm.button_text)
async def process_button_text_handler(message: Message, state: FSMContext):
    await state.update_data(button_text=message.text)
    await state.set_state(MessageForm.button_link)
    await message.answer(
        "Текст кнопки сохранен! "
        "Отправьте ссылку кнопки:"
    )


@inject
async def answer_created_message(
        message: Message,
        state: FSMContext,
        from_user_id: int,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
):
    data = await state.get_data()
    current_user = await telegram_user_service.get_telegram_user(
        user_id=from_user_id
    )
    await message.answer(
        "Готовый вариант:",
        reply_markup=get_reply_keyboard(current_user)
    )
    complete_message = await send_assembled_message(
        bot=message.bot,
        chat_id=from_user_id,
        text=data.get("text"),
        photo_id=data.get("photo"),
        button_text=data.get("button_text"),
        button_link=data.get("button_link"),
    )

    await state.update_data(complete_message=complete_message)
    await state.set_state(MessageForm.confirm_referrals_send)

    await message.answer(
        "Отправить рассылку?",
        reply_to_message_id=complete_message.message_id,
        reply_markup=get_confirm_referrals_send_keyboard(),
    )


@referral_router.message(MessageForm.button_link)
async def process_button_link_handler(
        message: Message,
        state: FSMContext,
):
    if not message.text.startswith(("http://", "https://")):
        await message.answer(
            "❌ Введите корректную ссылку "
            "(http:// или https://)"
        )
        return

    await state.update_data(button_link=message.text)
    await answer_created_message(
        message,
        state,
        from_user_id=message.from_user.id
    )


@referral_router.callback_query(F.data == "skip_referrals_msg_state")
async def skip_step(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    current_state = await state.get_state()

    if current_state == MessageForm.photo.state:
        await state.set_state(MessageForm.text)
        await callback.message.answer(
            "Фото пропущено. Введите текст:"
        )

    elif current_state == MessageForm.button_text.state:
        await answer_created_message(
            callback.message,
            state,
            from_user_id=callback.from_user.id
        )


@referral_router.callback_query(
    F.data == "send_complete_message"
)
async def send_complete_message_callback_handler(
        callback: CallbackQuery,
        state: FSMContext,
) -> None:
    await callback.message.delete()
    await callback.message.answer(
        "Перешлите в чат готовое сообщение",
        reply_markup=reply_cancel_keyboard
    )
    await state.set_state(MessageForm.complete_message)


@referral_router.message(MessageForm.complete_message)
@inject
async def process_complete_message_handler(
        message: Message,
        state: FSMContext,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
):
    current_user = await telegram_user_service.get_telegram_user(
        user_id=message.from_user.id
    )
    await state.update_data(complete_message=message)
    await state.set_state(MessageForm.confirm_referrals_send)
    await message.answer(
        "Готовый вариант:",
        reply_markup=get_reply_keyboard(current_user)
    )
    echo_message: Message = await echo_message_with_media(
        chat_id=message.from_user.id,
        original_message=message,
    )
    await message.answer(
        "Отправить рассылку?",
        reply_to_message_id=echo_message.message_id,
        reply_markup=get_confirm_referrals_send_keyboard()
    )


@referral_router.callback_query(
    MessageForm.confirm_referrals_send,
    F.data == "confirm_referrals_send",
)
@inject
async def confirm_referrals_send_message_handler(
        callback: CallbackQuery,
        state: FSMContext,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
):
    state_data = await state.get_data()
    to_everyone = state_data.get("to_everyone")
    if to_everyone:
        receivers = await telegram_user_service.get_list(is_admin=False)
    else:
        receivers = await telegram_user_service.get_invited_users(
            sponsor_user_id=callback.from_user.id
        )

    await callback.message.edit_text(
        "Рассылка отправлена ✅",
        reply_markup=None,
    )
    await state.clear()

    for user in receivers:
        try:
            if not to_everyone:
                await callback.bot.send_message(
                    chat_id=user.user_id,
                    text="Вам сообщение от вашего спонсора:"
                )

            await echo_message_with_media(
                chat_id=user.user_id,
                original_message=state_data["complete_message"],
            )
        except TelegramAPIError:
            continue
