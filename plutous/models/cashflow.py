from .base import BaseModel
from .types import Amount

from sqlmodel import (
    Field, Relationship, Column,
    Index, ForeignKey, DECIMAL,
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .transaction import Transaction
    from .t_account import TAccount


class Cashflow(BaseModel, table=True):
    __table_args__ = (
        Index(
            'ix_cashflows_transaction_id_t_account_id',
            'transaction_id', 't_account_id', unique=True
        ),
    )

    transaction_id: int = Field(
        sa_column=Column(
            ForeignKey('transactions.id'),
            nullable=False, index=True
        )
    )
    t_account_id: int = Field(
        sa_column=Column(
            ForeignKey('t_accounts.id'),
            nullable=False, index=True
        )
    )
    amount: Amount = Field(sa_column=Column(DECIMAL(20, 8), nullable=False))

    transaction: "Transaction" = Relationship()
    account: "TAccount" = Relationship()
