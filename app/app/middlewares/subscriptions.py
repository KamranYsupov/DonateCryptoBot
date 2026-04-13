from aiogram.enums import ChatMemberStatus
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dependency_injector.wiring import inject, Provide

from app.services import telegram_user_service
from app.core.container import Container
from app.services.telegram_user_service import TelegramUserService
from app.db.commit_decorator import commit_and_close_session
from app.core.config import settings
from app.keyboards.donate import get_donate_keyboard


@inject
async def subscription_checker_middleware(
        handler,
        event: Message,
        data: dict,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
):
    """
    Middleware, для обработки проверки подписки на каналы.
    """
    current_user = await telegram_user_service.get_telegram_user(
        user_id=event.from_user.id
    )
    if not current_user:
        return await handler(event, data)
    chat_result = await event.bot.get_chat_member(
        chat_id=settings.chat_id, user_id=event.from_user.id
    )
    channel_result = await event.bot.get_chat_member(
        chat_id=settings.channel_id, user_id=event.from_user.id
    )

    not_subscribed_statuses = (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED)
    if channel_result.status in not_subscribed_statuses and chat_result.status in not_subscribed_statuses:
        buttons = [
            InlineKeyboardButton(
                text="📌 КАНАЛ 📌",
                url=settings.channel_link),
            InlineKeyboardButton(
                text="💬 ЧАТ 💬",
                url=settings.chat_link),
            InlineKeyboardButton(
                text="Проверить подписку ✅",
                callback_data=f"menu_{current_user.sponsor_user_id}",
            )
        ]
        keyboard = InlineKeyboardBuilder()
        keyboard.add(*buttons)

        await event.answer(
            f"🔑 Для доступа к основным функциям бота, подпишитесь на чат и канал сообщества ⤵️",
            reply_markup=keyboard.adjust(1, 1).as_markup()
        )

    return await handler(event, data)