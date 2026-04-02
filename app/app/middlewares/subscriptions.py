from aiogram.enums import ChatMemberStatus
from aiogram.types import Message, CallbackQuery
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
    result = await event.bot.get_chat_member(
        chat_id=settings.chat_id, user_id=event.from_user.id
    )

    if result.status in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED):
        await event.answer(
            f"Присоединитесь к чату нашего сообщества\n\n {settings.chat_link}",
            reply_markup=get_donate_keyboard(
                buttons={
                    "Я подписан(а) ✅": f"menu_{current_user.sponsor_user_id}",
                }
            ),
        )
        return

    return await handler(event, data)