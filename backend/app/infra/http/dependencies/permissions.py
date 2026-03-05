from fastapi import Depends, HTTPException, Path, status

from app.adapters.repositories.mongo_member_repo import MongoMemberRepository
from app.domain.entities.list_member import ListMember
from app.domain.entities.user import User
from app.domain.value_objects.member_role import MemberRole
from app.infra.db.mongodb import get_database
from app.infra.http.dependencies.auth import get_current_user


async def require_list_member(
    list_id: str = Path(...),
    current_user: User = Depends(get_current_user),
) -> ListMember:
    db = get_database()
    repo = MongoMemberRepository(db)
    membership = await repo.find(list_id, current_user.id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you are not a member of this list",
        )
    return membership


async def require_list_owner(
    list_id: str = Path(...),
    current_user: User = Depends(get_current_user),
) -> ListMember:
    db = get_database()
    repo = MongoMemberRepository(db)
    membership = await repo.find(list_id, current_user.id)
    if not membership or membership.role != MemberRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: only the list owner can perform this action",
        )
    return membership
