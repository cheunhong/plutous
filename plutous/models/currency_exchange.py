from sqlmodel import (
    Field, Relationship, Column,
    ForeignKey, DECIMAL, Session, text
)
from sqlalchemy.dialects.mysql import TIMESTAMP
from sqlalchemy.orm import relationship
from typing import TYPE_CHECKING, Optional
from datetime import datetime

from .transaction import Transaction, Transactable, DoubleEntry
from .types import Amount

if TYPE_CHECKING:
    from typing_extensions import Self
    from .t_account import TAccount
    from .trade import Trade


class CurrencyExchange(Transactable, DoubleEntry, table=True):
    debit_account_id: int = Field(
        sa_column=Column(
            ForeignKey('t_accounts.id'),
            index=True, nullable=False
        )
    )
    credit_account_id: int = Field(
        sa_column=Column(
            ForeignKey('t_accounts.id'),
            index=True, nullable=False
        )
    )
    debit_amount: Amount = Field(
        sa_column=Column(DECIMAL(20, 8), nullable=False)
    )
    credit_amount: Amount = Field(
        sa_column=Column(DECIMAL(20, 8), nullable=False)
    )
    trade_id: Optional[int] = Field(
        sa_column=Column(ForeignKey('trades.id'), index=True)
    )
    transacted_at: datetime = Field(
        sa_column=Column(
            TIMESTAMP(fsp=6), nullable=False,
            server_default=text("CURRENT_TIMESTAMP(6)")
        )
    )

    debit_account: "TAccount" = Relationship(
        sa_relationship=relationship(
            'TAccount', foreign_keys='CurrencyExchange.debit_account_id',
        )
    )
    credit_account: "TAccount" = Relationship(
        sa_relationship=relationship(
            'TAccount', foreign_keys='CurrencyExchange.credit_account_id',
        )
    )
    trade: Optional["Trade"] = Relationship(
        back_populates='currency_exchanges'
    )

    def add(
        self, session: Session,
        refresh: Optional[bool] = True,
    ) -> "Self":
        return self._add(
            session=session,
            refresh=refresh,
            before_insert=['check_attrs', 'check_account'],
        )

    def record_transactions(self):
        params = {
            'transactable_type': self.transactable_type,
            'transacted_at': self.transacted_at,
            'transactable_id': self.id,
        }
        ce_account1 = self.get_transactable_account(self.debit_currency)
        ce_account2 = self.get_transactable_account(self.credit_currency)
        t1 = Transaction(
            debit_account=self.debit_account,
            credit_account=ce_account1,
            amount=self.debit_amount,
            **params,
        )
        t2 = Transaction(
            credit_account=self.credit_account,
            debit_account=ce_account2,
            amount=self.credit_amount,
            **params,
        )
        t1._trade = self.trade
        t2._trade = self.trade
        t1.add(self.session)
        t2.add(self.session)

    def update_transactions(self):
        ce_account1 = self.get_transactable_account(self.debit_currency)
        ce_account2 = self.get_transactable_account(self.credit_currency)
        old_debit_account_id = self.get_last_state('debit_account_id')
        for transaction in self.transactions:
            if transaction.debit_account_id == old_debit_account_id:
                amount = self.debit_amount
                debit_account = self.debit_account
                credit_account = ce_account1
            else:
                amount = self.credit_amount
                debit_account = ce_account2
                credit_account = self.credit_account
            transaction.amount = amount
            transaction.debit_account = debit_account
            transaction.credit_account = credit_account
            transaction.add(self.session)
