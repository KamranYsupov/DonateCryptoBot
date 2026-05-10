import asyncio
from typing import Callable, List, Awaitable, Optional

import loguru
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import  CommandObject, Command

from app.core.config import settings
from app.tasks.matrix import execute_bot_matrix_tasks
from app.tasks.contest import update_contest_task

worker_router = Router()

async def add_bot_to_matrix_task_worker(delay: Optional[int] = None) -> None:
    delay = delay or settings.add_bot_to_matrix_task_delay
    while True:
        loguru.logger.info("Executing add_bot_to_matrix_tasks...")
        await execute_bot_matrix_tasks()
        await asyncio.sleep(delay)


async def update_contest_task_worker(delay: Optional[int] = None) -> None:
    delay = delay or settings.update_contests_task_delay
    while True:
        loguru.logger.info("Executing update_contests_task...")
        await update_contest_task()
        await asyncio.sleep(delay)


def get_workers() -> List[Callable[[Optional[int]], Awaitable[None]]]:
    return [
        add_bot_to_matrix_task_worker,
        update_contest_task_worker
    ]


















