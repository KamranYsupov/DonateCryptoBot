import os
import secrets
from enum import Enum

from pydantic import PostgresDsn, Field, computed_field
from pydantic_settings import BaseSettings


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


def field_validator(param, mode):
    pass


class Settings(BaseSettings):
    """Настройки проекта"""

    # region Настройки бота
    bot_token: str = Field(title="Токен бота")
    bot_name: str | None = Field(title="Имя бота", default=None)
    bot_link: str = Field(title="Ссылка на бота")
    chat_id: int = Field(title="ID чата")
    chat_link: str = Field(title="Ссылка на чат")
    channel_id: str = Field(title="ID канала")
    channel_link: str = Field(title="Ссылка на канал")
    group_link: str = Field(title="Ссылка на чат")
    presentation_link: str = Field(title="Ссылка на презентацию")
    donates_channel_id: int = Field(title="ID канала с донатами")
    donates_channel_link: str = Field(title="Ссылка на канал с донатами")
    web_app_link: str = Field(title="Ссылка на web app")
    message_per_second: float = Field(title="Кол-во сообщений в секунду", default=1)
    support_username: str = Field(title="Username аккаунта поддержки")
    log_level: LogLevel = Field(title="Уровень логирования", default=LogLevel.INFO)
    # endregion

    # region API
    api_prefix: str = Field(title="Префикс API", default="/api")
    # endregion

    debug: bool = Field(title="Режим отладки", default=True)
    secret_key: str = Field(
        title="Секретный ключ", default_factory=lambda: secrets.token_hex(16)
    )

    # region Настройки БД
    postgres_user: str = Field(title="Пользователь БД")
    postgres_password: str = Field(title="Пароль БД")
    postgres_host: str = Field(title="Хост БД")
    postgres_port: int = Field(title="Порт ДБ", default="5432")
    postgres_db: str = Field(title="Название БД")
    # endregion

    # region Настройки RabbitMQ
    rabbitmq_host: str = Field(title="Хост rabbitmq", default="guest:guest@rabbitmq")
    rabbitmq_port: int | str = Field(title="Порт rabbitmq", default=5672)
    # endregion

    # region Настройки Redis
    redis_host: str = Field(title="Хост redis", default="redis")
    redis_port: int | str = Field(title="Порт redis", default=6379)
    # endregion

    # region CryptoBot
    crypto_bot_api_token: str = Field(title="CryptoBot API token")
    crypto_bot_api_base_url: str = Field(
        title="CryptoBot API base url",
        default="https://pay.crypt.bot/api/",
    )
    # endregion

    database_url: PostgresDsn | None = Field(title="Ссылка БД", default=None)

    add_bot_to_matrix_1_countdown_minutes: int = 5
    add_bot_to_matrix_2_countdown_minutes: int = 15

    first_sponsor_donate_percent: int = 20
    second_sponsor_donate_percent: int = 10
    third_sponsor_donate_percent: int = 5

    matrix_donate_percent: int = 10

    withdrawal_min_tokens_count: int = 10

    level_length: int = 2
    second_level_length: int = 4
    third_level_length: int = 8
    fourth_level_length: int = 16
    matrix_max_length: int = 30
    matrix_max_level: int = 4

    telegram_server_host: str = Field(
        title="Telegram Local Server host",
        default="telegram-server",
    )
    telegram_server_port: int = Field(title="Telegram Local Server port", default=8081)
    telegram_app_api_id: int = Field(title="Telegram App API ID")
    telegram_app_api_hash: str = Field(title="Telegram App API Hash")

    @computed_field
    @property
    def telegram_server_url(self) -> str:
        return f"http://{self.telegram_server_host}:{self.telegram_server_port}"

    @computed_field
    @property
    def postgres_url(self) -> PostgresDsn:
        if self.database_url:
            return self.database_url
        return PostgresDsn.build(
            scheme="postgresql",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            path=f"{self.postgres_db}",
        )

    @computed_field
    @property
    def rabbitmq_url(self) -> str:
        return f"amqp://{self.rabbitmq_host}:{self.rabbitmq_port}/"

    @computed_field
    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/"

    @computed_field
    @property
    def celery_broker_url(self) -> str:
        return self.rabbitmq_url

    @computed_field
    @property
    def celery_backend_url(self) -> str:
        return f"{self.redis_url}/0"



class Config:
    env_file = ".env"


settings = Settings()
