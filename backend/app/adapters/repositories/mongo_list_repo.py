from datetime import UTC, datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.entities.shopping_list import ShoppingList
from app.domain.value_objects.list_status import ListStatus
from app.ports.repositories.list_repository import ListRepository


def _doc_to_list(doc: dict) -> ShoppingList:
    return ShoppingList(
        id=str(doc["_id"]),
        title=doc["title"],
        store_name=doc["store_name"],
        address=doc["address"],
        owner_id=str(doc["owner_id"]),
        status=doc["status"],
        total_cost=doc.get("total_cost"),
        source_list_id=str(doc["source_list_id"]) if doc.get("source_list_id") else None,
        created_at=doc["created_at"],
        archived_at=doc.get("archived_at"),
    )


class MongoListRepository(ListRepository):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db.shopping_lists

    async def create(self, store_name: str, address: str, title: str, owner_id: str) -> ShoppingList:
        doc = {
            "title": title,
            "store_name": store_name,
            "address": address,
            "owner_id": ObjectId(owner_id),
            "status": ListStatus.ACTIVE,
            "total_cost": None,
            "source_list_id": None,
            "created_at": datetime.now(UTC),
            "archived_at": None,
        }
        result = await self._col.insert_one(doc)
        doc["_id"] = result.inserted_id
        return _doc_to_list(doc)

    async def find_by_id(self, list_id: str) -> ShoppingList | None:
        if not ObjectId.is_valid(list_id):
            return None
        doc = await self._col.find_one({"_id": ObjectId(list_id)})
        return _doc_to_list(doc) if doc else None

    async def find_by_user(self, user_id: str, status: ListStatus | None = None) -> list[ShoppingList]:
        query: dict = {"owner_id": ObjectId(user_id)}
        if status:
            query["status"] = status
        cursor = self._col.find(query).sort("created_at", -1)
        return [_doc_to_list(doc) async for doc in cursor]

    async def update_status_archived(self, list_id: str, total_cost: float) -> ShoppingList | None:
        doc = await self._col.find_one_and_update(
            {"_id": ObjectId(list_id), "status": ListStatus.ACTIVE},
            {"$set": {"status": ListStatus.ARCHIVED, "total_cost": total_cost, "archived_at": datetime.now(UTC)}},
            return_document=True,
        )
        return _doc_to_list(doc) if doc else None
