from datetime import datetime

from pydantic import BaseModel, EmailStr


class User(BaseModel):
    id: str
    email: EmailStr
    name: str
    avatar_url: str | None = None
    hashed_password: str
    is_active: bool = True
    created_at: datetime
