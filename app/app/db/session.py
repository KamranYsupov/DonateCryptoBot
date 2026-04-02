from contextvars import ContextVar

from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine

scope: ContextVar = ContextVar("db_session_scope")


def scopefunc():
    try:
        return scope.get()
    except LookupError:
        print("scope not set")


class SyncSession:
    def __init__(self, db_url: str):
        self.engine = create_engine(url=str(db_url), pool_pre_ping=True)
        self.session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(self.session_factory)

    def create_session(self):
        return self.Session()
