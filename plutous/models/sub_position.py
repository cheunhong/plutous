from sqlmodel import (
    Field, Relationship, Column, ForeignKey, DECIMAL, text
)
from sqlalchemy.dialects.mysql import TIMESTAMP
from typing import TYPE_CHECKING, Optional, List
from datetime import datetime

from .sub_position_link import SubPositionLink
from .base import BaseModel
from .types import Amount

if TYPE_CHECKING:
    from .position_flow import PositionFlow
    from .position import Position


class SubPosition(BaseModel, table=True):
    __refresh_cols__ = [
        'id',
        'size',
        'entry_price',
        'cost',
        'unrealized_pnl',
        'realized_pnl',
    ]

    position_id: int = Field(
        sa_column=Column(
            ForeignKey('positions.id'),
            nullable=False, index=True,
        )
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
    opened_at: Optional[datetime] = Field(sa_column=Column(TIMESTAMP(fsp=6)))
    closed_at: Optional[datetime] = Field(sa_column=Column(TIMESTAMP(fsp=6)))

    position: "Position" = Relationship(back_populates='sub_positions')
    position_flows: List["PositionFlow"] = Relationship(
        back_populates='sub_positions', link_model=SubPositionLink
    )
