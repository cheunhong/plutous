from .enums import (
    AssetType, PositionFlowType, PositionSide
)
from .position_flow import PositionFlow
from .sub_position import SubPosition
from .base import BaseModel
from .types import Amount

from sqlmodel import (
    Field, Relationship, Column, ForeignKey, Index,
    DECIMAL, JSON, Enum, Session, String, text,
)
from sqlalchemy.orm import relationship, AppenderQuery
from sqlalchemy.dialects.mysql import TIMESTAMP
from typing import (
    TYPE_CHECKING, Optional, List, Dict, Any,
)
from datetime import datetime

if TYPE_CHECKING:
    from typing_extensions import Self
    from .funding_fee import FundingFee
    from .t_account import TAccount
    from .account import Account
    from .trade import Trade


class Position(BaseModel, table=True):
    __table_args__ = (
        Index(
            'ix_positions_asset_type_currency_code',
            'asset_type', 'currency', 'code',
        ),
    )
    __refresh_cols__ = [
        'id',
        'size',
        'entry_price',
        'cost',
        'margin',
        'unrealized_pnl',
        'realized_pnl',
    ]

    code: str = Field(sa_column=Column(String(10), nullable=False))
    asset_type: AssetType = Field(
        sa_column=Column(Enum(AssetType), nullable=False)
    )
    currency: str = Field(sa_column=Column(String(10), nullable=False))
    side: PositionSide = Field(
        sa_column=Column(Enum(PositionSide), nullable=False)
    )
    size: Optional[Amount] = Field(
        sa_column=Column(
            DECIMAL(20, 8), nullable=False,
            server_default=text("'0.00000000'"),
        )
    )
    entry_price: Optional[Amount] = Field(
        sa_column=Column(
            DECIMAL(20, 8), nullable=False,
            server_default=text("'0.00000000'")
        )
    )
    cost: Optional[Amount] = Field(
        sa_column=Column(
            DECIMAL(20, 12), nullable=False,
            server_default=text("'0.00000000'")
        )
    )
    price: Optional[Amount] = Field(sa_column=Column(DECIMAL(20, 8)))
    margin: Optional[Amount] = Field(
        sa_column=Column(
            DECIMAL(20, 8), nullable=False,
            server_default=text("'0.00000000'")
        )
    )
    margin_currency: Optional[str] = Field(sa_column=Column(String(10)))
    liquidation_price: Optional[Amount] = Field(
        sa_column=Column(DECIMAL(20, 8))
    )
    unrealized_pnl: Optional[Amount] = Field(
        sa_column=Column(
            DECIMAL(20, 8), nullable=False,
            server_default=text("'0.00000000'")
        )
    )
    realized_pnl: Optional[Amount] = Field(
        sa_column=Column(
            DECIMAL(20, 8), nullable=False,
            server_default=text("'0.00000000'")
        )
    )
    details: Optional[Dict[str, Any]] = Field(
        sa_column=Column(JSON(none_as_null=True))
    )
    account_id: int = Field(
        sa_column=Column(
            ForeignKey('accounts.id'),
            nullable=False, index=True,
        )
    )
    t_account_id: Optional[int] = Field(
        sa_column=Column(ForeignKey('t_accounts.id'), index=True)
    )
    opened_at: Optional[datetime] = Field(sa_column=Column(TIMESTAMP(fsp=6)))
    closed_at: Optional[datetime] = Field(sa_column=Column(TIMESTAMP(fsp=6)))

    account: "Account" = Relationship(back_populates='positions')
    t_account: Optional["TAccount"] = Relationship(back_populates='positions')
    funding_fees: List["FundingFee"] = Relationship(back_populates='position')
    sub_positions: List["SubPosition"] = Relationship(
        sa_relationship=relationship(
            'SubPosition', back_populates='position',
            order_by='desc(SubPosition.opened_at)',
        )
    )
    position_flows: AppenderQuery = Relationship(
        sa_relationship=relationship(
            'PositionFlow', back_populates='position', lazy='dynamic', 
            order_by='desc(PositionFlow.transacted_at)',
        )
    )

    @property
    def trades(self) -> List["Trade"]:
        from .trade import Trade

        return (
            self.session.query(Trade)
            .join(PositionFlow)
            .filter(PositionFlow.position_id == self.id)
        ).all()

    def get(self, session: Session, *args, **kwargs) -> "Self":
        return super().get(session, closed_at=None, *args, **kwargs)

    def add(
        self, session: Session,
        refresh: Optional[bool] = True,
    ) -> "Self":
        return self._add(
            session, refresh,
            after_insert=['attach_sub_position'],
        )

    def attach_sub_position(self):
        if self.asset_type in (
            AssetType.crypto_perp,
            AssetType.crypto_inverse_perp,
        ):
            SubPosition(position=self).add(self.session)

    def increase(
        self, price: float,
        size: float,
        margin: Optional[float] = 0.0,
        transacted_at: Optional[datetime] = None,
        transaction_id: Optional[int] = None,
        trade_id: Optional[int] = None,
    ) -> "PositionFlow":
        return PositionFlow(
            position=self,
            type=PositionFlowType.increase,
            size=size,
            price=price,
            margin=margin,
            transacted_at=transacted_at,
            transaction_id=transaction_id,
            trade_id=trade_id,
        ).add(self.session)

    def decrease(
        self, price: float,
        size: float,
        margin: Optional[float] = 0.0,
        transacted_at: Optional[datetime] = None,
        transaction_id: Optional[int] = None,
        trade_id: Optional[int] = None,
    ) -> "PositionFlow":
        pnl = round((self.entry_price - price) * size, 8)
        return PositionFlow(
            position=self,
            type=PositionFlowType.decrease,
            size=size,
            price=price,
            pnl=pnl,
            margin=margin,
            transacted_at=transacted_at,
            transaction_id=transaction_id,
            trade_id=trade_id,
        ).add(self.session)

    def transfer(
        self, size: float,
        target_size: float,
        position: "Position",
        cost: Optional[float] = None,
        transacted_at: Optional[datetime] = None,
        transaction_id: Optional[int] = None,
        trade_id: Optional[int] = None,
    ) -> List["PositionFlow"]:
        if position.currency != self.currency:
            raise ValueError("""
                This operation only allowed to be done by 2 positions with the same currency
            """)

        if cost is None:
            cost = self.entry_price * self.size
        entry_price = cost / target_size
        kwargs = {
            'transacted_at': transacted_at,
            'transaction_id': transaction_id,
            'trade_id': trade_id,
        }
        return [
            self.decrease(price=self.price, size=(-1 * size), **kwargs),
            position.increase(price=entry_price, size=target_size, **kwargs)
        ]
