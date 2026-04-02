from .base import RepositoryBase
from app.models.admin_user import AdminUser


class RepositoryAdminUser(RepositoryBase[AdminUser]):
    """Репозиторий супер пользователя"""
