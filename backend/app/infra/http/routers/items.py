"""
Items router — inclui o fluxo mais complexo: PATCH /{item_id} com optimistic locking.
"""
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.adapters.repositories.mongo_item_repo import MongoItemRepository
from app.adapters.repositories.mongo_member_repo import MongoMemberRepository
from app.adapters.repositories.mongo_user_repo import MongoUserRepository
from app.domain.entities.list_member import ListMember
from app.domain.entities.user import User
from app.domain.exceptions.conflict import ConflictError
from app.domain.exceptions.forbidden import ForbiddenError
from app.domain.exceptions.not_found import NotFoundError
from app.infra.db.mongodb import get_database
from app.infra.http.dependencies.auth import get_current_user
from app.infra.http.dependencies.permissions import require_list_member, require_list_owner
from app.infra.http.schemas.item import (
    AddItemRequest,
    AssignItemRequest,
    AssignedUserInfo,
    ItemResponse,
    UpdateItemRequest,
)
from app.infra.websocket.connection_manager import manager
from app.use_cases.items.add_item import AddItemUC
from app.use_cases.items.assign_item import AssignItemUC
from app.use_cases.items.delete_item import DeleteItemUC
from app.use_cases.items.update_item_status import UpdateItemStatusUC

router = APIRouter(prefix="/{list_id}/items", tags=["items"])


async def _enrich_item(item, db) -> ItemResponse:
    """Enrich item with user info for assigned_to and checked_by."""
    user_repo = MongoUserRepository(db)
    assigned_to = None
    checked_by = None

    if item.assigned_to_user_id:
        u = await user_repo.find_by_id(item.assigned_to_user_id)
        if u:
            assigned_to = AssignedUserInfo(user_id=u.id, name=u.name, avatar_url=u.avatar_url)

    if item.checked_by_user_id:
        u = await user_repo.find_by_id(item.checked_by_user_id)
        if u:
            checked_by = AssignedUserInfo(user_id=u.id, name=u.name, avatar_url=u.avatar_url)

    return ItemResponse(
        id=item.id,
        list_id=item.list_id,
        name=item.name,
        quantity=item.quantity,
        status=item.status,
        assigned_to=assigned_to,
        price=item.price,
        last_price=item.last_price,
        checked_by=checked_by,
        checked_at=item.checked_at,
        version=item.version,
        created_at=item.created_at,
    )


@router.get("", response_model=list[ItemResponse])
async def list_items(
    list_id: str = Path(...),
    filter: str | None = Query(default=None, pattern="^mine$"),
    membership: ListMember = Depends(require_list_member),
    current_user: User = Depends(get_current_user),
) -> list[ItemResponse]:
    db = get_database()
    repo = MongoItemRepository(db)
    assigned_to = current_user.id if filter == "mine" else None
    items = await repo.find_by_list(list_id, assigned_to=assigned_to)
    return [await _enrich_item(item, db) for item in items]


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def add_item(
    payload: AddItemRequest,
    list_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    membership: ListMember = Depends(require_list_member),
) -> ItemResponse:
    db = get_database()
    uc = AddItemUC(MongoItemRepository(db), None, MongoMemberRepository(db))  # list_repo not needed here
    try:
        item = await MongoItemRepository(db).create(
            list_id=list_id,
            name=payload.name,
            quantity=payload.quantity,
            created_by=current_user.id,
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    response = await _enrich_item(item, db)
    await manager.broadcast(list_id, "item_added", response.model_dump(mode="json"))
    return response


@router.patch("/{item_id}", response_model=ItemResponse)
async def update_item(
    payload: UpdateItemRequest,
    list_id: str = Path(...),
    item_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    membership: ListMember = Depends(require_list_member),
) -> ItemResponse:
    """
    Check, uncheck, or mark unavailable an item.
    Uses optimistic locking: include current `version` in request.
    Returns 409 if the item was modified concurrently.
    """
    db = get_database()
    uc = UpdateItemStatusUC(MongoItemRepository(db), MongoMemberRepository(db))
    try:
        item = await uc.execute(
            list_id=list_id,
            item_id=item_id,
            expected_version=payload.version,
            new_status=payload.status,
            price=payload.price,
            current_user_id=current_user.id,
        )
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Version conflict", "current_version": exc.current_version},
        )

    response = await _enrich_item(item, db)
    await manager.broadcast(
        list_id,
        "item_updated",
        response.model_dump(mode="json"),
        exclude_user_id=current_user.id,
    )
    return response


@router.patch("/{item_id}/assign", response_model=ItemResponse)
async def assign_item(
    payload: AssignItemRequest,
    list_id: str = Path(...),
    item_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    membership: ListMember = Depends(require_list_owner),
) -> ItemResponse:
    db = get_database()
    uc = AssignItemUC(MongoItemRepository(db), MongoMemberRepository(db))
    try:
        item = await uc.execute(list_id, item_id, payload.user_id, current_user.id)
    except (ForbiddenError, NotFoundError) as exc:
        code = status.HTTP_403_FORBIDDEN if isinstance(exc, ForbiddenError) else status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=code, detail=str(exc))

    response = await _enrich_item(item, db)
    await manager.broadcast(list_id, "item_assigned", response.model_dump(mode="json"))
    return response


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    list_id: str = Path(...),
    item_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    membership: ListMember = Depends(require_list_member),
) -> None:
    db = get_database()
    uc = DeleteItemUC(MongoItemRepository(db), MongoMemberRepository(db))
    try:
        await uc.execute(list_id, item_id, current_user.id)
    except (ForbiddenError, NotFoundError) as exc:
        code = status.HTTP_403_FORBIDDEN if isinstance(exc, ForbiddenError) else status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=code, detail=str(exc))

    await manager.broadcast(list_id, "item_deleted", {"item_id": item_id})
