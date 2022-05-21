from sqlmodel import Field, Relationship, Column, ForeignKey, DECIMAL, text
from sqlalchemy.dialects.mysql import TIMESTAMP
from typing import TYPE_CHECKING, Optional
from datetime import datetime
from .transaction import Transaction, Transactable, SingleEntry
from .types import Amount

if TYPE_CHECKING:
    from .transaction import Transaction
    from .t_account import TAccount
    from .trade import Trade


class RealizedPnl(Transactable, SingleEntry, table=True):
    trade_id: int = Field(
        sa_column=Column(
            ForeignKey('trades.id'), index=True,
            unique=True, nullable=False,
        )
    )
    t_account_id: int = Field(
        sa_column=Column(
            ForeignKey('t_accounts.id'),
            nullable=False, index=True,
        )
    )
    amount: Amount = Field(sa_column=Column(DECIMAL(20, 8), nullable=False))
    granted_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(fsp=6), nullable=False,
            server_default=text("CURRENT_TIMESTAMP(6)"),
        )
    )

    trade: "Trade" = Relationship(back_populates='realized_pnls')
    t_account: "TAccount" = Relationship(back_populates='realized_pnls')

    def record_transactions(self):
        transactable_account = self.get_transactable_account()
        debit_account, credit_account = (
            (self.t_account, transactable_account)
            if self.amount >= 0.0 else
            (transactable_account, self.t_account)
        )
        Transaction(
            debit_account=debit_account,
            credit_account=credit_account,
            amount=abs(self.amount),
            transacted_at=self.granted_at,
            transactable_id=self.id,
            transactable_type=self.transactable_type,
        ).add(self.session)

    def update_transactions(self):
        transactable_account = self.get_transactable_account()
        debit_account, credit_account = (
            (self.t_account, transactable_account)
            if self.amount >= 0.0 else
            (transactable_account, self.t_account)
        )
        transaction = self.transactions[0]
        transaction.debit_account = debit_account
        transaction.credit_account = credit_account
        transaction.amount = self.amount
        transaction.transacted_at = self.granted_at
        transaction.add(self.session)
