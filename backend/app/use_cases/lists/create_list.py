from datetime import UTC, datetime

from app.domain.entities.shopping_list import ShoppingList
from app.domain.value_objects.member_role import MemberRole
from app.ports.repositories.list_repository import ListRepository
from app.ports.repositories.member_repository import MemberRepository


class CreateListUC:
    def __init__(self, list_repo: ListRepository, member_repo: MemberRepository) -> None:
        self._list_repo = list_repo
        self._member_repo = member_repo

    async def execute(self, store_name: str, address: str, owner_id: str) -> ShoppingList:
        today = datetime.now(UTC).strftime("%d/%m/%Y")
        title = f"{store_name} {today}"

        shopping_list = await self._list_repo.create(
            store_name=store_name,
            address=address,
            title=title,
            owner_id=owner_id,
        )
        await self._member_repo.add(
            list_id=shopping_list.id,
            user_id=owner_id,
            role=MemberRole.OWNER,
        )
        return shopping_list
