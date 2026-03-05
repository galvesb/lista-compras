from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.adapters.repositories.mongo_item_repo import MongoItemRepository
from app.adapters.repositories.mongo_member_repo import MongoMemberRepository
from app.adapters.repositories.mongo_user_repo import MongoUserRepository
from app.domain.entities.list_member import ListMember
from app.domain.entities.user import User
from app.domain.exceptions.conflict import DuplicateError
from app.domain.exceptions.forbidden import ForbiddenError
from app.domain.exceptions.not_found import NotFoundError
from app.infra.db.mongodb import get_database
from app.infra.http.dependencies.auth import get_current_user
from app.infra.http.dependencies.permissions import require_list_member, require_list_owner
from app.infra.http.schemas.list import InviteMemberRequest, MemberInfo
from app.infra.websocket.connection_manager import manager
from app.use_cases.members.invite_member import InviteMemberUC
from app.use_cases.members.remove_member import RemoveMemberUC

router = APIRouter(prefix="/{list_id}/members", tags=["members"])


@router.get("", response_model=list[MemberInfo])
async def get_members(
    list_id: str = Path(...),
    membership: ListMember = Depends(require_list_member),
) -> list[MemberInfo]:
    db = get_database()
    member_repo = MongoMemberRepository(db)
    user_repo = MongoUserRepository(db)

    members = await member_repo.find_all(list_id)
    result = []
    for m in members:
        u = await user_repo.find_by_id(m.user_id)
        if u:
            result.append(
                MemberInfo(
                    user_id=u.id,
                    name=u.name,
                    email=u.email,
                    avatar_url=u.avatar_url,
                    role=m.role,
                    joined_at=m.joined_at,
                )
            )
    return result


@router.post("", response_model=MemberInfo, status_code=status.HTTP_201_CREATED)
async def invite_member(
    payload: InviteMemberRequest,
    list_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    membership: ListMember = Depends(require_list_owner),
) -> MemberInfo:
    db = get_database()
    uc = InviteMemberUC(MongoMemberRepository(db), MongoUserRepository(db))
    try:
        new_member = await uc.execute(list_id, payload.email, current_user.id)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{payload.email}' not found")
    except DuplicateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    user = await MongoUserRepository(db).find_by_id(new_member.user_id)
    response = MemberInfo(
        user_id=new_member.user_id,
        name=user.name if user else "",
        email=user.email if user else payload.email,
        avatar_url=user.avatar_url if user else None,
        role=new_member.role,
        joined_at=new_member.joined_at,
    )
    await manager.broadcast(list_id, "member_joined", response.model_dump(mode="json"))
    return response


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    list_id: str = Path(...),
    user_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    membership: ListMember = Depends(require_list_member),
) -> None:
    db = get_database()
    uc = RemoveMemberUC(MongoMemberRepository(db), MongoItemRepository(db))
    try:
        await uc.execute(list_id, user_id, current_user.id)
    except (NotFoundError, ForbiddenError) as exc:
        code = status.HTTP_404_NOT_FOUND if isinstance(exc, NotFoundError) else status.HTTP_403_FORBIDDEN
        raise HTTPException(status_code=code, detail=str(exc))

    await manager.broadcast(list_id, "member_removed", {"user_id": user_id})
