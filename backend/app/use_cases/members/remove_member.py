from app.domain.exceptions.forbidden import ForbiddenError
from app.domain.exceptions.not_found import NotFoundError
from app.domain.value_objects.member_role import MemberRole
from app.ports.repositories.item_repository import ItemRepository
from app.ports.repositories.member_repository import MemberRepository


class RemoveMemberUC:
    def __init__(self, member_repo: MemberRepository, item_repo: ItemRepository) -> None:
        self._member_repo = member_repo
        self._item_repo = item_repo

    async def execute(
        self, list_id: str, target_user_id: str, current_user_id: str
    ) -> None:
        current_membership = await self._member_repo.find(list_id, current_user_id)
        if not current_membership:
            raise ForbiddenError("User is not a member of this list")

        is_owner = current_membership.role == MemberRole.OWNER
        is_self_removal = target_user_id == current_user_id

        if not is_owner and not is_self_removal:
            raise ForbiddenError("Only the owner can remove other members")

        target = await self._member_repo.find(list_id, target_user_id)
        if not target:
            raise NotFoundError("ListMember", target_user_id)

        if target.role == MemberRole.OWNER:
            raise ForbiddenError("Cannot remove the list owner")

        # Reassign items from removed member to owner
        owner_membership = await self._member_repo.find(list_id, current_user_id if is_owner else target_user_id)
        # Find actual owner
        all_members = await self._member_repo.find_all(list_id)
        owner = next((m for m in all_members if m.role == MemberRole.OWNER), None)
        if owner:
            await self._item_repo.reassign_items(list_id, target_user_id, owner.user_id)

        await self._member_repo.remove(list_id, target_user_id)
