from datetime import UTC, datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.entities.list_member import ListMember
from app.domain.value_objects.member_role import MemberRole
from app.ports.repositories.member_repository import MemberRepository


def _doc_to_member(doc: dict) -> ListMember:
    return ListMember(
        id=str(doc["_id"]),
        list_id=str(doc["list_id"]),
        user_id=str(doc["user_id"]),
        role=doc["role"],
        joined_at=doc["joined_at"],
    )


class MongoMemberRepository(MemberRepository):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db.list_members

    async def add(self, list_id: str, user_id: str, role: MemberRole) -> ListMember:
        doc = {
            "list_id": ObjectId(list_id),
            "user_id": ObjectId(user_id),
            "role": role,
            "joined_at": datetime.now(UTC),
        }
        result = await self._col.insert_one(doc)
        doc["_id"] = result.inserted_id
        return _doc_to_member(doc)

    async def find(self, list_id: str, user_id: str) -> ListMember | None:
        doc = await self._col.find_one(
            {"list_id": ObjectId(list_id), "user_id": ObjectId(user_id)}
        )
        return _doc_to_member(doc) if doc else None

    async def find_all(self, list_id: str) -> list[ListMember]:
        cursor = self._col.find({"list_id": ObjectId(list_id)})
        return [_doc_to_member(doc) async for doc in cursor]

    async def remove(self, list_id: str, user_id: str) -> bool:
        result = await self._col.delete_one(
            {"list_id": ObjectId(list_id), "user_id": ObjectId(user_id)}
        )
        return result.deleted_count > 0

    async def find_lists_for_user(self, user_id: str) -> list[str]:
        cursor = self._col.find({"user_id": ObjectId(user_id)}, {"list_id": 1})
        return [str(doc["list_id"]) async for doc in cursor]
