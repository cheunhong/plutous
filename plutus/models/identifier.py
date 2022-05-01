from sqlmodel import (
    Field, Relationship, Column,
    Index, ForeignKey, Text, String
)
from sqlalchemy.orm import relationship
from typing import TYPE_CHECKING, Optional
from .base import BaseModel

if TYPE_CHECKING:
    from .t_account import TAccount


class Identifier(BaseModel, table=True):
    __table_args__ = (
        Index(
            'ix_identifiers_keyword_base_account_id',
            'keyword', 'base_account_id', unique=True
        ),
    )

    keyword: str = Field(sa_column=Column(String(30)))
    description: str = Field(sa_column=Column(Text))
    tag_id: Optional[int] = Field(
        sa_column=Column(ForeignKey('tags.id'), index=True)
    )
    debit_account_id: Optional[int] = Field(
        sa_column=Column(
            ForeignKey('t_accounts.id'), index=True
        )
    )
    credit_account_id: Optional[int] = Field(
        sa_column=Column(ForeignKey('t_accounts.id'), index=True)
    )
    base_account_id: int = Field(
        sa_column=Column(
            ForeignKey('t_accounts.id'),
            index=True, nullable=False
        )
    )

    debit_account: Optional["TAccount"] = Relationship(
        sa_relationship=relationship(
            'TAccount', foreign_keys='Identifier.debit_account_id',
        )
    )
    credit_account: Optional["TAccount"] = Relationship(
        sa_relationship=relationship(
            'TAccount', foreign_keys='Identifier.credit_account_id',
        )
    )
    base_account: "TAccount" = Relationship(
        sa_relationship=relationship(
            'TAccount', foreign_keys='Identifier.base_account_id',
        )
    )
