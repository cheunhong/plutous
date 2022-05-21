from sqlmodel import (
    Field, Relationship, Column, ForeignKey,
    DECIMAL, JSON, Enum, String, Text, text
)
from sqlalchemy.dialects.mysql import INTEGER, TIMESTAMP
from typing import TYPE_CHECKING, Optional, Dict, Any
from datetime import datetime
from .enums import AssetType, Action, OrderType
from .base import BaseModel
from .types import Amount

if TYPE_CHECKING:
    from .account import Account


class Order(BaseModel, table=True):
    code: str = Field(sa_column=Column(String(10), nullable=False))
    type: OrderType = Field(sa_column=Column(Enum(OrderType), nullable=False))
    asset_type: AssetType = Field(
        sa_column=Column(Enum(AssetType), nullable=False)
    )
    currency: str = Field(sa_column=Column(String(10), nullable=False))
    action: Action = Field(sa_column=Column(Enum(Action), nullable=False))
    size: Amount = Field(sa_column=Column(DECIMAL(20, 8), nullable=False))
    price: Amount = Field(sa_column=Column(DECIMAL(20, 8), nullable=False))
    status: str = Field(sa_column=Column(String(10), nullable=False))
    account_id: int = Field(
        sa_column=Column(
            ForeignKey('accounts.id'),
            index=True, nullable=False,
        )
    )
    position_id: int = Field(
        sa_column=Column(ForeignKey('positions.id'), index=True)
    )
    reference_id: int = Field(sa_column=Column(INTEGER(10)))

    account: Optional["Account"] = Relationship()
