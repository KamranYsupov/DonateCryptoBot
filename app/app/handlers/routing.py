from aiogram import Router

from .start import start_router
from .donate import donate_router
from .info import info_router
from .ban_user import ban_user_router
from .referral_message import referral_router

def get_all_routers() -> Router:
    """Функция для регистрации всех router"""

    router = Router()
    router.include_router(start_router)
    router.include_router(donate_router)
    router.include_router(info_router)
    router.include_router(ban_user_router)
    router.include_router(referral_router)


    return router
