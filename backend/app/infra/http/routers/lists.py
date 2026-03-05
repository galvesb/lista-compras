from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.adapters.repositories.mongo_item_repo import MongoItemRepository
from app.adapters.repositories.mongo_list_repo import MongoListRepository
from app.adapters.repositories.mongo_member_repo import MongoMemberRepository
from app.adapters.repositories.mongo_user_repo import MongoUserRepository
from app.domain.entities.list_member import ListMember
from app.domain.entities.user import User
from app.domain.exceptions.forbidden import ForbiddenError
from app.domain.exceptions.not_found import NotFoundError
from app.domain.value_objects.list_status import ListStatus
from app.infra.db.mongodb import get_database
from app.infra.http.dependencies.auth import get_current_user
from app.infra.http.dependencies.permissions import require_list_member, require_list_owner
from app.infra.http.routers.items import _enrich_item
from app.infra.http.schemas.item import AssignedUserInfo
from app.infra.http.schemas.list import (
    CreateListRequest,
    ListDetailResponse,
    ListSummaryResponse,
    MemberInfo,
)
from app.infra.websocket.connection_manager import manager
from app.use_cases.lists.archive_list import ArchiveListUC
from app.use_cases.lists.create_list import CreateListUC
from app.use_cases.lists.reuse_list import ReuseListUC

router = APIRouter(prefix="/lists", tags=["lists"])


@router.get("", response_model=list[ListSummaryResponse])
async def get_lists(
    status_filter: ListStatus | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
) -> list[ListSummaryResponse]:
    db = get_database()
    list_repo = MongoListRepository(db)
    member_repo = MongoMemberRepository(db)

    # Get all list_ids where user is a member
    list_ids = await member_repo.find_lists_for_user(current_user.id)

    results = []
    for lid in list_ids:
        sl = await list_repo.find_by_id(lid)
        if not sl:
            continue
        if status_filter and sl.status != status_filter:
            continue
        membership = await member_repo.find(lid, current_user.id)
        results.append(
            ListSummaryResponse(
                id=sl.id,
                title=sl.title,
                store_name=sl.store_name,
                status=sl.status,
                total_cost=sl.total_cost,
                created_at=sl.created_at,
                role=membership.role if membership else "member",
            )
        )
    results.sort(key=lambda x: x.created_at, reverse=True)
    return results


@router.post("", response_model=ListSummaryResponse, status_code=status.HTTP_201_CREATED)
async def create_list(
    payload: CreateListRequest,
    current_user: User = Depends(get_current_user),
) -> ListSummaryResponse:
    db = get_database()
    uc = CreateListUC(MongoListRepository(db), MongoMemberRepository(db))
    sl = await uc.execute(payload.store_name, payload.address, current_user.id)
    return ListSummaryResponse(
        id=sl.id,
        title=sl.title,
        store_name=sl.store_name,
        status=sl.status,
        total_cost=sl.total_cost,
        created_at=sl.created_at,
        role="owner",
    )


@router.get("/{list_id}", response_model=ListDetailResponse)
async def get_list(
    list_id: str = Path(...),
    filter: str | None = Query(default=None, pattern="^mine$"),
    current_user: User = Depends(get_current_user),
    membership: ListMember = Depends(require_list_member),
) -> ListDetailResponse:
    db = get_database()
    list_repo = MongoListRepository(db)
    member_repo = MongoMemberRepository(db)
    item_repo = MongoItemRepository(db)
    user_repo = MongoUserRepository(db)

    sl = await list_repo.find_by_id(list_id)
    if not sl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="List not found")

    members_data = await member_repo.find_all(list_id)
    members = []
    for m in members_data:
        u = await user_repo.find_by_id(m.user_id)
        if u:
            members.append(
                MemberInfo(
                    user_id=u.id,
                    name=u.name,
                    email=u.email,
                    avatar_url=u.avatar_url,
                    role=m.role,
                    joined_at=m.joined_at,
                )
            )

    assigned_to = current_user.id if filter == "mine" else None
    raw_items = await item_repo.find_by_list(list_id, assigned_to=assigned_to)
    items = [await _enrich_item(item, db) for item in raw_items]

    return ListDetailResponse(
        id=sl.id,
        title=sl.title,
        store_name=sl.store_name,
        address=sl.address,
        status=sl.status,
        total_cost=sl.total_cost,
        created_at=sl.created_at,
        archived_at=sl.archived_at,
        members=members,
        items=items,
    )


@router.patch("/{list_id}/archive", response_model=ListSummaryResponse)
async def archive_list(
    list_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    membership: ListMember = Depends(require_list_owner),
) -> ListSummaryResponse:
    db = get_database()
    uc = ArchiveListUC(MongoListRepository(db), MongoItemRepository(db))
    try:
        sl = await uc.execute(list_id, current_user.id)
    except (NotFoundError, ForbiddenError) as exc:
        code = status.HTTP_404_NOT_FOUND if isinstance(exc, NotFoundError) else status.HTTP_403_FORBIDDEN
        raise HTTPException(status_code=code, detail=str(exc))

    await manager.broadcast(list_id, "list_archived", {"total_cost": sl.total_cost})
    return ListSummaryResponse(
        id=sl.id,
        title=sl.title,
        store_name=sl.store_name,
        status=sl.status,
        total_cost=sl.total_cost,
        created_at=sl.created_at,
        role="owner",
    )


@router.post("/{list_id}/reuse", response_model=ListSummaryResponse, status_code=status.HTTP_201_CREATED)
async def reuse_list(
    list_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    membership: ListMember = Depends(require_list_owner),
) -> ListSummaryResponse:
    db = get_database()
    uc = ReuseListUC(MongoListRepository(db), MongoItemRepository(db), MongoMemberRepository(db))
    try:
        sl = await uc.execute(list_id, current_user.id)
    except (NotFoundError, ForbiddenError) as exc:
        code = status.HTTP_404_NOT_FOUND if isinstance(exc, NotFoundError) else status.HTTP_403_FORBIDDEN
        raise HTTPException(status_code=code, detail=str(exc))

    return ListSummaryResponse(
        id=sl.id,
        title=sl.title,
        store_name=sl.store_name,
        status=sl.status,
        total_cost=sl.total_cost,
        created_at=sl.created_at,
        role="owner",
    )
