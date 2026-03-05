from app.domain.entities.list_item import ListItem
from app.domain.exceptions.forbidden import ForbiddenError
from app.domain.exceptions.not_found import NotFoundError
from app.domain.value_objects.member_role import MemberRole
from app.ports.repositories.item_repository import ItemRepository
from app.ports.repositories.member_repository import MemberRepository


class AssignItemUC:
    def __init__(self, item_repo: ItemRepository, member_repo: MemberRepository) -> None:
        self._item_repo = item_repo
        self._member_repo = member_repo

    async def execute(
        self,
        list_id: str,
        item_id: str,
        assign_to_user_id: str | None,
        current_user_id: str,
    ) -> ListItem:
        # Only owner can assign
        membership = await self._member_repo.find(list_id, current_user_id)
        if not membership or membership.role != MemberRole.OWNER:
            raise ForbiddenError("Only the list owner can assign items")

        item = await self._item_repo.find_by_id(item_id)
        if not item or item.list_id != list_id:
            raise NotFoundError("ListItem", item_id)

        # Validate target user is a member (if assigning, not clearing)
        if assign_to_user_id:
            target_membership = await self._member_repo.find(list_id, assign_to_user_id)
            if not target_membership:
                raise NotFoundError("ListMember", assign_to_user_id)

        updated = await self._item_repo.update_assigned_to(item_id, assign_to_user_id)
        if not updated:
            raise NotFoundError("ListItem", item_id)
        return updated
