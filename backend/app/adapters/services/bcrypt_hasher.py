from passlib.context import CryptContext

from app.ports.services.password_hasher import PasswordHasher

_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


class BcryptHasher(PasswordHasher):
    def hash(self, plain: str) -> str:
        return _ctx.hash(plain)

    def verify(self, plain: str, hashed: str) -> bool:
        return _ctx.verify(plain, hashed)
