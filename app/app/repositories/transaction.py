from .base import RepositoryBase
from app.models.transaction import Transaction


class RepositoryTransaction(RepositoryBase[Transaction]):
    """Репозиторий транзакции"""
