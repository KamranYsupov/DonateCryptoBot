import datetime
import uuid
from typing import Tuple, Any

import loguru

from app.models.telegram_user import DonateStatus, status_list
from app.repositories.matrix import RepositoryMatrix
from app.models import Matrix
from app.schemas.matrix import MatrixEntity
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
from app.tasks.matrix import send_matrix_first_level_notification_task
from app.models.telegram_user import MatrixBuildType


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

    def get_matrix_telegram_users(
            self,
            matrix: Matrix
    ) -> tuple[list[TelegramUser], int]:
        first_matrices_ids, second_matrices_ids = get_matrices_list(matrix.matrices)

        matrices_ids = first_matrices_ids + second_matrices_ids

        first_matrices = self._repository_matrix.get_matrices_by_ids_list(first_matrices_ids)
        second_matrices = self._repository_matrix.get_matrices_by_ids_list(second_matrices_ids)
        first_sorted_matrices = sorted(get_sorted_objects_by_ids(first_matrices, first_matrices_ids),
                                       key=lambda x: x.created_at)
        second_sorted_matrices = sorted(get_sorted_objects_by_ids(second_matrices, second_matrices_ids),
                                        key=lambda x: x.created_at)

        telegram_users_ids = [
            matrix.owner_id if matrix else 0 for matrix in (first_sorted_matrices + second_sorted_matrices)
        ]
        telegram_users = self._repository_telegram_user.get_telegram_users_by_user_ids_list(telegram_users_ids)
        sorted_telegram_users = get_sorted_objects_by_ids(telegram_users, telegram_users_ids)

        return sorted_telegram_users, len(first_matrices_ids)

