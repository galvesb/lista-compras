from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.adapters.repositories.mongo_user_repo import MongoUserRepository
from app.adapters.services.bcrypt_hasher import BcryptHasher
from app.adapters.services.jwt_token_service import JWTTokenService
from app.domain.entities.user import User
from app.domain.exceptions.conflict import DuplicateError
from app.domain.exceptions.forbidden import ForbiddenError
from app.infra.config import settings
from app.infra.db.mongodb import get_database
from app.infra.http.dependencies.auth import get_current_user
from app.infra.http.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.use_cases.auth.login_user import LoginUserUC
from app.use_cases.auth.register_user import RegisterUserUC

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest) -> UserResponse:
    db = get_database()
    uc = RegisterUserUC(MongoUserRepository(db), BcryptHasher())
    try:
        user = await uc.execute(payload.email, payload.name, payload.password)
    except DuplicateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return UserResponse(id=user.id, email=user.email, name=user.name, avatar_url=user.avatar_url)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest) -> TokenResponse:
    db = get_database()
    uc = LoginUserUC(MongoUserRepository(db), BcryptHasher(), JWTTokenService())
    try:
        _, token = await uc.execute(payload.email, payload.password)
    except ForbiddenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        avatar_url=current_user.avatar_url,
    )
