import uuid
from typing import Tuple, Any, List

from app.repositories.transfer import RepositoryTransfer
from app.repositories.telegram_user import RepositoryTelegramUser
from app.models.transfer import Transfer
from app.schemas.transfer import TransferCreateSchema


class TransferService:

    def __init__(
            self,
            repository_transfer: RepositoryTransfer,
            repository_telegram_user: RepositoryTelegramUser
    ) -> None:
        self._repository_transfer = repository_transfer
        self._repository_telegram_user = repository_telegram_user


    async def get_list(
            self,
            *args,
            join_sender: bool = False,
            join_receiver: bool = False,
            **kwargs
    ) -> list[Transfer]:
        return self._repository_transfer.get_list(
            *args,
            join_sender,
            join_receiver,
            **kwargs
        )

    async def get_transfer(self, **kwargs) -> Transfer:
        return self._repository_transfer.get(**kwargs)

    async def exists(self, **kwargs) -> Transfer:
        return self._repository_transfer.exists(**kwargs)

    async def create_transfer(
        self,
        obj_in: TransferCreateSchema,
    ) -> Transfer | None:
        return self._repository_transfer.create(obj_in=obj_in.model_dump())