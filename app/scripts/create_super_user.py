import random
import string
import enum

from loguru import logger

from app.models.admin_user import AdminUser
from app.db.session import SyncSession
from app.core.config import settings


class Answers(enum.Enum):
    yes = "y"
    no = "n"


class SuperUserGenerator:
    """Класс для генерации суперпользователя."""

    def __init__(self, sync_session):
        self._sync_session = sync_session

    @staticmethod
    def _get_user_input(prompt, valid_options=None):
        while True:
            user_input = input(prompt)
            if valid_options and user_input not in [
                option.value for option in valid_options
            ]:
                logger.info(
                    f"Некорректный ввод: {', '.join(option.value for option in valid_options)}."
                )
                continue
            return user_input

    @staticmethod
    def _generate_password(length=12):
        characters = string.ascii_letters + string.digits + string.punctuation
        return "".join(random.choice(characters) for _ in range(length))

    def create_superuser(self):
        self.login = self._get_user_input("Введите логин: ")
        custom_password = self._get_user_input(
            "Хотите ли вы задать свой пароль? (y/n): ", [Answers.yes, Answers.no]
        )
        if custom_password == Answers.yes.value:
            self.password = self._get_user_input("Введите пароль: ")
        else:
            self.password = self._generate_password()
            logger.info(f"Пароль сгенерирован: {self.password}")

    def save_to_database(self):
        admin_user = AdminUser(login=self.login, password=self.password, is_active=True)
        self._sync_session.session.add(admin_user)
        self._sync_session.session.commit()
        self._sync_session.session.close()
        logger.info("Superuser saved to database successfully.")

    def display_credentials(self):
        logger.info(
            f"\nСуперпользователь создан!\nLogin: {self.login}\nPassword: {self.password}"
        )


if __name__ == "__main__":
    session = SyncSession(db_url=settings.postgres_url)

    superuser_generator = SuperUserGenerator(session)
    superuser_generator.create_superuser()
    superuser_generator.save_to_database()
    superuser_generator.display_credentials()
