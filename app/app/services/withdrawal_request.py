from app.models.withdrawal_request import WithdrawalRequest
from app.repositories.withdrawal_request import RepositoryWithdrawalRequest
from app.schemas.withdrawal_request import WithdrawalRequestEntity


class WithdrawalRequestService:
    def __init__(self, repository_withdrawal_request: RepositoryWithdrawalRequest) -> None:
        self._repository_withdrawal_request = repository_withdrawal_request

    async def get_withdrawal_requests(
            self,
            *args,
            order_by: list = [],
            **kwargs
    ) -> list[WithdrawalRequest]:
        return self._repository_withdrawal_request.get_withdrawal_requests(
            *args,
            order_by=order_by,
            **kwargs
        )

    async def get_withdrawal_request(self, **kwargs) -> WithdrawalRequest:
        return self._repository_withdrawal_request.get(**kwargs)

    async def create_withdrawal_request(
            self,
            withdrawal_requests_entity: WithdrawalRequestEntity
    ) -> WithdrawalRequest:
        return self._repository_withdrawal_request.create(
            obj_in=withdrawal_requests_entity
        )

    async def withdrawal_requests_exists(self, *args, **kwargs) -> WithdrawalRequest:
        return self._repository_withdrawal_request.exists(*args, **kwargs)
