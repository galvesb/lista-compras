from datetime import datetime

from pydantic import BaseModel

from app.domain.value_objects.list_status import ListStatus


class ShoppingList(BaseModel):
    id: str
    title: str
    store_name: str
    address: str
    owner_id: str
    status: ListStatus = ListStatus.ACTIVE
    total_cost: float | None = None
    source_list_id: str | None = None
    created_at: datetime
    archived_at: datetime | None = None
