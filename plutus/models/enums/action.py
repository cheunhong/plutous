from enum import Enum


class Action(int, Enum):
    buy: int = 1
    sell: int = 2
    open_long: int = 3
    open_short: int = 4
    close_long: int = 5
    close_short: int = 6
