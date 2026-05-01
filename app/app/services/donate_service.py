import time
import uuid
from copy import copy
from datetime import datetime, timedelta
from typing import Tuple, Any, Sequence, Optional

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
from app.models.donate import DonateTransactionType


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
        if donate_sum == 10:
            return DonateStatus.TEST
        elif donate_sum == 25:
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
    def get_sponsor_depth(transaction_quantity: float | int, donate_quantity: int) -> int | None:
        transaction_percent = int(transaction_quantity * 100 / donate_quantity)

        sponsors_percents = [
            settings.first_sponsor_donate_percent,
            settings.second_sponsor_donate_percent,
            settings.third_sponsor_donate_percent,
        ]
        if transaction_percent in sponsors_percents:
            return sponsors_percents.index(transaction_percent) +  1

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

    async def _update_donate_data_with_sponsors(
            self,
            first_sponsor: Optional[TelegramUser],
            second_sponsor: Optional[TelegramUser],
            third_sponsor: Optional[TelegramUser],
            donate_sum: int | float,
            donations_data: list,
    ) -> list[dict[str, Any]]:
        sponsor_donate_percents = (
            (first_sponsor, settings.first_sponsor_donate_percent,),
            (second_sponsor, settings.second_sponsor_donate_percent,),
            (third_sponsor, settings.third_sponsor_donate_percent,)
        )

        for sponsor_depth, (sponsor, percent) in enumerate(sponsor_donate_percents):
            if not sponsor:
                continue

            if sponsor.status != DonateStatus.NOT_ACTIVE:
                donations_data.append({
                    "receiver": sponsor,
                    "receiver_chat_id": sponsor.user_id,
                    "sponsor_depth": sponsor_depth + 1,
                    "quantity": donate_sum * percent / 100,
                    "type_": DonateTransactionType.SPONSOR,
                 })

        return donations_data

    async def _update_donate_data_with_matrix_receivers(
            self,
            matrix: Matrix,
            donate_sum: int | float,
            donations_data: list,
            free_place_path: list[uuid.UUID],
            parents: list[Matrix],
            is_bot: bool,
    ) -> list[dict[str, Any]]:
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
        sponsor_donations_quantities = [
            transaction["quantity"] for transaction in donations_data
        ]

        for receiver in donate_receivers:
            if receiver.status == DonateStatus.NOT_ACTIVE:
                continue

            donations_data.append({
                "receiver": receiver,
                "receiver_chat_id": receiver.user_id,
                "quantity": matrix_donate_sum,
                "type_": DonateTransactionType.MATRIX,
            })

        if is_bot:
            return donations_data

        donate_reminder = donate_sum - (
            (len(donate_receivers) * matrix_donate_sum)
            + sum(sponsor_donations_quantities)
        )

        if donate_reminder:
            admin_user = self._repository_telegram_user.get(is_admin=True)
            donations_data.append({
                "receiver": admin_user,
                "receiver_chat_id": admin_user.user_id,
                "quantity": donate_reminder,
                "type_": DonateTransactionType.SYSTEM,
            })

        return donations_data

    async def add_to_matrix(
            self,
            matrix_to_add: Matrix,
            current_user: TelegramUser,
            free_place_level: int,
            free_place_path: list[str],
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
            sponsors: Sequence[TelegramUser],
            current_user: TelegramUser,
            donate_sum: int,
            donations_data: list,
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

        first_sponsor, second_sponsor, third_sponsor = sponsors
        await self._update_donate_data_with_sponsors(
            first_sponsor,
            second_sponsor,
            third_sponsor,
            donate_sum,
            donations_data,
        )

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
            if first_sponsor.is_admin:
                matrix_entity = MatrixEntity(
                    owner_id=first_sponsor.id,
                    status=status,
                )
                matrix = self._repository_matrix.create(obj_in=matrix_entity)
                (matrix.matrices,
                 matrix.matrix_telegram_usernames,
                 matrix.telegram_users) = {}, {}, []
                await self._handle_insertion_to_free_matrix(
                    matrix,
                    current_user,
                    donate_sum,
                    donations_data,
                    level_length,
                )
                return matrix

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
            donations_data: list,
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

        created_matrix = await self.add_to_matrix(
            free_matrix,
            current_user,
            free_place_level,
            free_place_path,
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
                        minutes=settings.add_bot_to_matrix_1_countdown_minutes
                    ),
                    **task_data,
                )
            )
            self._repository_add_bot_to_matrix_task_model.create(
                AddBotToMatrixTaskEntity(
                    execute_at=now + timedelta(
                        minutes=settings.add_bot_to_matrix_2_countdown_minutes
                    ),
                    **task_data,
                )
            )


    async def _find_free_matrix(
            self,
            user_to_add: TelegramUser,
            donate_sum: int | float,
            status: DonateStatus,
            donations_data: list,
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
            if not next_sponsor_matrices:
                user_to_add = next_sponsor
                continue

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

            if next_sponsor.is_admin:
                matrix_entity = MatrixEntity(
                    owner_id=next_sponsor.id,
                    status=status,
                )
                matrix = self._repository_matrix.create(obj_in=matrix_entity)
                (matrix.matrices,
                 matrix.matrix_telegram_usernames,
                 matrix.telegram_users) = {}, {}, []
                await self._handle_insertion_to_free_matrix(
                    matrix,
                    current_user,
                    donate_sum,
                    donations_data,
                    level_length,
                )
                return matrix
