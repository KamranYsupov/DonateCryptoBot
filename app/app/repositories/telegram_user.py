from uuid import UUID

from sqlalchemy import select, text, func
from sqlalchemy.orm import joinedload, aliased

from .base import RepositoryBase
from app.models.telegram_user import TelegramUser, MatrixBuildType, DonateStatus


class RepositoryTelegramUser(RepositoryBase[TelegramUser]):
    """Репозиторий телеграм пользователя"""

    def get_list(
            self,
            *args,
            join_sponsor: bool = False,
            **kwargs
    ):

        query_options = []
        if join_sponsor:
            query_options.append(joinedload(TelegramUser.sponsor))

        statement = (
            select(TelegramUser)
            .options(*query_options)
            .filter(*args)
            .filter_by(**kwargs)
            .order_by(TelegramUser.created_at)
        )
        return self._session.execute(statement).scalars().all()

    def get_ids(self, *args, **kwargs) -> list[UUID]:
        statement = (
            select(TelegramUser.id)
            .filter(*args)
            .filter_by(**kwargs)
        )
        return self._session.execute(statement).scalars().all()

    def get_active_users_by_ids(self, ids: list[UUID], **kwargs):
        statement = (
            select(TelegramUser)
            .where(
                TelegramUser.status != DonateStatus.NOT_ACTIVE,
                TelegramUser.id.in_(ids),
            )
            .filter_by(**kwargs)
        )

        users = self._session.execute(statement).scalars().all()
        mapping = {user.id: user for user in users}

        return [mapping[i] for i in ids if i in mapping]

    def get_count(
            self,
            *args,
            **kwargs
    ) -> int:
        statement = (
            select(func.count(TelegramUser.user_id))
            .filter(*args)
            .filter_by(**kwargs)
        )
        return self._session.execute(statement).scalar()

    def get_invited_users(
            self,
            sponsor_user_id: int
    ):
        """Получение списка всех приглашенных пользователей"""
        statement = (
            select(TelegramUser)
            .filter_by(
                sponsor_user_id=sponsor_user_id,
                is_bot=False,
            )
            .order_by(TelegramUser.created_at)
        )

        return self._session.execute(statement).scalars().all()

    def get_telegram_user_with_sponsors(
        self, user_id: int
    ) -> tuple[TelegramUser, TelegramUser, TelegramUser]:
        t1, t2, t3, t4 = [aliased(TelegramUser) for _ in range(4)]
        sponsors = (
            self._session.query(t1, t2, t3, t4)
            .outerjoin(t2, t2.user_id == t1.sponsor_user_id)
            .outerjoin(t3, t3.user_id == t2.sponsor_user_id)
            .outerjoin(t4, t4.user_id == t3.sponsor_user_id)
            .filter(t1.user_id == user_id)
            .limit(1)
            .one_or_none()
        )

        return sponsors

    def get_sponsors_for_separating_donate(self, user_id: int):
        sponsors = []
        user = self.get(user_id=user_id)
        while user.sponsor_user_id:
            sponsor = self.get(user_id=user.sponsor_user_id)
            sponsors.append(sponsor)
        return sponsors

    def get_sponsors_chain(self, user_id):
        recursive_query = text(
            """
            WITH RECURSIVE sponsor_chain AS (
            SELECT user_id, sponsor_user_id, username, first_name FROM telegram_users WHERE user_id = :user_id
            UNION
            SELECT tu.user_id, tu.sponsor_user_id, tu.username, tu.first_name FROM telegram_users tu 
            JOIN sponsor_chain sc ON tu.user_id = sc.sponsor_user_id
            )
            SELECT sponsor_chain.user_id AS sponsor_user_id, sponsor_chain.sponsor_user_id AS sponsor_of_sponsor_user_id,
            sponsor_chain.username AS sponsor_username, sponsor_chain.first_name AS sponsor_first_name
            FROM sponsor_chain;
            """
        )

        result = self._session.execute(recursive_query, {"user_id": user_id})
        return result.fetchall()

    def get_telegram_users_by_user_ids_list(
            self,
            telegram_users_ids: list[TelegramUser.user_id]
    ) -> list[TelegramUser]:
        statement = select(TelegramUser).filter(
            TelegramUser.id.in_(telegram_users_ids)
        )
        return self._session.execute(statement).scalars().all()
