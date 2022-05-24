from sqlmodel import (
    Field, Relationship, Session, ForeignKey,
    Column, Index, DECIMAL, JSON, String, Enum
)
from sqlalchemy.dialects.mysql import TIMESTAMP
from typing import TYPE_CHECKING, Optional, Dict, Any
from datetime import datetime

from .transaction import Transaction, Transactable
from .enums import AssetType, PositionSide
from .position import Position
from .types import Amount

if TYPE_CHECKING:
    from typing_extensions import Self
    from .t_account import TAccount
    from .position import Position
    from .account import Account


class FundingFee(Transactable, table=True):
    __table_args__ = (
        Index(
            'ix_funding_fees_t_account_id_reference_id',
            't_account_id', 'reference_id', unique=True
        ),
    )

    code: str = Field(sa_column=Column(String(10), nullable=False))
    currency: str = Field(sa_column=Column(String(10), nullable=False))
    asset_type: AssetType = Field(
        sa_column=Column(Enum(AssetType), nullable=False)
    )
    funding_rate: Amount = Field(
        sa_column=Column(DECIMAL(20, 8), nullable=False)
    )
    amount: Amount = Field(sa_column=Column(DECIMAL(20, 8), nullable=False))
    charged_at: datetime = Field(
        sa_column=Column(TIMESTAMP(fsp=6), nullable=False)
    )
    reference_id: str = Field(sa_column=Column(String(20), nullable=False))
    details: Optional[Dict[str, Any]] = Field(
        sa_column=Column(JSON(none_as_null=True))
    )
    account_id: int = Field(
        sa_column=Column(
            ForeignKey('accounts.id'),
            nullable=False, index=True
        )
    )
    position_id: Optional[int] = Field(
        sa_column=Column(
            ForeignKey('positions.id'),
            nullable=False, index=True,
        )
    )
    t_account_id: Optional[int] = Field(
        sa_column=Column(
            ForeignKey('t_accounts.id'),
            nullable=False, index=True
        )
    )

    account: "Account" = Relationship(back_populates='funding_fees')
    position: Optional["Position"] = Relationship(
        back_populates='funding_fees'
    )
    t_account: Optional["TAccount"] = Relationship(
        back_populates='funding_fees'
    )

    def add(
        self, session: Session,
        refresh: Optional[bool] = True,
    ) -> "Self":
        return self._add(
            session=session,
            refresh=refresh,
            before_insert=[
                'chech_asset_type',
                'attach_position',
                'attach_t_account'
            ],
        )

    def chech_asset_type(self):
        allowed = [
            AssetType.crypto_perp,
            AssetType.crypto_inverse_perp,
        ]
        if self.asset_type not in allowed:
            raise ValueError(f'Only asset_type {allowed} is allowed')

    def attach_position(self):
        side = (
            PositionSide.long
            if (self.funding_rate * self.amount) > 0
            else PositionSide.short
        )

        if not self.position:
            code, currency = self.code.split('/')
            self.position = self.account.positions.filter_by(
                code=code, currency=currency, side=side,
                asset_type=self.asset_type,
            ).filter(
                (Position.opened_at < self.charged_at) & (
                    (Position.closed_at > self.charged_at) |
                    (Position.closed_at == None)
                )
            ).one()

    def attach_t_account(self):
        if not self.t_account:
            self.t_account = self.account.acquire_t_account(
                self.currency, AssetType.crypto
            )

    def record_transactions(self):
        transactable_account = self.get_transactable_account()
        debit_account, credit_account = (
            (transactable_account, self.t_account)
            if self.amount >= 0.0 else
            (self.t_account, transactable_account)
        )
        Transaction(
            debit_account=debit_account,
            credit_account=credit_account,
            amount=abs(self.amount),
            transacted_at=self.charged_at,
            transactable_id=self.id,
            transactable_type=self.transactable_type,
        ).add(self.session)

    def update_transactions(self):
        transactable_account = self.get_transactable_account()
        debit_account, credit_account = (
            (transactable_account, self.t_account)
            if self.amount >= 0.0 else
            (self.t_account, transactable_account)
        )
        transaction = self.transactions[0]
        transaction.debit_account = debit_account
        transaction.credit_account = credit_account
        transaction.amount = self.amount
        transaction.transacted_at = self.charged_at
        transaction.add(self.session)
