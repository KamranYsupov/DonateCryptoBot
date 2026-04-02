from uuid import UUID
from typing import Generic, Optional, Type, TypeVar

from sqlalchemy.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import select, update, delete


ModelType = TypeVar("ModelType")


class RepositoryBase(Generic[ModelType,]):
    """Репозиторий с базовым CRUD"""

    def __init__(self, model: Type[ModelType], session) -> None:
        self._model = model
        self._session = session

    def create(self, obj_in) -> ModelType:
        obj_in_data = dict(obj_in)
        db_obj = self._model(**obj_in_data)

        self._session.add(db_obj)
        self._session.flush()

        return db_obj

    def get(
        self,
        *args,
        **kwargs,
    ) -> Optional[ModelType]:
        statement = (
            select(self._model)
            .filter(*args)
            .filter_by(**kwargs)
            .order_by(self._model.created_at)
        )
        return self._session.execute(statement).scalars().first()

    def list(self, *args, **kwargs):
        statement = select(self._model).filter(*args).filter_by(**kwargs)
        return self._session.execute(statement).scalars().all()

    def update(self, *, obj_id: UUID, obj_in) -> ModelType:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)

        statement = (
            update(self._model).where(self._model.id == obj_id).values(**update_data)
        )
        self._session.execute(statement)

        return self._session.get(self._model, obj_id)

    def delete(self, *args, obj_id: UUID, **kwargs) -> None:
        statement = delete(self._model).where(self._model.id == obj_id)
        self._session.execute(statement)

    def exists(self, *args, **kwargs) -> bool:
        try:
            statement = select(self._model).filter(*args).filter_by(**kwargs)
            self._session.execute(statement).one()
            return True
        except NoResultFound:
            return False
        except MultipleResultsFound:
            return False
