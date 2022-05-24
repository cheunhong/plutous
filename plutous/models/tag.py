from sqlmodel import Field, Relationship, Column, ForeignKey, String
from sqlalchemy.orm import relationship
from typing import TYPE_CHECKING, Optional

from .base import BaseModel

if TYPE_CHECKING:
    from .t_account import TAccount


class Tag(BaseModel, table=True):
    name: str = Field(
        sa_column=Column(
            String(50), nullable=False, unique=True,
        )
    )
    debit_account_id: int = Field(
        sa_column=Column(
            ForeignKey('t_accounts.id'),
            index=True, nullable=False,
        )
    )
    credit_account_id: int = Field(
        sa_column=Column(
            ForeignKey('t_accounts.id'),
            index=True, nullable=False,
        )
    )

    debit_account: "TAccount" = Relationship(
        sa_relationship=relationship(
            'TAccount', primaryjoin='Tag.debit_account_id == TAccount.id'
        )
    )
    credit_account: "TAccount" = Relationship(
        sa_relationship=relationship(
            'TAccount', primaryjoin='Tag.credit_account_id == TAccount.id'
        )
    )
