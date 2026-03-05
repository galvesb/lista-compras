from datetime import UTC, datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.entities.user import User
from app.ports.repositories.user_repository import UserRepository


def _doc_to_user(doc: dict) -> User:
    return User(
        id=str(doc["_id"]),
        email=doc["email"],
        name=doc["name"],
        avatar_url=doc.get("avatar_url"),
        hashed_password=doc["hashed_password"],
        is_active=doc.get("is_active", True),
        created_at=doc["created_at"],
    )


class MongoUserRepository(UserRepository):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db.users

    async def create(self, email: str, name: str, hashed_password: str) -> User:
        doc = {
            "email": email,
            "name": name,
            "hashed_password": hashed_password,
            "avatar_url": None,
            "is_active": True,
            "created_at": datetime.now(UTC),
        }
        result = await self._col.insert_one(doc)
        doc["_id"] = result.inserted_id
        return _doc_to_user(doc)

    async def find_by_email(self, email: str) -> User | None:
        doc = await self._col.find_one({"email": email, "is_active": True})
        return _doc_to_user(doc) if doc else None

    async def find_by_id(self, user_id: str) -> User | None:
        if not ObjectId.is_valid(user_id):
            return None
        doc = await self._col.find_one({"_id": ObjectId(user_id), "is_active": True})
        return _doc_to_user(doc) if doc else None

    async def search_by_email(self, email_query: str, limit: int = 5) -> list[User]:
        cursor = self._col.find(
            {"email": {"$regex": email_query, "$options": "i"}, "is_active": True},
            limit=limit,
        )
        return [_doc_to_user(doc) async for doc in cursor]
