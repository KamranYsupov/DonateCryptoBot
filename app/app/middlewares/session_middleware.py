from contextlib import asynccontextmanager
from aiogram import BaseMiddleware


class SQLAlchemySessionMiddleware(BaseMiddleware):
    """Middleware для commit & close  session"""

    def __init__(self, sync_session):
        super().__init__()
        self._sync_session = sync_session

    async def __call__(self, handler, event, data):
        async with self.db_session_maker() as session:
            data["session"] = session
            return await handler(event, data)

    @asynccontextmanager
    async def db_session_maker(self):
        try:
            yield self._sync_session
            self._sync_session.commit()
        except Exception as e:
            self._sync_session.rollback()
            raise e
        finally:
            self._sync_session.close()
