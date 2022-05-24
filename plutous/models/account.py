from sqlmodel import Field, Relationship, Column, ForeignKey, String, Boolean
from sqlalchemy.dialects.mysql import INTEGER, TIMESTAMP
from sqlalchemy.orm import relationship, AppenderQuery
from typing import TYPE_CHECKING, Optional, Dict
from pydantic import PrivateAttr
from datetime import datetime

from .enums import TAccountType, AssetType, PositionSide
from .currency_exchange import CurrencyExchange
from .t_account import TAccount
from .position import Position
from .base import BaseModel

if TYPE_CHECKING:
    from .currency_exchange import CurrencyExchange
    from .funding_fee import FundingFee
    from .t_account import TAccount
    from .position import Position
    from .platform import Platform
    from .trade import Trade
    from .user import User


class Account(BaseModel, table=True):
    name: str = Field(
        sa_column=Column(
            String(20), unique=True, nullable=False,
        )
    )
    user_id: int = Field(
        sa_column=Column(
            ForeignKey('users.id'),
            index=True, nullable=False,
        )
    )
    platform_id: int = Field(
        sa_column=Column(
            ForeignKey('platforms.id'),
            index=True, nullable=False,
        )
    )
    reference_id: Optional[int] = Field(sa_column=Column(INTEGER(10)))
    init_balance_at: Optional[datetime] = Field(
        sa_column=Column(TIMESTAMP(fsp=6))
    )
    is_investment: bool = Field(sa_column=Column(Boolean))

    user: "User" = Relationship(back_populates='accounts')
    platform: "Platform" = Relationship(back_populates='accounts')
    t_accounts: AppenderQuery = Relationship(
        sa_relationship=relationship('TAccount', lazy='dynamic')
    )
    positions: AppenderQuery = Relationship(
        sa_relationship=relationship(
            'Position', back_populates='account',
            lazy='dynamic', order_by='desc(Position.opened_at)',
        )
    )
    trades: AppenderQuery = Relationship(
        sa_relationship=relationship(
            'Trade', back_populates='account',
            lazy='dynamic', order_by='desc(Trade.transacted_at)',
        )
    )
    funding_fees: AppenderQuery = Relationship(
        sa_relationship=relationship(
            'FundingFee', back_populates='account',
            lazy='dynamic', order_by='desc(FundingFee.charged_at)',
        )
    )

    _t_accounts = PrivateAttr(default={})
    _positions = PrivateAttr(default={})

    @property
    def active_positions(self) -> AppenderQuery:
        return self.positions.filter_by(closed_at=None)

    def get_latest_trade(self, asset_type: AssetType) -> "Trade":
        return (
            self.trades
            .filter_by(asset_type=asset_type)
            .limit(1).first()
        )

    def get_latest_funding_history(
        self, asset_type: AssetType, **kwargs
    ) -> "FundingFee":
        return (
            self.funding_fees
            .filter_by(asset_type=asset_type, **kwargs)
            .limit(1).first()
        )

    def get_last_transacted_at(
        self, asset_type: AssetType,
        since: Optional[datetime] = None,
    ) -> datetime:
        if not since:
            since = self.init_balance_at
        latest_trade = self.get_latest_trade(asset_type)
        if latest_trade is not None:
            if latest_trade.transacted_at > since:
                since = latest_trade.transacted_at
        return since

    def acquire_t_account(
        self, currency: str,
        asset_type: AssetType,
        **kwargs,
    ) -> "TAccount":
        if not isinstance(self._t_accounts, dict):
            self._t_accounts = {}
        key = f'{asset_type}_{currency}'
        t_account = self._t_accounts.get(key)
        if t_account:
            return t_account
        t_account = TAccount(
            name=f'{self.name} ({currency})',
            type=TAccountType.asset,
            currency=currency,
            asset_type=asset_type,
            account_id=self.id,
            **kwargs,
        ).acquire(self.session)
        self._t_accounts[key] = t_account
        return t_account

    def acquire_position(
        self, code: str,
        asset_type: AssetType,
        currency: str,
        side: PositionSide,
        **kwargs,
    ) -> "Position":
        if not isinstance(self._positions, dict):
            self._positions: Dict[str, "Position"] = {}
        key = f'{code}_{asset_type}_{currency}_{side}'
        position = self._positions.get(key)
        if position:
            if position.closed_at == None:
                return position
        position = Position(
            code=code,
            asset_type=asset_type,
            account_id=self.id,
            currency=currency,
            side=side,
            **kwargs,
        ).acquire(self.session)
        self._positions[key] = position
        return position

    def exchange(
        self, from_currency: str,
        to_currency: str,
        from_amount: float,
        to_amount: float,
        asset_type: AssetType,
        transacted_at: Optional[datetime] = None,
        trade: Optional["Trade"] = None,
    ) -> "CurrencyExchange":
        from_account = self.acquire_t_account(from_currency, asset_type)
        to_account = self.acquire_t_account(to_currency, asset_type)

        return CurrencyExchange(
            transacted_at=transacted_at,
            credit_account=from_account,
            debit_account=to_account,
            credit_amount=from_amount,
            debit_amount=to_amount,
            trade=trade,
        ).add(self.session)
