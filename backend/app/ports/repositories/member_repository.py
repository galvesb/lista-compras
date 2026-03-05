from abc import ABC, abstractmethod

from app.domain.entities.list_member import ListMember
from app.domain.value_objects.member_role import MemberRole


class MemberRepository(ABC):
    @abstractmethod
    async def add(self, list_id: str, user_id: str, role: MemberRole) -> ListMember: ...

    @abstractmethod
    async def find(self, list_id: str, user_id: str) -> ListMember | None: ...

    @abstractmethod
    async def find_all(self, list_id: str) -> list[ListMember]: ...

    @abstractmethod
    async def remove(self, list_id: str, user_id: str) -> bool: ...

    @abstractmethod
    async def find_lists_for_user(self, user_id: str) -> list[str]:
        """Returns list of list_ids where user is a member."""
        ...
