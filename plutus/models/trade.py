from sqlmodel import (
    Field, Relationship, Session, Column, ForeignKey,
    Index, DECIMAL, JSON, Enum, String, text,
)
from sqlalchemy.dialects.mysql import TIMESTAMP
from sqlalchemy.orm import relationship
from typing import TYPE_CHECKING, Optional, List, Dict, Any
from datetime import datetime
from .enums import Action, AssetType, PositionSide
from .transaction import transactable_join
from .realized_pnl import RealizedPnl
from .commission import Commission
from .base import BaseModel
from ..config import config
from .types import Amount


if TYPE_CHECKING:
    from typing_extensions import Self
    from .currency_exchange import CurrencyExchange
    from .position_flow import PositionFlow
    from .realized_pnl import RealizedPnl
    from .transaction import Transaction
    from .account import Account


class Trade(BaseModel, table=True):
    __table_args__ = (
        Index(
            'ix_trades_account_id_reference_id',
            'account_id', 'reference_id', unique=True
        ),
    )

    code: str = Field(sa_column=Column(String(10), nullable=False))
    asset_type: AssetType = Field(
        sa_column=Column(Enum(AssetType), nullable=False)
    )
    currency: str = Field(sa_column=Column(String(10), nullable=False))
    action: Action = Field(sa_column=Column(Enum(Action), nullable=False))
    size: Amount = Field(sa_column=Column(DECIMAL(20, 8), nullable=False))
    price: Amount = Field(sa_column=Column(DECIMAL(20, 8), nullable=False))
    margin: Optional[Amount] = Field(
        sa_column=Column(
            DECIMAL(20, 8), nullable=False,
            server_default=text("'0.00000000'"),
        )
    )
    margin_currency: Optional[str] = Field(sa_column=Column(String(10)))
    comms: Optional[Amount] = Field(
        sa_column=Column(
            DECIMAL(20, 8), nullable=False,
            server_default=text("'0.00000000'"),
        )
    )
    comms_currency: Optional[str] = Field(sa_column=Column(String(10)))
    pnl: Optional[Amount] = Field(
        sa_column=Column(
            DECIMAL(20, 8), nullable=False,
            server_default=text("'0.00000000'"),
        )
    )
    pnl_currency: Optional[str] = Field(sa_column=Column(String(10)))
    account_id: int = Field(
        sa_column=Column(
            ForeignKey('accounts.id'), nullable=False, index=True
        )
    )
    transacted_at: datetime = Field(
        sa_column=Column(
            TIMESTAMP(fsp=6), nullable=False,
            server_default=text("CURRENT_TIMESTAMP(6)"),
        )
    )
    reference_id: str = Field(sa_column=Column(String(20)))
    details: Optional[Dict[str, Any]] = Field(
        sa_column=Column(JSON(none_as_null=True))
    )

    account: "Account" = Relationship(back_populates='trades')
    commissions: List["Commission"] = Relationship(back_populates='trade')
    realized_pnls: List["RealizedPnl"] = Relationship(back_populates='trade')
    position_flows: List["PositionFlow"] = Relationship(back_populates='trade')
    currency_exchanges: List["CurrencyExchange"] = (
        Relationship(back_populates='trade')
    )
    transactions: List["Transaction"] = Relationship(
        sa_relationship=relationship(
            'Transaction', viewonly=True,
            uselist=True, foreign_keys='Trade.id',
            primaryjoin=transactable_join('Trade'),
        )
    )

    @property
    def base_asset_type(self) -> AssetType:
        if self.asset_type in (
            AssetType.crypto,
            AssetType.crypto_perp,
            AssetType.crypto_inverse_perp,
        ):
            return AssetType.crypto
        return AssetType.cash

    @property
    def base_currency(self) -> str:
        return config['position']['base_currency'].get(
            self.asset_type, self.currency
        )

    @property
    def cash_equivalents(self) -> List[str]:
        return config['position']['cash_equivalents'].get(
            self.asset_type, [self.currency]
        )

    def add(
        self, session: Session,
        refresh: Optional[bool] = True,
    ) -> "Self":
        return self._add(
            session=session,
            refresh=refresh,
            after_insert=[
                'record_pnl',
                'record_exchange',
                'record_commission',
                'record_position_flow',
            ],
        )

    def record_exchange(self):
        allowed = [AssetType.crypto]
        if self.asset_type not in allowed:
            return

        amount = round(self.size * self.price, 8)

        if self.action == Action.buy:
            to_currency, from_currency = self.code, self.currency
            from_amount, to_amount = amount, self.size
        else:
            to_currency, from_currency = self.currency, self.code
            from_amount, to_amount = self.size, amount

        self.account.exchange(
            from_currency, to_currency,
            from_amount=from_amount,
            to_amount=to_amount,
            asset_type=self.asset_type,
            transacted_at=self.transacted_at,
            trade=self,
        )

    def record_commission(self):
        if self.comms:
            t_account = self.account.acquire_t_account(
                self.comms_currency, self.base_asset_type
            )
            Commission(
                trade_id=self.id,
                t_account=t_account,
                amount=self.comms,
                charged_at=self.transacted_at,
            ).add(self.session)

    def record_pnl(self):
        if self.pnl:
            t_account = self.account.acquire_t_account(
                self.pnl_currency, self.base_asset_type
            )
            RealizedPnl(
                trade_id=self.id,
                t_account=t_account,
                amount=self.pnl,
                granted_at=self.transacted_at,
            ).add(self.session)

    def record_position_flow(self):
        allowed = [
            AssetType.crypto_perp,
            AssetType.crypto_inverse_perp,
        ]
        if self.asset_type not in allowed:
            return

        side = (
            PositionSide.long
            if self.action in (Action.open_long, Action.close_long)
            else PositionSide.short
        )
        position = self.account.acquire_position(
            self.code, self.asset_type,
            self.currency, side,
            margin_currency=self.margin_currency,
        )
        size = (
            -1 * self.size
            if self.action in (Action.close_long, Action.open_short)
            else self.size
        )
        params = {
            'price': self.price,
            'size': size,
            'transacted_at': self.transacted_at,
            'trade_id': self.id,
        }

        if self.action in (Action.open_long, Action.open_short):
            position.increase(**params)
        else:
            position.decrease(**params)
