from app.domain.entities.list_member import ListMember
from app.domain.exceptions.conflict import DuplicateError
from app.domain.exceptions.forbidden import ForbiddenError
from app.domain.exceptions.not_found import NotFoundError
from app.domain.value_objects.member_role import MemberRole
from app.ports.repositories.member_repository import MemberRepository
from app.ports.repositories.user_repository import UserRepository


class InviteMemberUC:
    def __init__(self, member_repo: MemberRepository, user_repo: UserRepository) -> None:
        self._member_repo = member_repo
        self._user_repo = user_repo

    async def execute(self, list_id: str, invitee_email: str, inviter_id: str) -> ListMember:
        # Only owner can invite
        membership = await self._member_repo.find(list_id, inviter_id)
        if not membership or membership.role != MemberRole.OWNER:
            raise ForbiddenError("Only the list owner can invite members")

        # Find target user
        invitee = await self._user_repo.find_by_email(invitee_email)
        if not invitee:
            raise NotFoundError("User", invitee_email)

        # Check not already a member
        existing = await self._member_repo.find(list_id, invitee.id)
        if existing:
            raise DuplicateError(f"User '{invitee_email}' is already a member")

        return await self._member_repo.add(list_id, invitee.id, MemberRole.MEMBER)
