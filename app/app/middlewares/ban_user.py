from aiogram.types import Message, CallbackQuery
from dependency_injector.wiring import inject, Provide

from app.services import telegram_user_service
from app.core.container import Container
from app.services.telegram_user_service import TelegramUserService
from app.db.commit_decorator import commit_and_close_session
from app.core.config import settings


@inject
async def ban_user_middleware(
        handler,
        event: Message | CallbackQuery,
        data: dict,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
):
    """
    Middleware, для обработки действий от забаненного пользователя.
    """
    current_user = await telegram_user_service.get_telegram_user(
        user_id=event.from_user.id
    )
    if not current_user:
        return await handler(event, data)
    if current_user.is_banned:
        await event.bot.send_message(
            chat_id=event.from_user.id,
            text=(
                "Ваш аккаунт заблокирован. Для уточнения причины блокировки, "
                f"свяжитесь со службой поддержки. @{settings.support_username}"
            )
        )
        return

    return await handler(event, data)