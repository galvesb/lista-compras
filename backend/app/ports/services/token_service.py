from abc import ABC, abstractmethod


class TokenService(ABC):
    @abstractmethod
    def create_access_token(self, user_id: str) -> str: ...

    @abstractmethod
    def decode_token(self, token: str) -> str:
        """Returns user_id or raises ValueError if invalid/expired."""
        ...
