from aiogram import Router

from .start import start_router
from .donate import donate_router
from .info import info_router
from .ban_user import ban_user_router
from .referral_message import referral_router
from .payments import payment_router
from .withdrawal_request import withdrawal_requests_router
from .transfer import transfer_router
from .worker import worker_router
from .bill_type import bill_type_router
from .aggregators import aggregators_router
from .sponsors_contest import sponsors_contest_router

def get_all_routers() -> Router:
    """Функция для регистрации всех router"""

    router = Router()
    router.include_router(start_router)
    router.include_router(donate_router)
    router.include_router(info_router)
    router.include_router(ban_user_router)
    router.include_router(referral_router)
    router.include_router(payment_router)
    router.include_router(withdrawal_requests_router)
    router.include_router(transfer_router)
    router.include_router(worker_router)
    router.include_router(bill_type_router)
    router.include_router(aggregators_router)
    router.include_router(sponsors_contest_router)

    return router
