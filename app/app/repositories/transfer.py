import uuid
from typing import List

from sqlalchemy import select, delete, update, func
from sqlalchemy.orm import selectinload

from .base import RepositoryBase
from app.models.transfer import Transfer


class RepositoryTransfer(RepositoryBase[Transfer]):
    """Репозиторий конкурса кураторов"""

    def get_list(
            self,
            *args,
            join_sender: bool = False,
            join_receiver: bool = False,
            **kwargs
    ):
        options = []
        if join_sender:
            options.append(selectinload(Transfer.sender))
        if join_receiver:
            options.append(selectinload(Transfer.recipient))

        statement = select(Transfer).options(*options).order_by(Transfer.created_at)
        result  = self._session.execute(statement)

        return result.scalars().all()