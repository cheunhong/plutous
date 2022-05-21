from sqlmodel import SQLModel, Field, Column, Session, text
from sqlalchemy.dialects.mysql import INTEGER, TIMESTAMP
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Query, InstanceState
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import inspect
from typing import TYPE_CHECKING, Optional, List
import inflect
import re

if TYPE_CHECKING:
    from typing_extensions import Self


class BaseModel(SQLModel):
    __refresh_cols__ = ['id']
    id: Optional[int] = Field(sa_column=Column(INTEGER(10), primary_key=True))

    @declared_attr
    def created_at(cls):
        return Column(
            TIMESTAMP(fsp=6), nullable=False,
            server_default=text("CURRENT_TIMESTAMP(6)")
        )

    @declared_attr
    def updated_at(cls):
        return Column(
            TIMESTAMP(fsp=6), nullable=False,
            server_default=text(
                "CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)"
            )
        )

    @declared_attr
    def __tablename__(cls):
        engine = inflect.engine()
        tablename = re.sub('(?<!^)(?=[A-Z])', '_', cls.__name__).lower()
        return engine.plural(tablename)

    @property
    def state(self) -> InstanceState:
        return inspect(self)

    @property
    def session(self) -> Session:
        return self.state.session

    @classmethod
    def query(cls, session: Session, *args, **kwargs) -> Query:
        q = session.query(cls)
        for arg in args:
            q = q.filter(arg)
        for attr, val in kwargs.items():
            if isinstance(val, list):
                if len(val):
                    q = q.filter(getattr(cls, attr).in_(val))
            elif isinstance(val, tuple):
                if len(tuple) != 2:
                    raise ValueError(f"""
                        Tuple range filter only accept 2 elements.
                        Inputted tuple {attr}: {val}
                    """)
                if val[0]:
                    q = q.filter(getattr(cls, attr) >= (val[0]))
                if val[1]:
                    q = q.filter(getattr(cls, attr) <= (val[1]))
            else:
                q = q.filter(getattr(cls, attr) == val)
        return q

    @classmethod
    def get_first(cls, session: Session, *args, **kwargs) -> "Self":
        return cls.query(session, *args, **kwargs).first()

    @classmethod
    def get_all(cls, session: Session, *args, **kwargs) -> List["Self"]:
        return cls.query(session, *args, **kwargs).all()

    @classmethod
    def exists(cls, session: Session, *args, **kwargs) -> bool:
        return session.query(
            cls.query(session, *args, **kwargs).exists()
        ).first()[0]

    def get_last_state(self, attr: str):
        return self.state.attrs[attr].history.non_added()[0]

    def get(self, session: Session, *args, **kwargs) -> "Self":
        params = {
            key: val
            for key, val in self.dict().items()
            if val is not None
        }
        kwargs = {**kwargs, **params}
        return self.query(session, *args, **kwargs).one()

    def add(
        self, session: Session,
        refresh: Optional[bool] = True,
    ) -> "Self":
        return self._add(session, refresh)

    def delete(self):
        return self._delete()

    def acquire(self, session: Session, *args, **kwargs) -> "Self":
        try:
            return self.get(session, *args, **kwargs)
        except NoResultFound:
            return self.add(session)

    def _add(
        self, session: Session,
        refresh: Optional[bool] = True,
        before_insert: Optional[List[str]] = [],
        after_insert: Optional[List[str]] = [],
        before_update: Optional[List[str]] = [],
    ) -> "Self":
        mode = 'insert'
        for func in before_insert:
            getattr(self, func)()

        if self.id:
            mode = 'update'
            for func in before_update:
                getattr(self, func)()

        session.add(self)
        session.flush()
        if refresh:
            session.refresh(self, self.__refresh_cols__)

        if mode == 'insert':
            for func in after_insert:
                getattr(self, func)()
        return self

    def _delete(
        self, on_delete: Optional[List[str]] = [],
    ) -> "Self":
        for func in on_delete:
            getattr(self, func)()
        self.session.delete(self)
