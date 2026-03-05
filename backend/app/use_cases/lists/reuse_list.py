from app.domain.entities.shopping_list import ShoppingList
from app.domain.exceptions.forbidden import ForbiddenError
from app.domain.exceptions.not_found import NotFoundError
from app.domain.value_objects.list_status import ListStatus
from app.domain.value_objects.member_role import MemberRole
from app.ports.repositories.item_repository import ItemRepository
from app.ports.repositories.list_repository import ListRepository
from app.ports.repositories.member_repository import MemberRepository
from app.use_cases.lists.create_list import CreateListUC


class ReuseListUC:
    def __init__(
        self,
        list_repo: ListRepository,
        item_repo: ItemRepository,
        member_repo: MemberRepository,
    ) -> None:
        self._list_repo = list_repo
        self._item_repo = item_repo
        self._member_repo = member_repo

    async def execute(self, source_list_id: str, owner_id: str) -> ShoppingList:
        source = await self._list_repo.find_by_id(source_list_id)
        if not source:
            raise NotFoundError("ShoppingList", source_list_id)
        if source.owner_id != owner_id:
            raise ForbiddenError("Only the list owner can reuse it")
        if source.status != ListStatus.ARCHIVED:
            raise ForbiddenError("Only archived lists can be reused")

        # Create new list using same store info
        create_uc = CreateListUC(self._list_repo, self._member_repo)
        new_list = await create_uc.execute(
            store_name=source.store_name,
            address=source.address,
            owner_id=owner_id,
        )

        # Copy items with last_price reference
        source_items = await self._item_repo.find_by_list(source_list_id)
        for item in source_items:
            await self._item_repo.create(
                list_id=new_list.id,
                name=item.name,
                quantity=item.quantity,
                created_by=owner_id,
                last_price=item.price,  # carry previous price as reference
            )

        return new_list
