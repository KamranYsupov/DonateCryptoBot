from dependency_injector import containers, providers

from app.core.config import Settings
from app.db.session import SyncSession
from app.repositories.donate import RepositoryDonate, RepositoryDonateTransaction

from app.repositories.telegram_user import RepositoryTelegramUser
from app.repositories.admin_user import RepositoryAdminUser
from app.repositories.matrix import RepositoryMatrix
from app.repositories.transaction import RepositoryTransaction
from app.repositories.withdrawal_request import RepositoryWithdrawalRequest

from app.models.telegram_user import TelegramUser
from app.models.admin_user import AdminUser
from app.models.donate import Donate, DonateTransaction
from app.models.matrix import Matrix
from app.models.transaction import Transaction
from app.models.withdrawal_request import WithdrawalRequest

from app.services.donate_confirm_service import DonateConfirmService
from app.services.telegram_user_service import TelegramUserService
from app.services.matrix_service import MatrixService
from app.services.donate_service import DonateService
from app.services.crypto_bot_api_service import CryptoBotAPIService
from app.services.withdrawal_request import WithdrawalRequestService
from app.models.matrix import AddBotToMatrixTaskModel
from app.repositories.matrix import RepositoryAddBotToMatrixTaskModel
from app.services.matrix_service import AddBotToMatrixTaskModelService


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "app.api.endpoints.crypto_bot",

            "app.handlers.donate",
            "app.handlers.start",
            "app.handlers.info",
            "app.handlers.ban_user",
            "app.handlers.referral_message",
            "app.handlers.payments",
            "app.handlers.withdrawal_request",
            "app.handlers.transfer",
            "app.handlers.worker",
            "app.handlers.bill_type",
            "app.handlers.aggregators",

            "app.middlewares.ban_user",
            "app.middlewares.subscriptions",
            "app.tasks.donate",
            "app.tasks.matrix",
            "app.utils.excel",
            "app.utils.texts",
        ]
    )

    config = providers.Factory(Settings)
    db = providers.Singleton(SyncSession, db_url=config.provided.postgres_url)
    session = providers.Factory(db().create_session)

    # region repository
    repository_telegram_user = providers.Factory(
        RepositoryTelegramUser, model=TelegramUser, session=session
    )
    repository_admin_user = providers.Factory(
        RepositoryAdminUser, model=AdminUser, session=session
    )
    repository_matrix = providers.Factory(
        RepositoryMatrix, model=Matrix, session=session
    )
    repository_wallet_recharge = providers.Factory(
        RepositoryTransaction, model=Transaction, session=session
    )
    repository_donate = providers.Factory(
        RepositoryDonate,
        model=Donate,
        session=session,
    )
    repository_donate_transaction = providers.Factory(
        RepositoryDonateTransaction,
        model=DonateTransaction,
        session=session,
    )
    repository_withdrawal_request = providers.Factory(
        RepositoryWithdrawalRequest, model=WithdrawalRequest, session=session
    )
    repository_add_bot_to_matrix_task = providers.Factory(
        RepositoryAddBotToMatrixTaskModel, model=AddBotToMatrixTaskModel, session=session
    )
    # endregion

    # region services
    telegram_user_service = providers.Factory(
        TelegramUserService, repository_telegram_user=repository_telegram_user
    )
    matrix_service = providers.Factory(
        MatrixService,
        repository_matrix=repository_matrix,
        repository_telegram_user=repository_telegram_user,
    )
    donate_service = providers.Factory(
        DonateService,
        repository_telegram_user=repository_telegram_user,
        repository_matrix=repository_matrix,
        repository_donate=repository_donate,
        repository_add_bot_to_matrix_task_model=repository_add_bot_to_matrix_task,
    )
    donate_confirm_service = providers.Factory(
        DonateConfirmService,
        repository_donate=repository_donate,
        repository_donate_transaction=repository_donate_transaction,
        repository_telegram_user=repository_telegram_user,
    )
    crypto_bot_api_service = providers.Factory(
        CryptoBotAPIService,
        base_url=config.provided.crypto_bot_api_base_url,
        api_token=config.provided.crypto_bot_api_token,
    )
    withdrawal_request_service = providers.Factory(
        WithdrawalRequestService,
        repository_withdrawal_request=repository_withdrawal_request,
    )
    add_bot_to_matrix_task_service = providers.Factory(
        AddBotToMatrixTaskModelService,
        repository_add_bot_to_matrix_task=repository_add_bot_to_matrix_task,
    )
    # endregion
