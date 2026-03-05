from app.domain.entities.shopping_list import ShoppingList
from app.domain.exceptions.forbidden import ForbiddenError
from app.domain.exceptions.not_found import NotFoundError
from app.ports.repositories.item_repository import ItemRepository
from app.ports.repositories.list_repository import ListRepository


class ArchiveListUC:
    def __init__(self, list_repo: ListRepository, item_repo: ItemRepository) -> None:
        self._list_repo = list_repo
        self._item_repo = item_repo

    async def execute(self, list_id: str, owner_id: str) -> ShoppingList:
        shopping_list = await self._list_repo.find_by_id(list_id)
        if not shopping_list:
            raise NotFoundError("ShoppingList", list_id)
        if shopping_list.owner_id != owner_id:
            raise ForbiddenError("Only the list owner can archive it")

        total = await self._item_repo.get_checked_total(list_id)
        archived = await self._list_repo.update_status_archived(list_id, total)
        if not archived:
            raise NotFoundError("ShoppingList", list_id)
        return archived
