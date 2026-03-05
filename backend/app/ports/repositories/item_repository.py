from abc import ABC, abstractmethod

from app.domain.entities.list_item import ListItem
from app.domain.value_objects.item_status import ItemStatus


class ItemRepository(ABC):
    @abstractmethod
    async def create(self, list_id: str, name: str, quantity: str, created_by: str, last_price: float | None = None) -> ListItem: ...

    @abstractmethod
    async def find_by_id(self, item_id: str) -> ListItem | None: ...

    @abstractmethod
    async def find_by_list(self, list_id: str, assigned_to: str | None = None) -> list[ListItem]: ...

    @abstractmethod
    async def update_with_version(
        self,
        item_id: str,
        expected_version: int,
        status: ItemStatus | None = None,
        price: float | None = None,
        clear_price: bool = False,
        checked_by_user_id: str | None = None,
        clear_checked_by: bool = False,
    ) -> ListItem | None:
        """Returns updated item or None if version conflict."""
        ...

    @abstractmethod
    async def update_assigned_to(self, item_id: str, user_id: str | None) -> ListItem | None: ...

    @abstractmethod
    async def reassign_items(self, list_id: str, from_user_id: str, to_user_id: str) -> int: ...

    @abstractmethod
    async def delete(self, item_id: str) -> bool: ...

    @abstractmethod
    async def get_checked_total(self, list_id: str) -> float: ...
