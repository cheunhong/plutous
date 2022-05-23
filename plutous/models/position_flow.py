from .sub_position_link import SubPositionLink
from .enums import PositionFlowType, AssetType
from .base import BaseModel
from .types import Amount

from sqlmodel import (
    Field, Relationship, Session, Column,
    ForeignKey, DECIMAL, Enum, text,
)
from sqlalchemy.dialects.mysql import TIMESTAMP
from typing import TYPE_CHECKING, Optional, List
from datetime import datetime

import numpy as np

if TYPE_CHECKING:
    from typing_extensions import Self
    from .sub_position import SubPosition
    from .transaction import Transaction
    from .position import Position
    from .trade import Trade


class PositionFlow(BaseModel, table=True):
    position_id: int = Field(
        sa_column=Column(
            ForeignKey('positions.id'), nullable=False, index=True,
        )
    )
    type: PositionFlowType = Field(
        sa_column=Column(
            Enum(PositionFlowType),
            nullable=False))
    size: Amount = Field(sa_column=Column(DECIMAL(20, 8), nullable=False))
    price: Amount = Field(sa_column=Column(DECIMAL(20, 8), nullable=False))
    margin: Optional[Amount] = Field(
        sa_column=Column(
            DECIMAL(20, 8), nullable=False,
            server_default=text("'0.00000000'"),
        )
    )
    pnl: Optional[Amount] = Field(
        sa_column=Column(
            DECIMAL(20, 8), nullable=False,
            server_default=text("'0.00000000'")
        )
    )
    transacted_at: datetime = Field(
        sa_column=Column(
            TIMESTAMP(fsp=6), nullable=False,
            server_default=text("CURRENT_TIMESTAMP(6)"),
        )
    )
    transaction_id: Optional[int] = Field(
        sa_column=Column(
            ForeignKey('transactions.id'), index=True,
        )
    )
    trade_id: Optional[int] = Field(
        sa_column=Column(ForeignKey('trades.id'), index=True)
    )

    position: "Position" = Relationship(back_populates='position_flows')
    sub_positions: List["SubPosition"] = Relationship(
        back_populates='position_flows', link_model=SubPositionLink
    )
    trade: Optional["Trade"] = Relationship(back_populates='position_flows')
    transaction: Optional["Transaction"] = Relationship(
        back_populates='position_flows'
    )

    def add(
        self, session: Session,
        refresh: Optional[bool] = True,
    ) -> "Self":
        return self._add(
            session=session,
            refresh=refresh,
            after_insert=[
                'record_position',
                'record_sub_position',
            ],
        )

    def delete(self):
        return self._delete(
            before_insert=['check_closed'],
            on_delete=['revert_position'],
        )

    def check_closed(self):
        if self.position.closed_at:
            raise RuntimeError(f"""
                position(id: {self.position.id}) already closed,
                position_flow(id: {self.id}) failed to be updated.
            """)

    def record_position(self):
        position = self.position
        position.price = self.price
        position.size += self.size
        position.cost += self.size * self.price + self.pnl
        position.realized_pnl += self.pnl
        if position.size != 0:
            position.entry_price = position.cost / position.size
        if not position.opened_at:
            position.opened_at = self.transacted_at
        if position.size == 0:
            position.closed_at = self.transacted_at
            position.unrealized_pnl = 0
        position.add(self.session, refresh=False)

    def revert_position(self):
        position = self.position
        position.size -= self.size
        position.cost -= self.size * self.price + self.pnl
        position.entry_price = position.cost / position.size
        position.realized_pnl -= self.pnl
        position.opened_at = None if position.opened_at == self.transacted_at else position.opened_at
        position.add(self.session)

    def record_sub_position(self):
        if self.position.asset_type not in (
            AssetType.crypto_perp,
            AssetType.crypto_inverse_perp,
        ):
            return
        self._increase_sub_position()
        self._decrease_sub_positions()

    def _increase_sub_position(self):
        if self.type != PositionFlowType.increase:
            return

        sub_position = self.position.sub_positions[0]
        sub_position.price = self.price
        sub_position.size += self.size
        sub_position.cost += self.size * self.price + self.pnl
        if sub_position.size != 0:
            sub_position.entry_price = sub_position.cost / sub_position.size
        if not sub_position.opened_at:
            sub_position.opened_at = self.transacted_at
        sub_position.position_flows.append(self)
        sub_position.add(self.session, refresh=False)

    def _decrease_sub_positions(self):
        if self.type != PositionFlowType.decrease:
            return

        i = 0
        total_size = self.size
        total_pnl = self.pnl
        while abs(total_size) > 0:
            sub_position = self.position.sub_positions[i]
            sizes = [-1 * sub_position.size, total_size]
            size = sizes[np.argmin(np.abs(sizes))]
            pnl = round((size / total_size) * total_pnl, 8)

            sub_position.price = self.price
            sub_position.size += size
            sub_position.cost += size * self.price + pnl
            sub_position.realized_pnl += pnl
            if sub_position.size != 0:
                sub_position.entry_price = sub_position.cost / sub_position.size
            if not sub_position.opened_at:
                sub_position.opened_at = self.transacted_at
            if sub_position.size == 0:
                sub_position.closed_at = self.transacted_at
                sub_position.unrealized_pnl = 0
            sub_position.position_flows.append(self)
            sub_position.add(self.session, refresh=False)

            total_size -= size
            total_pnl -= pnl
            i += 1
