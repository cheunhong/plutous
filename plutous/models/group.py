from .enums import TAccountType
from .t_account import TAccount
from .base import BaseModel

from sqlmodel import Field, Relationship, Column, String
from sqlalchemy.orm import relationship, AppenderQuery
from typing import TYPE_CHECKING, Optional


DEFAULT_TYPES = {
    'currency_exchange': TAccountType.income,
    'realized_pnl': TAccountType.income,
    'funding_fee': TAccountType.expense,
    'commission': TAccountType.expense,
    'deposit': TAccountType.income,
    'capital': TAccountType.equity,
    'adjustment': TAccountType.expense,
}


class Group(BaseModel, table=True):
    name: str = Field(sa_column=Column(String(20), unique=True))

    t_accounts: AppenderQuery = Relationship(
        sa_relationship=relationship('TAccount', lazy='dynamic')
    )

    def acquire_t_account(
        self, currency: str,
        account_type: Optional[TAccountType] = None,
    ) -> TAccount:
        if not account_type:
            if self.name not in DEFAULT_TYPES:
                raise ValueError("""
                    This group has no predefined account_types,
                    please input an account_type.
                """)
            account_type = DEFAULT_TYPES[self.name]

        return TAccount(
            name=f"{self.name.replace('_', ' ').title()} ({currency})",
            type=account_type,
            currency=currency,
            group_id=self.id,
        ).acquire(self.session)
