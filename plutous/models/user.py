from sqlmodel import Field, Relationship, Column, String
from typing import TYPE_CHECKING, List

from .base import BaseModel

if TYPE_CHECKING:
    from .account import Account


class User(BaseModel, table=True):
    name: str = Field(sa_column=Column(String(20), unique=True))

    accounts: List["Account"] = Relationship(back_populates='user')
