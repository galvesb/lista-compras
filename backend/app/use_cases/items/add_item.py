from app.domain.entities.list_item import ListItem
from app.domain.exceptions.forbidden import ForbiddenError
from app.domain.exceptions.not_found import NotFoundError
from app.ports.repositories.item_repository import ItemRepository
from app.ports.repositories.list_repository import ListRepository
from app.ports.repositories.member_repository import MemberRepository


class AddItemUC:
    def __init__(
        self,
        item_repo: ItemRepository,
        list_repo: ListRepository,
        member_repo: MemberRepository,
    ) -> None:
        self._item_repo = item_repo
        self._list_repo = list_repo
        self._member_repo = member_repo

    async def execute(
        self, list_id: str, name: str, quantity: str, current_user_id: str
    ) -> ListItem:
        shopping_list = await self._list_repo.find_by_id(list_id)
        if not shopping_list:
            raise NotFoundError("ShoppingList", list_id)

        membership = await self._member_repo.find(list_id, current_user_id)
        if not membership:
            raise ForbiddenError("User is not a member of this list")

        return await self._item_repo.create(
            list_id=list_id,
            name=name,
            quantity=quantity,
            created_by=current_user_id,
        )
