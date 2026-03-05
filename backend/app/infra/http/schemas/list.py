from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.value_objects.list_status import ListStatus
from app.domain.value_objects.member_role import MemberRole
from app.infra.http.schemas.item import ItemResponse


class CreateListRequest(BaseModel):
    store_name: str = Field(min_length=1, max_length=200)
    address: str = Field(min_length=1, max_length=500)


class MemberInfo(BaseModel):
    user_id: str
    name: str
    email: str
    avatar_url: str | None = None
    role: MemberRole
    joined_at: datetime


class ListSummaryResponse(BaseModel):
    id: str
    title: str
    store_name: str
    status: ListStatus
    total_cost: float | None = None
    created_at: datetime
    role: MemberRole


class ListDetailResponse(BaseModel):
    id: str
    title: str
    store_name: str
    address: str
    status: ListStatus
    total_cost: float | None = None
    created_at: datetime
    archived_at: datetime | None = None
    members: list[MemberInfo]
    items: list[ItemResponse]


class InviteMemberRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
