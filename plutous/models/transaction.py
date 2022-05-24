import re

from sqlmodel import (
    Field, Relationship, Column, ForeignKey,
    Index, DECIMAL, String, Text, Session, text
)
from sqlalchemy.dialects.mysql import TIMESTAMP, INTEGER
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship
from typing import TYPE_CHECKING, Optional, List
from pydantic.fields import ModelPrivateAttr
from pydantic import PrivateAttr
from datetime import datetime

from .enums import PositionFlowType, Action
from .position_flow import PositionFlow
from .position import Position
from .base import BaseModel
from .types import Amount
from .group import Group

if TYPE_CHECKING:
    from typing_extensions import Self
    from .currency_exchange import CurrencyExchange
    from .realized_pnl import RealizedPnl
    from .commission import Commission
    from .t_account import TAccount
    from .deposit import Deposit
    from .trade import Trade


def transactable_join(classname: str):
    return f"""and_(
        Transaction.transactable_id == {classname}.id,
        Transaction.transactable_type == '{classname}'
    )"""


class SingleEntry(BaseModel):
    @property
    def currency(self) -> str:
        return self.t_account.currency

    @property
    def user_id(self) -> int:
        return self.t_account.user_id

    def check_attrs(self):
        if (self.t_account_id is not None) & (not self.t_account):
            raise ValueError(
                f'Please provide t_account relationship as it is needed for validity checks'
            )


class DoubleEntry(BaseModel):
    @property
    def currency(self) -> str:
        return (
            self.debit_currency
            or self.credit_currency
        )

    @property
    def debit_currency(self) -> Optional[str]:
        if self.debit_account:
            return self.debit_account.currency

    @property
    def credit_currency(self) -> Optional[str]:
        if self.credit_account:
            return self.credit_account.currency

    @property
    def debit_user_id(self) -> Optional[int]:
        if self.debit_account:
            return self.debit_account.user_id

    @property
    def credit_user_id(self) -> Optional[int]:
        if self.credit_account:
            return self.credit_account.user_id

    @property
    def same_currency(self) -> bool:
        debit_currency = self.debit_currency
        credit_currency = self.credit_currency

        if debit_currency and credit_currency:
            if debit_currency != credit_currency:
                return False
        return True

    @property
    def same_user(self) -> bool:
        return self.debit_user_id == self.credit_user_id

    @property
    def same_account(self) -> bool:
        return self.debit_account.account_id == self.credit_account.account_id

    def check_attrs(self):
        def msg(account: str) -> str:
            return f'Please provide {account} relationship as it is needed for validity checks'
        if (self.debit_account_id is not None) & (not self.debit_account):
            raise ValueError(msg('debit_account'))
        if (self.credit_account_id is not None) & (not self.credit_account):
            raise ValueError(msg('credit_account'))

    def check_currency(self):
        if not self.same_currency:
            raise ValueError(
                'debit_account and credit_account has different currency'
            )

    def check_user(self):
        if not self.same_user:
            raise ValueError(
                'debit_account and credit_account has different user_id'
            )

    def check_account(self):
        if not self.same_account:
            raise ValueError(
                'debit_account and credit_account has different account_id'
            )


class Transaction(DoubleEntry, table=True):
    __table_args__ = (
        Index(
            'ix_transactions_transactable_entries',
            'transactable_type', 'transactable_id',
            'debit_account_id', unique=True
        ),
    )

    amount: Amount = Field(
        sa_column=Column(
            DECIMAL(20, 8), nullable=False,
            server_default=text("'0.00000000'")
        )
    )
    tag_id: Optional[int] = Field(
        sa_column=Column(ForeignKey('tags.id'), index=True)
    )
    description: str = Field(sa_column=Column(Text))
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
    transacted_at: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(fsp=6), nullable=False,
            server_default=text("CURRENT_TIMESTAMP(6)")
        )
    )
    transactable_id: Optional[int] = Field(sa_column=Column(INTEGER(10)))
    transactable_type: Optional[str] = Field(sa_column=Column(String(20)))

    debit_account: Optional["TAccount"] = Relationship(
        sa_relationship=relationship(
            'TAccount', foreign_keys='Transaction.debit_account_id',
        )
    )
    credit_account: Optional["TAccount"] = Relationship(
        sa_relationship=relationship(
            'TAccount', foreign_keys='Transaction.credit_account_id',
        )
    )

    currency_exchange: Optional["CurrencyExchange"] = Relationship(
        sa_relationship=relationship(
            'CurrencyExchange', viewonly=True,
            foreign_keys='Transaction.transactable_id',
            primaryjoin=transactable_join('CurrencyExchange'),

        )
    )
    deposit: Optional["Deposit"] = Relationship(
        sa_relationship=relationship(
            'Deposit', viewonly=True,
            foreign_keys='Transaction.transactable_id',
            primaryjoin=transactable_join('Deposit'),
        )
    )
    trade: Optional["Trade"] = Relationship(
        sa_relationship=relationship(
            'Trade', viewonly=True,
            foreign_keys='Transaction.transactable_id',
            primaryjoin=transactable_join('Trade'),
        )
    )
    commission: Optional["Commission"] = Relationship(
        sa_relationship=relationship(
            'Commission', viewonly=True,
            foreign_keys='Transaction.transactable_id',
            primaryjoin=transactable_join('Commission'),
        )
    )
    realized_pnl: Optional["RealizedPnl"] = Relationship(
        sa_relationship=relationship(
            'RealizedPnl', viewonly=True,
            foreign_keys='Transaction.transactable_id',
            primaryjoin=transactable_join('RealizedPnl'),
        )
    )
    position_flows: List["PositionFlow"] = (
        Relationship(back_populates='transaction')
    )
    _trade = PrivateAttr(default={})

    def get_trade(self) -> "Trade":
        if not isinstance(self._trade, ModelPrivateAttr):
            return self._trade
        if self.transactable_type == 'CurrencyExchange':
            return self.currency_exchange.trade
        elif self.transactable_type == 'Trade':
            return self.trade

    def add(
        self, session: Session,
        refresh: Optional[bool] = True,
    ) -> "Self":
        return self._add(
            session=session,
            refresh=refresh,
            before_insert=['check_attrs', 'check_currency'],
            after_insert=['record_position_flow'],
        )

    def record_position_flow(self):
        debit_account, credit_account = self.debit_account, self.credit_account
        debit_account = debit_account if debit_account.is_investment else None
        credit_account = credit_account if credit_account.is_investment else None

        if not (debit_account or credit_account):
            return

        buy, sell = None, None
        trade = self.get_trade()

        if trade:
            buy, sell = (
                (trade.code, trade.currency)
                if trade.action == Action.buy
                else (trade.currency, trade.code)
            )

            if trade.currency in trade.cash_equivalents:
                cost = trade.price * trade.size
            else:
                code = trade.currency if trade.action == Action.buy else trade.code
                size = (
                    trade.size if trade.action == Action.buy
                    else trade.size * trade.price
                )
                position: Position = (
                    trade.account.active_positions
                    .filter_by(code=code).one()
                )
                cost = position.entry_price * size
        else:
            if credit_account:
                from_position: Position = (
                    credit_account.active_positions
                    .filter_by(code=credit_account.currency).one()
                )
                cost = self.amount * from_position.entry_price
            else:
                if debit_account.is_cash:
                    cost = self.amount
                else:
                    cost = 0

        params = {
            'price': round(cost / self.amount, 8),
            'size': self.amount,
            'transacted_at': self.transacted_at,
            'transaction_id': self.id,
            'trade_id': trade.id if trade else None,
        }

        if debit_account:
            exists = PositionFlow.exists(
                self.session,
                transaction_id=self.id,
                type=PositionFlowType.increase,
            )
            if not exists:
                position = debit_account.acquire_position(buy)
                position.increase(**params)

        if credit_account:
            exists = PositionFlow.exists(
                self.session,
                transaction_id=self.id,
                type=PositionFlowType.decrease,
            )
            if not exists:
                params['size'] = -1 * params['size']
                position = credit_account.acquire_position(sell)
                position.decrease(**params)


class Transactable(BaseModel):
    @declared_attr
    def transactions(cls) -> List[Transaction]:
        return relationship(
            'Transaction', viewonly=True,
            uselist=True, foreign_keys=f'{cls.__name__}.id',
            primaryjoin=transactable_join(cls.__name__),
        )

    @property
    def transactable_type(self) -> str:
        return self.__class__.__name__

    def get_transactable_account(
            self, currency: Optional[str] = None,
    ) -> "TAccount":
        if not currency:
            currency = self.currency
        name = re.sub('(?<!^)(?=[A-Z])', '_', self.__class__.__name__).lower()
        return (
            Group(name=name).get(self.session)
            .acquire_t_account(currency)
        )

    def _add(
        self, session: Session,
        refresh: Optional[bool] = True,
        before_insert: Optional[List[str]] = ['check_attrs'],
        after_insert: Optional[List[str]] = ['record_transactions'],
        before_update: Optional[List[str]] = ['update_transactions'],
    ) -> "Self":
        return super()._add(
            session=session,
            refresh=refresh,
            before_insert=before_insert,
            after_insert=after_insert,
            before_update=before_update,
        )
