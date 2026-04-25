# import time
# import subprocess
#
# from pathlib import Path
# from loguru import logger
#
# from watchdog.observers import Observer
# from watchdog.events import (
#     FileSystemEventHandler,
#     FileCreatedEvent,
#     FileModifiedEvent,
#     FileDeletedEvent,
# )
#
# from app.core.config import settings
#
#
# class ChangeHandler(FileSystemEventHandler):
#     """Handler для отслеживания изменения в боте"""
#
#     def __init__(self, script_name) -> None:
#         self.script_name = script_name
#         self.process = subprocess.Popen(["python3", self.script_name])
#
#     def on_any_event(self, event):
#         if event.is_directory:
#             return None
#
#         if "__pycache__" in Path(event.src_path).parts:
#             return None
#
#         if isinstance(event, (FileCreatedEvent, FileModifiedEvent, FileDeletedEvent)):
#             if settings.debug:
#                 logger.info(
#                     f"Detected change in: {event.src_path}. Change type: {event.event_type}"
#                 )
#             self.restart_script()
#
#     def restart_script(self):
#         logger.info("Reloading bot...")
#         self.process.kill()
#         self.process = subprocess.Popen(["python3", self.script_name])
#
#
# if __name__ == "__main__":
#     app_dir = Path("/app/app")
#     script_path = app_dir / "main.py"
#
#     event_handler = ChangeHandler(script_path)
#     observer = Observer()
#     observer.schedule(event_handler, str(app_dir), recursive=True)
#     observer.start()
#
#     try:
#         while True:
#             time.sleep(1)
#     except KeyboardInterrupt:
#         observer.stop()
#     observer.join()

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