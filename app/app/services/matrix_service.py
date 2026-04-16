import datetime
import uuid
from typing import Tuple, Any

import loguru

from app.models.telegram_user import DonateStatus, status_list
from app.repositories.matrix import RepositoryMatrix, RepositoryAddBotToMatrixTaskModel
from app.models import Matrix, AddBotToMatrixTaskModel
from app.schemas.matrix import MatrixEntity, AddBotToMatrixTaskEntity
from app.utils.matrix import get_sorted_matrices
from app.utils.pagination import Paginator
from app.models.telegram_user import TelegramUser
from app.repositories.telegram_user import RepositoryTelegramUser
from app.utils.matrix import (
    get_matrices_length,
    get_matrices_list,
)
from app.utils.sort import get_sorted_objects_by_ids
from app.utils.matrix import find_first_level_matrix_id
from app.models.telegram_user import MatrixBuildType
from app.schemas.telegram_user import generate_random_user


class MatrixService:
    def __init__(
            self,
            repository_matrix: RepositoryMatrix,
            repository_telegram_user: RepositoryTelegramUser,
    ) -> None:
        self._repository_matrix = repository_matrix
        self._repository_telegram_user = repository_telegram_user

    async def get_list(self) -> list[Matrix]:
        return self._repository_matrix.list()

    async def get_matrix(self, **kwargs) -> Matrix:
        return self._repository_matrix.get(**kwargs)

    async def get_user_matrices(
            self,
            owner_id: uuid.UUID,
            status: DonateStatus | None = None,
    ) -> list[Matrix]:
        return self._repository_matrix.get_user_matrices(
            owner_id=owner_id,
            status=status,
        )

    async def get_parent_matrix(
            self, matrix_id: Matrix.id, status: DonateStatus, return_all: bool = False
    )-> Matrix:
        return self._repository_matrix.get_parent_matrix(
            matrix_id=matrix_id, status=status, return_all=return_all
        )

    async def get_matrix_parents(self, matrix: Matrix, count: int) -> list[Matrix]:
        parents = []

        for _ in range(count):
            current_parent_matrix = self._repository_matrix.get_parent_matrix(
                matrix.id,
                status=matrix.status,
            )
            if not current_parent_matrix:
                break
            parents.append(current_parent_matrix.owner_id)

        return parents

    async def create_matrix(self, matrix: MatrixEntity) -> Matrix:
        return self._repository_matrix.create(obj_in=matrix.model_dump())

    async def delete(self, obj_id: uuid.UUID):
        self._repository_matrix.delete(obj_id=obj_id)


class AddBotToMatrixTaskModelService:
    def __init__(
            self,
            repository_add_bot_to_matrix_task: RepositoryAddBotToMatrixTaskModel
    ) -> None:
        self._repository_add_bot_to_matrix_task = repository_add_bot_to_matrix_task

    async def get_list(self, *args, **kwargs) -> list[Matrix]:
        return self._repository_add_bot_to_matrix_task.list(*args, **kwargs)

    async def get_task(self, **kwargs) -> Matrix:
        return self._repository_add_bot_to_matrix_task.get(**kwargs)

    async def create_task(self, add_bot_to_matrix_task_model: AddBotToMatrixTaskEntity) -> Matrix:
        return self._repository_add_bot_to_matrix_task.create(
            obj_in=add_bot_to_matrix_task_model.model_dump()
        )

    async def set_is_executed(self, ids: list[uuid.UUID], commit: bool = False,):
        return self._repository_add_bot_to_matrix_task.set_is_executed(ids, commit)



