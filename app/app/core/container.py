from dependency_injector import containers, providers

from app.core.config import Settings
from app.db.session import SyncSession
from app.repositories.donate import RepositoryDonate, RepositoryDonateTransaction

from app.repositories.telegram_user import RepositoryTelegramUser
from app.repositories.admin_user import RepositoryAdminUser
from app.repositories.matrix import RepositoryMatrix
from app.repositories.transaction import RepositoryTransaction

from app.models.telegram_user import TelegramUser
from app.models.admin_user import AdminUser
from app.models.donate import Donate, DonateTransaction
from app.models.matrix import Matrix
from app.models.transaction import Transaction
from app.services.donate_confirm_service import DonateConfirmService

from app.services.telegram_user_service import TelegramUserService
from app.services.matrix_service import MatrixService
from app.services.donate_service import DonateService


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "app.handlers.donate",
            "app.handlers.start",
            "app.handlers.info",
            "app.handlers.ban_user",
            "app.handlers.referral_message",
            "app.middlewares.ban_user",
            "app.middlewares.subscriptions",
            "app.tasks.donate",
            "app.utils.excel",
        ]
    )

    config = providers.Singleton(Settings)
    db = providers.Singleton(SyncSession, db_url=config.provided.postgres_url)
    session = providers.Factory(db().create_session)

    # region repository
    repository_telegram_user = providers.Singleton(
        RepositoryTelegramUser, model=TelegramUser, session=session
    )
    repository_admin_user = providers.Singleton(
        RepositoryAdminUser, model=AdminUser, session=session
    )
    repository_matrix = providers.Singleton(
        RepositoryMatrix, model=Matrix, session=session
    )
    repository_wallet_recharge = providers.Singleton(
        RepositoryTransaction, model=Transaction, session=session
    )
    repository_donate = providers.Singleton(
        RepositoryDonate,
        model=Donate,
        session=session,
    )
    repository_donate_transaction = providers.Singleton(
        RepositoryDonateTransaction,
        model=DonateTransaction,
        session=session,
    )
    # endregion

    # region services
    telegram_user_service = providers.Singleton(
        TelegramUserService, repository_telegram_user=repository_telegram_user
    )
    matrix_service = providers.Singleton(
        MatrixService,
        repository_matrix=repository_matrix,
        repository_telegram_user=repository_telegram_user,
    )
    donate_service = providers.Singleton(
        DonateService,
        repository_telegram_user=repository_telegram_user,
        repository_matrix=repository_matrix,
        repository_donate=repository_donate,
    )
    donate_confirm_service = providers.Singleton(
        DonateConfirmService,
        repository_donate=repository_donate,
        repository_donate_transaction=repository_donate_transaction,
        repository_telegram_user=repository_telegram_user,
    )
    # endregion
