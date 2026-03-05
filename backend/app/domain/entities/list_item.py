from datetime import datetime

from pydantic import BaseModel

from app.domain.value_objects.item_status import ItemStatus


class ListItem(BaseModel):
    id: str
    list_id: str
    name: str
    quantity: str
    status: ItemStatus = ItemStatus.PENDING
    assigned_to_user_id: str | None = None
    price: float | None = None
    last_price: float | None = None
    checked_by_user_id: str | None = None
    checked_at: datetime | None = None
    created_by_user_id: str
    version: int = 1
    created_at: datetime
    updated_at: datetime
