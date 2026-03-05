from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.infra.config import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(
            settings.mongo_uri,
            maxPoolSize=20,
            minPoolSize=2,
            serverSelectionTimeoutMS=5000,
        )
    return _client


def get_database() -> AsyncIOMotorDatabase:
    return get_client()[settings.mongo_db]


async def close_connection() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
