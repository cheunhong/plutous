from sqlmodel import (
    Field, Relationship, Column, ForeignKey,
    DECIMAL, String, Enum, text
)
from sqlalchemy.orm import relationship, AppenderQuery
from typing import TYPE_CHECKING, Optional, Dict
from pydantic import PrivateAttr
from datetime import datetime

from plutous.config import config
from .enums import TAccountType, AssetType, PositionSide
from .position import Position
from .base import BaseModel
from .types import Amount

if TYPE_CHECKING:
    from .transaction import Transaction
    from .account import Account
    from .group import Group
    from .user import User


class TAccount(BaseModel, table=True):
    __refresh_cols__ = ['id', 'balance']

    name: str = Field(sa_column=Column(String(50), unique=True))
    type: TAccountType = Field(
        sa_column=Column(
            Enum(TAccountType), nullable=False, index=True,
        )
    )
    asset_type: Optional[AssetType] = Field(
        sa_column=Column(Enum(AssetType), index=True)
    )
    currency: str = Field(
        sa_column=Column(String(5), nullable=False, index=True)
    )
    group_id: Optional[int] = Field(
        sa_column=Column(ForeignKey('groups.id'), index=True)
    )
    account_id: Optional[int] = Field(
        sa_column=Column(ForeignKey('accounts.id'), index=True)
    )
    balance: Optional[Amount] = Field(
        sa_column=Column(
            DECIMAL(20, 8), nullable=False,
            server_default=text("'0.00000000'"),
        ),
    )

    group: Optional["Group"] = Relationship(back_populates='t_accounts')
    account: Optional["Account"] = Relationship(back_populates='t_accounts')
    positions: AppenderQuery = Relationship(
        sa_relationship=relationship(
            'Position', back_populates='t_account',
            lazy='dynamic', order_by='desc(Position.opened_at)',
        )
    )
    adjustments: AppenderQuery = Relationship(
        sa_relationship=relationship(
            'Adjustment', back_populates='t_account',
            lazy='dynamic', order_by='desc(Adjustment.adjusted_at)',
        )
    )
    commissions: AppenderQuery = Relationship(
        sa_relationship=relationship(
            'Commission', back_populates='t_account',
            lazy='dynamic', order_by='desc(Commission.charged_at)',
        )
    )
    realized_pnls: AppenderQuery = Relationship(
        sa_relationship=relationship(
            'RealizedPnl', back_populates='t_account',
            lazy='dynamic', order_by='desc(RealizedPnl.granted_at)',
        )
    )
    funding_fees: AppenderQuery = Relationship(
        sa_relationship=relationship(
            'FundingFee', back_populates='t_account',
            lazy='dynamic', order_by='desc(FundingFee.charged_at)',
        )
    )

    _positions = PrivateAttr(default={})

    @property
    def user_id(self) -> Optional[int]:
        if self.account:
            return self.account.user_id

    @property
    def user(self) -> Optional["User"]:
        if self.account:
            return self.account.user

    @property
    def base_currency(self) -> str:
        if self.type == TAccountType.asset:
            return config['position']['base_currency'].get(
                self.asset_type, self.currency
            )

    @property
    def active_positions(self) -> AppenderQuery:
        return self.positions.filter_by(closed_at=None)

    @property
    def is_cash(self) -> bool:
        if self.asset_type == AssetType.cash:
            return True
        elif self.asset_type == AssetType.crypto:
            if self.currency in (
                config['position']['cash_equivalents'][self.asset_type]
            ):
                return True

    @property
    def is_investment(self) -> bool:
        if self.account_id:
            return self.account.is_investment

    def open_balance(
        self, amount: float,
        transacted_at: Optional[datetime] = None,
    ) -> "Transaction":
        from .transaction import Transaction
        from .group import Group

        if self.type not in [TAccountType.asset, TAccountType.liability]:
            raise ValueError(
                'Only type Asset and Liability allowed for this operation'
            )
        group = Group(name='capital').get(self.session)
        capital = group.acquire_t_account(currency=self.currency)
        return Transaction(
            amount=amount,
            credit_account=capital,
            debit_account=self,
            description=f'Opening Balance {self.name}',
            transacted_at=transacted_at,
        ).add(self.session)

    def acquire_position(
        self, code: Optional[str] = None,
    ) -> "Position":
        if not code:
            code = self.currency
        if not isinstance(self._positions, dict):
            self._positions: Dict[str, "Position"] = {}
        position = self._positions.get(code)
        if position:
            if position.closed_at == None:
                return position
        position = Position(
            account_id=self.account_id,
            t_account_id=self.id,
            currency=self.base_currency,
            asset_type=self.asset_type,
            side=PositionSide.long,
            code=code,
        ).acquire(self.session)
        self._positions[code] = position
        return position
