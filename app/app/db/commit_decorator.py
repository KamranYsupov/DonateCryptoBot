from functools import wraps

from dependency_injector.wiring import inject

from app.core.container import Container


@inject
def commit_and_close_session(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        session = Container.session()
        try:
            result = await func(*args, **kwargs)
            session.commit()
            return result
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    return wrapper
