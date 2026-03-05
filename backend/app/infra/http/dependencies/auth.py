from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.adapters.repositories.mongo_user_repo import MongoUserRepository
from app.adapters.services.jwt_token_service import JWTTokenService
from app.domain.entities.user import User
from app.infra.db.mongodb import get_database

_bearer = HTTPBearer()
_token_service = JWTTokenService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> User:
    token = credentials.credentials
    try:
        user_id = _token_service.decode_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    db = get_database()
    repo = MongoUserRepository(db)
    user = await repo.find_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
