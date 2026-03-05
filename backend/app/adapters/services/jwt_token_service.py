from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from app.infra.config import settings
from app.ports.services.token_service import TokenService


class JWTTokenService(TokenService):
    def create_access_token(self, user_id: str) -> str:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )
        payload = {"sub": user_id, "exp": expire, "iat": datetime.now(UTC)}
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    def decode_token(self, token: str) -> str:
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            user_id: str = payload.get("sub", "")
            if not user_id:
                raise ValueError("Invalid token: missing subject")
            return user_id
        except JWTError as exc:
            raise ValueError(f"Invalid or expired token: {exc}") from exc
