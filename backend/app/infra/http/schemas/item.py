from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.domain.value_objects.item_status import ItemStatus


class AssignedUserInfo(BaseModel):
    user_id: str
    name: str
    avatar_url: str | None = None


class ItemResponse(BaseModel):
    id: str
    list_id: str
    name: str
    quantity: str
    status: ItemStatus
    assigned_to: AssignedUserInfo | None = None
    price: float | None = None
    last_price: float | None = None
    checked_by: AssignedUserInfo | None = None
    checked_at: datetime | None = None
    version: int
    created_at: datetime


class AddItemRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    quantity: str = Field(min_length=1, max_length=100)


class UpdateItemRequest(BaseModel):
    version: int = Field(gt=0, description="Current version for optimistic locking")
    status: ItemStatus | None = None
    price: float | None = Field(default=None, ge=0, le=99999.99)

    @model_validator(mode="after")
    def price_only_with_checked(self) -> "UpdateItemRequest":
        if self.price is not None and self.status != ItemStatus.CHECKED:
            raise ValueError("Price can only be set when status is 'checked'")
        return self


class AssignItemRequest(BaseModel):
    user_id: str | None = None  # None = remove assignment
