import uuid

from urllib.parse import urljoin

from app.core.config import settings

from sqlalchemy import Column, DateTime, BigInteger, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func


class UUIDMixin:
    """UUID миксин для ID моделей"""

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)


class TimestampedMixin:
    """Миксин для даты создания и даты обновления"""

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class AbstractTelegramUser:
    """Базовый пользователь телеграм"""

    user_id = Column(
        BigInteger, nullable=False, unique=True, index=True, doc="ID пользователя"
    )
    username = Column(String, nullable=True, doc="Username")
    first_name = Column(String, nullable=True, doc="Имя пользователя")
    last_name = Column(String, nullable=True, doc="Фамилия пользователя")
    is_active = Column(Boolean, default=True, doc="Активность")

    @property
    def full_name(self) -> str:
        """Получаем имя и фамилию пользователя вместе"""
        parts = [self.first_name, self.last_name]
        return " ".join(filter(None, parts))

    @property
    def full_username(self) -> str | None:
        """Получение username пользователя с возможностью перейти к нему."""
        return f"@{self.username}" if self.username else None

    @property
    def referral_url(self) -> str:
        """Получение реферальной ссылки, в качестве идентификатора используется Telegram ID пользователя"""

        if not isinstance(settings.bot_link, str) or not isinstance(
            settings.bot_name, str
        ):
            return "Ссылка на бота или имя бота не заданы в настройках."

        if "{}" not in settings.bot_link:
            return "Ссылка на бота не может быть отформатирована."

        if self.user_id is None:
            return "User ID не задан."

        return urljoin(
            base=settings.bot_link.format(bot_name=settings.bot_name),
            url=f"?start={self.user_id}",
        )


class AbstractAdminUser:
    """Базовая модель пользователя для административной панели"""

    login = Column(String(255), doc="Логин")
    password = Column(String(80), doc="Пароль")
    is_active = Column(Boolean, default=True, doc="Активность")
