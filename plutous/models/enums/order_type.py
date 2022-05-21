from enum import Enum


class OrderType(int, Enum):
    limit: int = 1
    market: int = 2
    stop_loss: int = 3
    take_profit: int = 4
