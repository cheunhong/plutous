from .transaction import Transaction, DoubleEntry, Transactable
from .types import Amount

from sqlmodel import (
    Field, Relationship, Index, Column,
    ForeignKey, DECIMAL, Session, String, text
)
from sqlalchemy.dialects.mysql import TIMESTAMP
from sqlalchemy.orm import relationship
from typing import TYPE_CHECKING, Optional
from datetime import datetime

if TYPE_CHECKING:
    from typing_extensions import Self
    from .t_account import TAccount


class Deposit(Transactable, DoubleEntry, table=True):
    __table_args__ = (
        Index(
            'ix_deposits_debit_account_id_debit_reference_id',
            'debit_account_id', 'debit_reference_id', unique=True,
        ),
        Index(
            'ix_deposits_credit_account_id_credit_reference_id',
            'credit_account_id', 'credit_reference_id', unique=True,
        ),
    )

    debit_account_id: Optional[int] = Field(
        sa_column=Column(ForeignKey('t_accounts.id'))
    )
    credit_account_id: Optional[int] = Field(
        sa_column=Column(ForeignKey('t_accounts.id'))
    )
    amount: Amount = Field(sa_column=Column(DECIMAL(20, 8), nullable=False))
    debit_reference_id: Optional[str] = Field(sa_column=Column(String(100)))
    credit_reference_id: Optional[str] = Field(sa_column=Column(String(100)))
    unique_reference_id: Optional[str] = Field(sa_column=Column(String(100)))
    network: str = Field(sa_column=Column(String(10), nullable=False))
    transacted_at: datetime = Field(
        sa_column=Column(
            TIMESTAMP(fsp=6), nullable=False,
            server_default=text("CURRENT_TIMESTAMP(6)")
        )
    )

    debit_account: Optional["TAccount"] = Relationship(
        sa_relationship=relationship(
            'TAccount', foreign_keys='Deposit.debit_account_id',
        )
    )
    credit_account: Optional["TAccount"] = Relationship(
        sa_relationship=relationship(
            'TAccount', foreign_keys='Deposit.credit_account_id',
        )
    )

    def add(
        self, session: Session,
        refresh: Optional[bool] = True,
    ) -> "Self":
        return self._add(
            session=session,
            refresh=refresh,
            before_insert=['check_attrs', 'check_currency'],
        )

    def record_transactions(self):
        params = {
            'transactable_type': self.transactable_type,
            'transacted_at': self.transacted_at,
            'transactable_id': self.id,
            'amount': self.amount,
        }
        if self.same_user:
            Transaction(
                credit_account=self.credit_account,
                debit_account=self.debit_account,
                **params,
            ).add(self.session)
        else:
            deposit = self.get_transactable_account()
            if self.debit_account_id:
                Transaction(
                    debit_account=self.debit_account,
                    credit_account=deposit,
                    **params,
                ).add(self.session)
            if self.credit_account_id:
                Transaction(
                    credit_account=self.credit_account,
                    debit_account=deposit,
                    **params,
                ).add(self.session)

    def update_transactions(self):
        deposit = self.get_transactable_account()
        old_debit_account_id = self.get_last_state('debit_account_id')
        old_credit_account_id = self.get_last_state('credit_account_id')
        for transaction in self.transactions:
            transaction.transacted_at = self.transacted_at
            transaction.amount = self.amount
            if (
                (transaction.debit_account_id == old_debit_account_id)
                | ((not old_debit_account_id) & self.same_user)
            ):
                transaction.debit_account = (self.debit_account or deposit)
            if (
                (transaction.credit_account_id == old_credit_account_id)
                | ((not old_credit_account_id) & self.same_user)
            ):
                transaction.credit_account = (self.credit_account or deposit)

            transaction.add(self.session)

        params = {
            'transactable_type': self.transactable_type,
            'transacted_at': self.transacted_at,
            'transactable_id': self.id,
            'amount': self.amount,
        }
        if self.debit_user_id != self.credit_user_id:
            if (not old_debit_account_id) & self.debit_account_id:
                Transaction(
                    debit_account=self.debit_account,
                    credit_account=deposit,
                    **params,
                ).add(self.session)
            if (not old_credit_account_id) & self.credit_account_id:
                Transaction(
                    debit_account=self.debit_account,
                    credit_account=deposit,
                    **params,
                ).add(self.session)
