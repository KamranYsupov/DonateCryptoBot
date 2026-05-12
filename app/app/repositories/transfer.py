import uuid
from typing import List

from sqlalchemy import select, delete, update, func
from sqlalchemy.orm import selectinload

from .base import RepositoryBase
from app.models.transfer import Transfer


class RepositoryTransfer(RepositoryBase[Transfer]):
    """Репозиторий конкурса кураторов"""