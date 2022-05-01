from enum import Enum


class TAccountType(int, Enum):
    asset: int = 1
    liability: int = 2
    income: int = 3
    expense: int = 4
    equity: int = 5
