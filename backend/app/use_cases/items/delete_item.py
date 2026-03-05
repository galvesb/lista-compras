from app.domain.exceptions.forbidden import ForbiddenError
from app.domain.exceptions.not_found import NotFoundError
from app.ports.repositories.item_repository import ItemRepository
from app.ports.repositories.member_repository import MemberRepository


class DeleteItemUC:
    def __init__(self, item_repo: ItemRepository, member_repo: MemberRepository) -> None:
        self._item_repo = item_repo
        self._member_repo = member_repo

    async def execute(self, list_id: str, item_id: str, current_user_id: str) -> None:
        membership = await self._member_repo.find(list_id, current_user_id)
        if not membership:
            raise ForbiddenError("User is not a member of this list")

        item = await self._item_repo.find_by_id(item_id)
        if not item or item.list_id != list_id:
            raise NotFoundError("ListItem", item_id)

        await self._item_repo.delete(item_id)
