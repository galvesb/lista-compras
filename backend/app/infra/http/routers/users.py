from fastapi import APIRouter, Depends, Query

from app.adapters.repositories.mongo_user_repo import MongoUserRepository
from app.domain.entities.user import User
from app.infra.db.mongodb import get_database
from app.infra.http.dependencies.auth import get_current_user
from app.infra.http.schemas.auth import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/search", response_model=list[UserResponse])
async def search_users(
    email: str = Query(min_length=3, max_length=254),
    current_user: User = Depends(get_current_user),
) -> list[UserResponse]:
    db = get_database()
    repo = MongoUserRepository(db)
    users = await repo.search_by_email(email, limit=5)
    return [
        UserResponse(id=u.id, email=u.email, name=u.name, avatar_url=u.avatar_url)
        for u in users
        if u.id != current_user.id  # exclude self from results
    ]
