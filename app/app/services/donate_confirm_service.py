import math
import uuid
from typing import Tuple, Any, Optional, List

import loguru
from app.repositories.telegram_user import RepositoryTelegramUser
from app.repositories.donate import RepositoryDonate, RepositoryDonateTransaction
from app.models.telegram_user import TelegramUser
from app.schemas.donate import DonateEntity, DonateTransactionEntity
from app.schemas.telegram_user import TelegramUserEntity
from app.models.telegram_user import MatrixBuildType
from app.models.donate import DonateTransactionType


class DonateConfirmService:

    def __init__(
        self,
        repository_donate: RepositoryDonate,
        repository_donate_transaction: RepositoryDonateTransaction,
        repository_telegram_user: RepositoryTelegramUser,
    ):
        self._repository_donate = repository_donate
        self._repository_donate_transaction = repository_donate_transaction
        self._repository_telegram_user = repository_telegram_user

    async def create_donate(
        self,
        telegram_user_id: uuid.UUID,
        donate_data: list[dict[str, Any]],
        matrix_id: uuid.UUID,
        quantity: float,
    ):
        """Создание сущности доната"""
        donate_dict = {
            "telegram_user_id": telegram_user_id,
            "quantity": quantity,
            "matrix_id": matrix_id,
        }
        donate = DonateEntity(**donate_dict)
        donate_obj = self._repository_donate.create(obj_in=donate.model_dump())
        await self._create_donate_transaction(
            donate_id=donate_obj.id, donate_data=donate_data
        )
        return donate_obj

    async def _create_donate_transaction(
            self,
            donate_id: uuid.UUID,
            donate_data: list[dict[str, Any]],
    ):
        """
        Создание конкретной транзакции (часть доната), перечисляемой одному спонсору.
        При создании доната через create_donate - создаются автоматически.
        Всю инфу берет из donate_data.
        """
        for transaction_data in donate_data:
            sponsor = transaction_data["receiver"]

            if sponsor.is_banned:
                sponsor = self._repository_telegram_user.get(is_admin=True)

            donate_transaction_dict_obj = DonateTransactionEntity(
                sponsor_id=sponsor.id,
                donate_id=donate_id,
                quantity=transaction_data["quantity"],
                type_=transaction_data["type_"],
            )
            self._repository_donate_transaction.create(
                obj_in=donate_transaction_dict_obj.model_dump()
            )

    async def get_donate_by_id(self, donate_id: uuid.UUID):
        """Получить донат по id доната"""
        return self._repository_donate.get(id=donate_id)

    async def get_donate_by_telegram_user_id(
            self,
            telegram_user_id: uuid.UUID,
    ):
        return self._repository_donate.get_donate_by_telegram_user_id(
            telegram_user_id=telegram_user_id,
        )

    async def get_donate_transaction_by_id(self, donate_transaction_id: uuid.UUID):
        """Получить транзакцию по id"""
        return self._repository_donate_transaction.get(id=donate_transaction_id)

    async def get_donate_transaction_by_sponsor_id(self, sponsor_id: uuid.UUID):
        """Получить список транзакций по id спонсора (кому должны перечислить)."""
        return self._repository_donate_transaction.get_donate_transaction_by_sponsor_id(
            sponsor_id
        )

    async def get_all_my_donates_and_transactions(
            self,
            telegram_user_id: uuid.UUID,
    ):
        """Получить все свои отправленные донаты в виде словаря {донат: транзакции доната}"""
        get_donates_kwargs = {"telegram_user_id": telegram_user_id}
        donates = self._repository_donate.get_donates_list(**get_donates_kwargs)
        output_dict = {}
        for donate in donates:
            donate_transactions = self._repository_donate_transaction.list(
                donate_id=donate.id
            )
            output_dict[donate] = donate_transactions
        return output_dict

    async def get_donate_transactions_by_donate_id(
            self,
            donate_id: uuid.UUID,
            return_data: bool = False,
    ):
        transactions = self._repository_donate_transaction.list(
            donate_id=donate_id,
        )

        if not return_data:
            return transactions

        if not transactions:
            return []

        return [
            {
                "id": transaction.id,
                "sponsor_id": transaction.sponsor_id,
                "donate_id": transaction.donate_id,
                "quantity": transaction.quantity,
                "type_": transaction.type_,
                "created_at": transaction.created_at,
                "updated_at": transaction.updated_at,
            }
            for transaction in transactions
        ]

    async def get_all_donates_and_transactions(
            self,
    ):
        """Получить все свои отправленные донаты в виде словаря {донат: транзакции доната}"""
        get_donates_kwargs = dict()

        donates = self._repository_donate.get_donates_list(**get_donates_kwargs)
        output_dict = {}
        for donate in donates:
            donate_transactions = self._repository_donate_transaction.list(
                donate_id=donate.id
            )
            output_dict[donate] = donate_transactions
        return output_dict

    async def get_all_donate_transactions(self):
        return self._repository_donate_transaction.get_transactions_list()

    async def delete_donate_with_transactions(self, donate_id: uuid.UUID) -> None:
        return self._repository_donate.delete_donate_with_transactions(
            donate_id=donate_id
        )

    async def get_donates_count(self, *args, **kwargs) -> int:
        return self._repository_donate.get_count(*args, **kwargs)

    async def get_donates_by_matrices_ids(self, matrices_ids: List[uuid.UUID | str]):
        return self._repository_donate.get_donates_by_matrices_ids(matrices_ids)

    async def get_system_bill(self) -> int:
        transactions_quantities = (
            self._repository_donate_transaction.get_transactions_quantities(
                type_=DonateTransactionType.SYSTEM
            )
        )
        bots_transactions_quantities = \
            self._repository_donate_transaction.get_bots_transactions_quantities()

        return sum(transactions_quantities) - sum(bots_transactions_quantities)

    async def get_donates_sum(self) -> int:
        return sum(self._repository_donate.get_donates_quantities())
