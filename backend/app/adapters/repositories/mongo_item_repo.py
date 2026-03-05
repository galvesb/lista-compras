from datetime import UTC, datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.domain.entities.list_item import ListItem
from app.domain.value_objects.item_status import ItemStatus
from app.ports.repositories.item_repository import ItemRepository


def _doc_to_item(doc: dict) -> ListItem:
    return ListItem(
        id=str(doc["_id"]),
        list_id=str(doc["list_id"]),
        name=doc["name"],
        quantity=doc["quantity"],
        status=doc["status"],
        assigned_to_user_id=str(doc["assigned_to_user_id"]) if doc.get("assigned_to_user_id") else None,
        price=doc.get("price"),
        last_price=doc.get("last_price"),
        checked_by_user_id=str(doc["checked_by_user_id"]) if doc.get("checked_by_user_id") else None,
        checked_at=doc.get("checked_at"),
        created_by_user_id=str(doc["created_by_user_id"]),
        version=doc["version"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


class MongoItemRepository(ItemRepository):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db.list_items

    async def create(
        self,
        list_id: str,
        name: str,
        quantity: str,
        created_by: str,
        last_price: float | None = None,
    ) -> ListItem:
        now = datetime.now(UTC)
        doc = {
            "list_id": ObjectId(list_id),
            "name": name,
            "quantity": quantity,
            "status": ItemStatus.PENDING,
            "assigned_to_user_id": None,
            "price": None,
            "last_price": last_price,
            "checked_by_user_id": None,
            "checked_at": None,
            "created_by_user_id": ObjectId(created_by),
            "version": 1,
            "created_at": now,
            "updated_at": now,
        }
        result = await self._col.insert_one(doc)
        doc["_id"] = result.inserted_id
        return _doc_to_item(doc)

    async def find_by_id(self, item_id: str) -> ListItem | None:
        if not ObjectId.is_valid(item_id):
            return None
        doc = await self._col.find_one({"_id": ObjectId(item_id)})
        return _doc_to_item(doc) if doc else None

    async def find_by_list(self, list_id: str, assigned_to: str | None = None) -> list[ListItem]:
        query: dict = {"list_id": ObjectId(list_id)}
        if assigned_to:
            query["assigned_to_user_id"] = ObjectId(assigned_to)
        cursor = self._col.find(query).sort("created_at", 1)
        return [_doc_to_item(doc) async for doc in cursor]

    async def update_with_version(
        self,
        item_id: str,
        expected_version: int,
        status: ItemStatus | None = None,
        price: float | None = None,
        clear_price: bool = False,
        checked_by_user_id: str | None = None,
        clear_checked_by: bool = False,
    ) -> ListItem | None:
        """
        Atomic update with optimistic locking.
        Returns updated document or None if version conflict.
        """
        now = datetime.now(UTC)
        set_fields: dict = {"updated_at": now}
        unset_fields: dict = {}

        if status is not None:
            set_fields["status"] = status
        if price is not None:
            set_fields["price"] = price
        elif clear_price:
            unset_fields["price"] = ""
        if checked_by_user_id is not None:
            set_fields["checked_by_user_id"] = ObjectId(checked_by_user_id)
            set_fields["checked_at"] = now
        elif clear_checked_by:
            unset_fields["checked_by_user_id"] = ""
            unset_fields["checked_at"] = ""

        update: dict = {"$set": set_fields, "$inc": {"version": 1}}
        if unset_fields:
            update["$unset"] = unset_fields

        doc = await self._col.find_one_and_update(
            {"_id": ObjectId(item_id), "version": expected_version},
            update,
            return_document=ReturnDocument.AFTER,
        )
        return _doc_to_item(doc) if doc else None

    async def update_assigned_to(self, item_id: str, user_id: str | None) -> ListItem | None:
        value = ObjectId(user_id) if user_id else None
        doc = await self._col.find_one_and_update(
            {"_id": ObjectId(item_id)},
            {"$set": {"assigned_to_user_id": value, "updated_at": datetime.now(UTC)}, "$inc": {"version": 1}},
            return_document=ReturnDocument.AFTER,
        )
        return _doc_to_item(doc) if doc else None

    async def reassign_items(self, list_id: str, from_user_id: str, to_user_id: str) -> int:
        result = await self._col.update_many(
            {"list_id": ObjectId(list_id), "assigned_to_user_id": ObjectId(from_user_id)},
            {"$set": {"assigned_to_user_id": ObjectId(to_user_id), "updated_at": datetime.now(UTC)}},
        )
        return result.modified_count

    async def delete(self, item_id: str) -> bool:
        result = await self._col.delete_one({"_id": ObjectId(item_id)})
        return result.deleted_count > 0

    async def get_checked_total(self, list_id: str) -> float:
        pipeline = [
            {"$match": {"list_id": ObjectId(list_id), "status": ItemStatus.CHECKED, "price": {"$ne": None}}},
            {"$group": {"_id": None, "total": {"$sum": "$price"}}},
        ]
        async for doc in self._col.aggregate(pipeline):
            return float(doc["total"])
        return 0.0
