import uuid
from typing import List

from sqlalchemy import select, delete, update, func
from sqlalchemy.orm import selectinload

from app.models.telegram_user import TelegramUser, DonateStatus,  MatrixBuildType
from .base import RepositoryBase
from app.models.donate import Donate, DonateTransaction


class RepositoryDonate(RepositoryBase[Donate]):
    """Репозиторий доната"""

    def get_donates_list(self, *args, **kwargs):
        statement = (
            select(Donate)
            .filter(*args)
            .filter_by(**kwargs)
            .order_by(Donate.created_at.desc())
        )

        return self._session.execute(statement).scalars().all()

    def get_donate_by_telegram_user_id(
            self,
            telegram_user_id: uuid.UUID,
    ):
        statement = (
            select(Donate).filter_by(
                telegram_user_id=telegram_user_id,
            )
        ).order_by(Donate.created_at.desc())

        return self._session.execute(statement).scalars().all()

    def delete_donate_with_transactions(self, donate_id: uuid.UUID):
        delete_transactions_statement = (
            delete(DonateTransaction)
            .where(DonateTransaction.donate_id == donate_id)
        )

        delete_donate_statement = (
            delete(Donate)
            .where(Donate.id == donate_id)
        )

        self._session.execute(delete_transactions_statement)
        self._session.execute(delete_donate_statement)

    def get_count(self, *args, **kwargs) -> int:
        statement = (
            select(func.count(Donate.id))
            .filter(*args)
            .filter_by(**kwargs)
        )

        return self._session.execute(statement).scalar()

    def get_donates_by_matrices_ids(
            self,
            matrices_ids: List[uuid.UUID | str],
            **kwargs,
    ):
        statement = (
            select(Donate)
            .filter(Donate.matrix_id.in_(matrices_ids))
            .filter_by(**kwargs)
            .order_by(Donate.created_at.desc())
        )

        return self._session.execute(statement).scalars().all()


class RepositoryDonateTransaction(RepositoryBase[DonateTransaction]):
    """Репозиторий доната"""

    def get_transactions_list(self):
        statement = select(DonateTransaction).order_by(
            DonateTransaction.created_at.desc()
        )

        return self._session.execute(statement).scalars().all()

    def get_donate_transaction_by_sponsor_id(self, sponsor_id: uuid.UUID):
        statement = (
            select(DonateTransaction)
            .filter_by(sponsor_id=sponsor_id)
            .order_by(DonateTransaction.created_at.desc())
        )

        return self._session.execute(statement).scalars().all()

