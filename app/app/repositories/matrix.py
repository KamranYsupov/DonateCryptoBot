import uuid

import loguru
from sqlalchemy import select, cast, func, BigInteger, any_, update
from sqlalchemy.dialects.postgresql import JSONB

from app.models.telegram_user import TelegramUser, DonateStatus
from .base import RepositoryBase
from app.models.matrix import Matrix, AddBotToMatrixTaskModel

from ..models.telegram_user import MatrixBuildType


class RepositoryMatrix(RepositoryBase[Matrix]):
    """Репозиторий матрицы"""

    def get_parent_matrix(
            self, matrix_id: Matrix.id, status: DonateStatus, return_all: bool = False
    ) -> Matrix | list[Matrix]:
        statement = (
            select(Matrix)
            .where(
                (Matrix.status == status)
                & (Matrix.matrices.has_key(str(matrix_id)))
            )
            .order_by(Matrix.created_at)
        )
        if return_all:
            result = self._session.execute(statement).scalars().all()
        else:
            result = self._session.execute(statement).scalars().first()

        return result

    def get_user_matrices(
            self,
            owner_id: uuid.UUID,
            status: DonateStatus | None = None,
    ) -> list[Matrix]:
        statement_filter_by_kwargs = {"owner_id": owner_id}

        if status:
            statement_filter_by_kwargs["status"] = status

        statement = (
            select(Matrix)
            .filter_by(**statement_filter_by_kwargs)
            .order_by(Matrix.created_at)
        )

        return self._session.execute(statement).scalars().all()

    def get_matrices_by_ids_list(
            self,
            matrices_ids: list[str | uuid.UUID],
            mapping: bool = False
    ) -> list[Matrix]:
        statement = select(Matrix).filter(Matrix.id.in_(matrices_ids))
        matrices = self._session.execute(statement).scalars().all()


        if not mapping:
            return matrices

        matrices_map = {str(m.id): m for m in matrices}
        return [matrices_map[str(i)] for i in matrices_ids]

    def get_owner_ids_by_matrices_ids_list(
            self,
            matrices_ids: list[uuid.UUID]
    ) -> list[uuid.UUID]:
        if not matrices_ids:
            return []

        statement = select(Matrix.id, Matrix.owner_id).where(
            Matrix.id.in_(matrices_ids)
        )

        rows = self._session.execute(statement).all()
        mapping = {str(row.id): row.owner_id for row in rows}

        return [mapping[str(i)] for i in matrices_ids]


class RepositoryAddBotToMatrixTaskModel(RepositoryBase[AddBotToMatrixTaskModel]):

    def set_is_executed(self, ids: list[uuid.UUID], commit: bool = False):
        statement = (
            update(AddBotToMatrixTaskModel)
            .where(AddBotToMatrixTaskModel.id.in_(ids))
            .values(is_executed=True)
        )
        self._session.execute(statement)

        if commit:
            self._session.commit()



