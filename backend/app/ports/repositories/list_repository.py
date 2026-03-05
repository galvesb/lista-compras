from abc import ABC, abstractmethod

from app.domain.entities.shopping_list import ShoppingList
from app.domain.value_objects.list_status import ListStatus


class ListRepository(ABC):
    @abstractmethod
    async def create(self, store_name: str, address: str, title: str, owner_id: str) -> ShoppingList: ...

    @abstractmethod
    async def find_by_id(self, list_id: str) -> ShoppingList | None: ...

    @abstractmethod
    async def find_by_user(self, user_id: str, status: ListStatus | None = None) -> list[ShoppingList]: ...

    @abstractmethod
    async def update_status_archived(
        self, list_id: str, total_cost: float
    ) -> ShoppingList | None: ...
