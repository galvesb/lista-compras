from datetime import datetime

from pydantic import BaseModel

from app.domain.value_objects.member_role import MemberRole


class ListMember(BaseModel):
    id: str
    list_id: str
    user_id: str
    role: MemberRole
    joined_at: datetime
