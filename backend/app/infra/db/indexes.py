from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel


async def create_indexes(db: AsyncIOMotorDatabase) -> None:
    await db.users.create_indexes([
        IndexModel([("email", ASCENDING)], unique=True, name="email_unique"),
    ])

    await db.shopping_lists.create_indexes([
        IndexModel([("owner_id", ASCENDING), ("status", ASCENDING)], name="owner_status"),
        IndexModel([("created_at", DESCENDING)], name="created_at_desc"),
    ])

    await db.list_members.create_indexes([
        IndexModel(
            [("list_id", ASCENDING), ("user_id", ASCENDING)],
            unique=True,
            name="list_user_unique",
        ),
    ])

    await db.list_items.create_indexes([
        IndexModel([("list_id", ASCENDING)], name="list_id"),
        IndexModel(
            [("list_id", ASCENDING), ("assigned_to_user_id", ASCENDING)],
            name="list_assigned",
        ),
    ])
