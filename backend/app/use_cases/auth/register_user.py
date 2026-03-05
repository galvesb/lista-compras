from app.domain.entities.user import User
from app.domain.exceptions.conflict import DuplicateError
from app.ports.repositories.user_repository import UserRepository
from app.ports.services.password_hasher import PasswordHasher


class RegisterUserUC:
    def __init__(self, user_repo: UserRepository, hasher: PasswordHasher) -> None:
        self._user_repo = user_repo
        self._hasher = hasher

    async def execute(self, email: str, name: str, password: str) -> User:
        existing = await self._user_repo.find_by_email(email)
        if existing:
            raise DuplicateError(f"Email '{email}' already registered")

        hashed = self._hasher.hash(password)
        return await self._user_repo.create(email=email, name=name, hashed_password=hashed)
