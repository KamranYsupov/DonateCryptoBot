import asyncio

from loguru import logger

from app.handlers.routing import get_all_routers

from app.middlewares.throttling import (
    private_chat_only_middleware,
    rate_limit_middleware,
)
from app.middlewares.ban_user import (
    ban_user_middleware,
)
from app.middlewares.session_middleware import SQLAlchemySessionMiddleware

from app.core.container import Container
from app import handlers
from app.middlewares.subscriptions import subscription_checker_middleware

from loader import dp, bot


async def main(container: Container):
    """Запуск бота."""
    try:
        sync_session = container.session()

        all_routers = get_all_routers()
        dp.include_routers(all_routers)
        dp.message.middleware(private_chat_only_middleware)
        dp.message.middleware(rate_limit_middleware)
        dp.message.middleware(SQLAlchemySessionMiddleware(sync_session=sync_session))
        dp.message.middleware(ban_user_middleware)
        dp.message.middleware(subscription_checker_middleware)
        dp.callback_query.middleware(ban_user_middleware)

        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    container = Container()
    container.wire(modules=[handlers])
    logger.info("Bot is starting")
    asyncio.run(main(container=container))
