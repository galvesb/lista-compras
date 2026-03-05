from enum import StrEnum


class ItemStatus(StrEnum):
    PENDING = "pending"
    CHECKED = "checked"
    UNAVAILABLE = "unavailable"
