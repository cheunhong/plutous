from enum import Enum


class RoleType(int, Enum):
    admin: int = 1
    editor: int = 2
    member: int = 3
