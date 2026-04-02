from flask import Flask, render_template, request, redirect
from flask_admin import Admin
from flask_login import LoginManager, login_user

from app.db.session import SyncSession
from app.core.config import settings

from app.admin.views.tg_user import TelegramUserView

from app.models.telegram_user import TelegramUser
from app.models.admin_user import AdminUser

from loguru import logger

session = SyncSession(db_url=settings.postgres_url)

secureApp = Flask(__name__)
login = LoginManager(secureApp)


@login.user_loader
def load_user(user_id):
    return (
        session.create_session()
        .query(AdminUser)
        .filter(AdminUser.id == user_id)
        .first()
    )


secureApp.config["SECRET_KEY"] = settings.secret_key


class Middleware:
    """Simple WSGI middleware"""

    def __init__(self, app, session_factory):
        self.app = app
        self.session_factory = session_factory

    def __call__(self, environ, start_response):
        session = self.session_factory
        try:
            return self.app(environ, start_response)
        except Exception as exc:
            print(exc)
            session.rollback()
        finally:
            session.expunge_all()
            session.close()


Middleware(secureApp.wsgi_app, session_factory=session)

# create administrator
admin = Admin(
    secureApp, name="Admin", base_template="my_master.html", template_mode="bootstrap4"
)
# Add view
admin.add_view(TelegramUserView(TelegramUser, session.Session))


@secureApp.route("/admin/login/", methods=["POST", "GET"])
def login():
    sync_session = session.create_session()
    if request.method == "POST":
        users_login = request.form.get("login")
        password = request.form.get("password")
        user = (
            sync_session.query(AdminUser)
            .filter(AdminUser.password == password, AdminUser.login == users_login)
            .first()
        )
        if user.is_active:
            logger.info("go to login")
            login_user(user)
        return redirect("/admin")
    else:
        return render_template("index.html")
