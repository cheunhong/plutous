from sqlmodel import Field, Relationship, Column, ForeignKey, DECIMAL, text
from sqlalchemy.dialects.mysql import TIMESTAMP
from typing import TYPE_CHECKING, Optional
from datetime import datetime
from .transaction import Transaction, Transactable, SingleEntry
from .types import Amount

if TYPE_CHECKING:
    from .t_account import TAccount
    from .trade import Trade


class Commission(Transactable, SingleEntry, table=True):
    trade_id: int = Field(
        sa_column=Column(
            ForeignKey('trades.id'), index=True,
            unique=True, nullable=False,
        )
    )
    t_account_id: int = Field(
        sa_column=Column(
            ForeignKey('t_accounts.id'),
            nullable=False, index=True
        )
    )
    amount: Amount = Field(sa_column=Column(DECIMAL(20, 8), nullable=False))
    charged_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(fsp=6), nullable=False,
            server_default=text("CURRENT_TIMESTAMP(6)")
        )
    )

    trade: "Trade" = Relationship(back_populates='commissions')
    t_account: "TAccount" = Relationship(back_populates='commissions')

    def record_transactions(self):
        Transaction(
            debit_account=self.get_transactable_account(),
            credit_account=self.t_account,
            amount=self.amount,
            transacted_at=self.charged_at,
            transactable_id=self.id,
            transactable_type=self.transactable_type,
        ).add(self.session)

    def update_transactions(self):
        transaction = self.transactions[0]
        transaction.debit_account = self.get_transactable_account()
        transaction.credit_account = self.t_account
        transaction.amount = self.amount
        transaction.transacted_at = self.charged_at
        transaction.add(self.session)
