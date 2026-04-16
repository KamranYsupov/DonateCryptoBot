import uuid
from copy import copy
from datetime import datetime, timedelta
from typing import Tuple, Any, Sequence

import loguru
from dependency_injector.wiring import inject

from app.repositories.telegram_user import RepositoryTelegramUser
from app.repositories.matrix import RepositoryMatrix
from app.repositories.donate import RepositoryDonate
from app.models.telegram_user import TelegramUser, DonateStatus, MatrixBuildType
from app.models.matrix import Matrix
from app.services.matrix_service import MatrixService
from app.services.telegram_user_service import TelegramUserService
from app.schemas.matrix import MatrixEntity
from app.utils.matrix import get_matrices_length
from app.utils.matrix import find_first_level_matrix_id
from app.utils.sort import get_reversed_dict
from app.core.config import settings
from app.utils.matrix import find_free_place_in_matrix, insert_into_matrices
from app.utils.matrix import get_matrix_telegram_usernames_key
from app.repositories.matrix import RepositoryAddBotToMatrixTaskModel
from app.schemas.matrix import AddBotToMatrixTaskEntity


class DonateService:
    def __init__(
            self,
            repository_telegram_user: RepositoryTelegramUser,
            repository_matrix: RepositoryMatrix,
            repository_donate: RepositoryDonate,
            repository_add_bot_to_matrix_task_model: RepositoryAddBotToMatrixTaskModel,
    ) -> None:
        self._repository_telegram_user = repository_telegram_user
        self._repository_matrix = repository_matrix
        self._repository_donate = repository_donate
        self._repository_add_bot_to_matrix_task_model = repository_add_bot_to_matrix_task_model

    @staticmethod
    def get_donate_status(
            donate_sum: int,
    ) -> DonateStatus | None:
        if donate_sum == 25:
            return DonateStatus.BASE
        elif donate_sum == 50:
            return DonateStatus.BRONZE
        elif donate_sum == 100:
            return DonateStatus.SILVER
        elif donate_sum == 250:
            return DonateStatus.GOLD
        elif donate_sum == 500:
            return DonateStatus.PLATINUM
        elif donate_sum == 1000:
            return DonateStatus.BRILLIANT

        return None

    @staticmethod
    def _extend_donations_data(data: dict, sponsor: TelegramUser, donate: int | float):
        loguru.logger.info(str(donate))
        if data.get(sponsor):
            data[sponsor] += donate
        else:
            data[sponsor] = donate
        return data

    def get_matrix_parents(
            self,
            matrix: Matrix,
            count: int,
    ) -> list[Matrix]:
        parents = []
        current_matrix = matrix

        for _ in range(count):
            current_matrix = self._repository_matrix.get_parent_matrix(
                current_matrix.id,
                status=current_matrix.status,
            )
            if not current_matrix:
                break
            parents.append(current_matrix)

        return parents

    async def _update_donate_data_with_matrix_receivers(
            self,
            matrix: Matrix,
            donate_sum: int | float,
            donations_data: dict,
            free_place_path: list[uuid.UUID],
            parents: list[Matrix],
            is_bot: bool,
    ) -> dict[uuid.UUID, int | float]:
        matrix_donate_sum = donate_sum * settings.matrix_donate_percent / 100
        parents_owners_ids = [parent.owner_id for parent in parents]

        path_owner_ids = self._repository_matrix.get_owner_ids_by_matrices_ids_list(
            matrices_ids=free_place_path
        ) if free_place_path else []

        donate_receivers_ids = (
            [matrix.owner_id]
            + path_owner_ids
            + parents_owners_ids
        )

        donate_receivers = self._repository_telegram_user.get_active_users_by_ids(
            ids=donate_receivers_ids,
            is_bot=False,
        )

        for receiver in donate_receivers:
            if receiver.status == DonateStatus.NOT_ACTIVE:
                continue

            self._extend_donations_data(
                donations_data,
                receiver,
                matrix_donate_sum,
            )

        if is_bot:
            return donations_data

        receivers_donate_sum = sum(list(donations_data.values()))
        admin_user = self._repository_telegram_user.get(is_admin=True)
        self._extend_donations_data(
            donations_data,
            admin_user,
            donate_sum - receivers_donate_sum,
        )

        return donations_data

    async def add_to_matrix(
            self,
            matrix_to_add: Matrix,
            current_user: TelegramUser,
            free_place_level: int,
            free_place_path: list[str],
            matrix_telegram_usernames_path: list[str],
            parents: list[Matrix],
    ) -> Matrix:
        current_time = datetime.now()
        created_matrix_dict = {
            "owner_id": current_user.id,
            "status": matrix_to_add.status,
        }
        created_matrix_entity = MatrixEntity(**created_matrix_dict)
        created_matrix = self._repository_matrix.create(obj_in=created_matrix_entity.model_dump())
        created_matrix.created_at = current_time

        matrix_owner = self._repository_telegram_user.get(id=matrix_to_add.owner_id)
        if len(matrix_to_add.telegram_users) == settings.matrix_max_length and matrix_owner.is_admin:
            matrix_to_add_entity = MatrixEntity(
                owner_id=matrix_owner.id,
                status=matrix_to_add.status,
            )
            matrix_to_add = self._repository_matrix.create(obj_in=matrix_to_add_entity)
            (matrix_to_add.matrices,
             matrix_to_add.matrix_telegram_usernames,
             matrix_to_add.telegram_users) = {}, {}, []


        matrix_to_add_path_matrices = self._repository_matrix.get_matrices_by_ids_list(
            free_place_path, mapping=True
        )

        matrix_to_add.telegram_users.append(current_user.user_id)
        insert_into_matrices(
            matrix_to_add.matrices,
            free_place_path,
            free_place_level,
            str(created_matrix.id),
        )

        child_matrix_free_level = free_place_level
        child_matrix_path = copy(free_place_path)

        for path_matrix in matrix_to_add_path_matrices:

            child_matrix_free_level -= 1
            child_matrix_path.remove(str(path_matrix.id))

            path_matrix.telegram_users.append(current_user.user_id)
            insert_into_matrices(
                path_matrix.matrices,
                child_matrix_path,
                child_matrix_free_level,
                str(created_matrix.id),
            )

        parent_matrix_free_level = free_place_level
        parent_matrix_path = [str(matrix_to_add.id)] + free_place_path

        for parent_matrix in parents:
            parent_matrix_free_level += 1

            parent_matrix.telegram_users.append(current_user.user_id)
            insert_into_matrices(
                parent_matrix.matrices,
                parent_matrix_path,
                parent_matrix_free_level,
                str(created_matrix.id),
            )

            parent_matrix_path = [str(parent_matrix.id)] + parent_matrix_path

        return created_matrix

    async def handle_matrix_activation(
            self,
            first_sponsor: TelegramUser,
            current_user: TelegramUser,
            donate_sum: int,
            donations_data: dict,
            status: DonateStatus,
            level_length: int = settings.level_length,
            found_matrix: Matrix | None = None
    ) -> Matrix:
        if found_matrix:
            await self._handle_insertion_to_free_matrix(
                found_matrix,
                current_user,
                donate_sum,
                donations_data,
                level_length,
                start_bot_tasks=False,
            )
            return found_matrix

        first_sponsor_matrices = self._repository_matrix.get_user_matrices(
            owner_id=first_sponsor.id,
            status=status,
        )

        for matrix in first_sponsor_matrices:
            if len(matrix.telegram_users) < settings.matrix_max_length:
                await self._handle_insertion_to_free_matrix(
                    matrix,
                    current_user,
                    donate_sum,
                    donations_data,
                    level_length,
                )
                return matrix
        else:

            return await self._find_free_matrix(
                current_user,
                donate_sum,
                status,
                donations_data,
                level_length=settings.level_length,
            )


    async def _handle_insertion_to_free_matrix(
            self,
            free_matrix: Matrix,
            current_user: TelegramUser,
            donate_sum: int | float,
            donations_data: dict,
            level_length: int = settings.level_length,
            start_bot_tasks: bool = True
    ):
        free_place_path = find_free_place_in_matrix(free_matrix.matrices, level_length)
        free_place_level = len(free_place_path) + 1
        parents = self.get_matrix_parents(
            matrix=free_matrix,
            count=settings.matrix_max_level - free_place_level
        )

        await self._update_donate_data_with_matrix_receivers(
            free_matrix,
            donate_sum,
            donations_data,
            free_place_path,
            parents,
            is_bot=current_user.is_bot,
        )

        matrix_telegram_usernames_path = find_free_place_in_matrix(
            free_matrix.matrix_telegram_usernames,
            level_length
        )
        created_matrix = await self.add_to_matrix(
            free_matrix,
            current_user,
            free_place_level,
            free_place_path,
            matrix_telegram_usernames_path,
            parents,
        )

        if start_bot_tasks:
            now = datetime.now()
            task_data = dict(
                matrix_id=created_matrix.id,
                donate_sum=donate_sum,
            )
            self._repository_add_bot_to_matrix_task_model.create(
                AddBotToMatrixTaskEntity(
                    execute_at=now + timedelta(
                        seconds=settings.add_bot_to_matrix_1_countdown_minutes
                    ),
                    **task_data,
                )
            )
            self._repository_add_bot_to_matrix_task_model.create(
                AddBotToMatrixTaskEntity(
                    execute_at=now + timedelta(
                        seconds=settings.add_bot_to_matrix_2_countdown_minutes
                    ),
                    **task_data,
                )
            )


    async def _find_free_matrix(
            self,
            user_to_add: TelegramUser,
            donate_sum: int | float,
            status: DonateStatus,
            donations_data: dict,
            level_length: int,
    ):

        current_user = user_to_add
        while True:
            next_sponsor = self._repository_telegram_user.get(
                user_id=user_to_add.sponsor_user_id
            )

            if next_sponsor.status == DonateStatus.NOT_ACTIVE or not (
                int(status.get_status_donate_value())
                <= int(next_sponsor.status.get_status_donate_value())
            ):
                user_to_add = next_sponsor
                continue

            next_sponsor_matrices = self._repository_matrix.get_user_matrices(
                owner_id=next_sponsor.id,
                status=status,
            )

            for matrix in next_sponsor_matrices:
                if len(matrix.telegram_users) < settings.matrix_max_length:
                    await self._handle_insertion_to_free_matrix(
                        matrix,
                        current_user,
                        donate_sum,
                        donations_data,
                        level_length,
                    )
                    return matrix


    def check_is_matrix_free_with_donates(
            self,
            matrix: Matrix,
            status: DonateStatus
    ):
        current_matrix = matrix
        level_length = 2
        second_level_length = level_length * level_length

        first_level_current_matrix_length = len(list(current_matrix.matrices.keys()))
        current_matrix_donates_count = self._repository_donate.get_count(
            matrix_id=current_matrix.id,
            is_confirmed=False,
            is_canceled=False,
        )

        if first_level_current_matrix_length < level_length:
            first_level_empty_places_count = level_length - first_level_current_matrix_length

            if first_level_empty_places_count <= current_matrix_donates_count:
                return False

            parent_matrix = self._repository_matrix.get_parent_matrix(
                matrix_id=current_matrix.id,
                status=status,
            )
            if not parent_matrix:
                return True
            parent_first_level_matrices = self._repository_matrix.get_matrices_by_ids_list(
                matrices_ids=list(parent_matrix.matrices.keys())
            )

            sorted_parent_first_level_matrices = sorted(
                parent_first_level_matrices,
                key=lambda x: x.created_at,
            )
            current_matrix_index = sorted_parent_first_level_matrices.index(current_matrix)

            p_matrix_max_length_till_current_matrix = (
                (level_length * (current_matrix_index + 1)) + level_length
            )
            p_matrix_length_till_current_matrix = len(parent_first_level_matrices)

            for parent_first_level_matrix in sorted_parent_first_level_matrices[:current_matrix_index + 1]:
                p_matrix_length_till_current_matrix += len(list(parent_first_level_matrix.matrices.keys()))

            p_matrix_empty_places_count_till_current_matrix = (
                p_matrix_max_length_till_current_matrix - p_matrix_length_till_current_matrix
            )
            donate_matrices_ids = [
                matrix.id for matrix in parent_first_level_matrices[:current_matrix_index]
                if len(list(matrix.matrices.keys())) < level_length
            ]
            donate_matrices_ids.append(parent_matrix.id)

            matrices_donates = self._repository_donate.get_donates_by_matrices_ids(
                matrices_ids=donate_matrices_ids,
                is_confirmed=False,
                is_canceled=False,
            )
            total_donates_count = len(matrices_donates) + current_matrix_donates_count

            if p_matrix_empty_places_count_till_current_matrix <= total_donates_count:
                return False

            return True

        # !!!!!!!!!!!!!!!!!!
        second_level_current_matrix_length = len(current_matrix.telegram_users) - settings.level_length
        second_level_empty_places_count = second_level_length - second_level_current_matrix_length

        if second_level_empty_places_count <= current_matrix_donates_count:
            return False

        first_level_matrices = self._repository_matrix.get_matrices_by_ids_list(
            matrices_ids=list(matrix.matrices.keys())
        )
        sorted_first_level_matrices = sorted(first_level_matrices, key=lambda x: x.created_at)

        donate_first_level_matrices_ids = [
            matrix.id for matrix in sorted_first_level_matrices
            if len(list(matrix.matrices.keys())) < level_length
        ]
        first_level_matrices_donates = self._repository_donate.get_donates_by_matrices_ids(
            matrices_ids=donate_first_level_matrices_ids,
            is_confirmed=False,
            is_canceled=False,
        )
        total_donates_count = len(first_level_matrices_donates) + current_matrix_donates_count
        if second_level_empty_places_count <= total_donates_count:
            return False

        return True
























