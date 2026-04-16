import asyncio
import datetime
import random
import time
from functools import wraps

import loguru
from aiogram import Router, F
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, CommandObject, Command
from dependency_injector.wiring import inject, Provide
from sqlalchemy.sql import func

from app.core.container import Container
from app.services.telegram_user_service import TelegramUserService
from app.schemas.telegram_user import TelegramUserEntity, generate_random_user
from app.schemas.matrix import MatrixEntity
from app.keyboards.donate import get_donate_keyboard
from app.core.config import settings
from app.models.telegram_user import status_list
from app.services.matrix_service import MatrixService
from app.utils.sponsor import get_callback_value
from app.services.donate_service import DonateService
from app.models.telegram_user import DonateStatus, MatrixBuildType
from app.db.commit_decorator import commit_and_close_session
from app.repositories.matrix import RepositoryAddBotToMatrixTaskModel
from app.schemas.matrix import AddBotToMatrixTaskEntity
from app.services.matrix_service import AddBotToMatrixTaskModelService
from app.tasks.matrix import execute_tasks

worker_router = Router()


@worker_router.message(Command("start_add_bot_to_matrix_task_worker"))
@inject
async def start_add_bot_to_matrix_task_worker_handler(
        message: Message,
        command: CommandObject,
) -> None:
    await message.answer("starting..")
    pause = int(command.args)
    while True:
        loguru.logger.info("Executing tasks...")
        await execute_tasks()
        await asyncio.sleep(pause)


