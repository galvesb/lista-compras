from app.domain.entities.user import User
from app.domain.exceptions.forbidden import ForbiddenError
from app.ports.repositories.user_repository import UserRepository
from app.ports.services.password_hasher import PasswordHasher
from app.ports.services.token_service import TokenService


class LoginUserUC:
    def __init__(
        self,
        user_repo: UserRepository,
        hasher: PasswordHasher,
        token_service: TokenService,
    ) -> None:
        self._user_repo = user_repo
        self._hasher = hasher
        self._token_service = token_service

    async def execute(self, email: str, password: str) -> tuple[User, str]:
        user = await self._user_repo.find_by_email(email)
        if not user or not self._hasher.verify(password, user.hashed_password):
            raise ForbiddenError("Invalid email or password")

        token = self._token_service.create_access_token(user.id)
        return user, token
