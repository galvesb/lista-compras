# Backend DB — MongoDB Avançado com Motor + Beanie

## Transações Multi-documento

MongoDB suporta transações ACID a partir da versão 4.0 em replica sets:

```python
from motor.motor_asyncio import AsyncIOMotorClient

async def transfer_with_transaction(from_id: str, to_id: str, amount: float):
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    async with await client.start_session() as session:
        async with session.start_transaction():
            from_account = await Account.get(from_id, session=session)
            if from_account.balance < amount:
                raise ValueError("Saldo insuficiente")
            await from_account.set({Account.balance: from_account.balance - amount}, session=session)
            to_account = await Account.get(to_id, session=session)
            await to_account.set({Account.balance: to_account.balance + amount}, session=session)
            # Commit automático ao sair do bloco
```

## Índices Avançados

```python
# models/product.py
from beanie import Document, Indexed
from pymongo import TEXT, ASCENDING, DESCENDING

class Product(Document):
    name: str
    description: str
    price: float
    category: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "products"
        indexes = [
            # Índice composto para queries frequentes
            [("category", ASCENDING), ("price", ASCENDING)],
            # Índice de texto para busca full-text
            [("name", TEXT), ("description", TEXT)],
            # Índice TTL para documentos temporários
            # [("expires_at", ASCENDING), {"expireAfterSeconds": 0}],
        ]
```

## Paginação com Cursor (mais eficiente que skip/limit)

```python
# Para grandes coleções, use cursor-based pagination
class PaginatedResponse(BaseModel):
    items: list
    next_cursor: Optional[str] = None
    has_more: bool

async def get_products_paginated(cursor: Optional[str] = None, limit: int = 20):
    query = Product.find()
    if cursor:
        # Buscar produtos com _id > cursor
        from bson import ObjectId
        query = query.find({"_id": {"$gt": ObjectId(cursor)}})
    
    items = await query.sort("_id").limit(limit + 1).to_list()
    has_more = len(items) > limit
    if has_more:
        items = items[:limit]
    
    next_cursor = str(items[-1].id) if has_more else None
    return PaginatedResponse(items=items, next_cursor=next_cursor, has_more=has_more)
```

## Aggregation Pipeline

```python
# Relatório de vendas por categoria
async def sales_by_category(start_date: datetime, end_date: datetime):
    pipeline = [
        {"$match": {"created_at": {"$gte": start_date, "$lte": end_date}}},
        {"$group": {
            "_id": "$category",
            "total_revenue": {"$sum": "$price"},
            "count": {"$sum": 1},
            "avg_price": {"$avg": "$price"}
        }},
        {"$sort": {"total_revenue": -1}},
        {"$project": {
            "category": "$_id",
            "total_revenue": 1,
            "count": 1,
            "avg_price": {"$round": ["$avg_price", 2]},
            "_id": 0
        }}
    ]
    return await Product.aggregate(pipeline).to_list()
```

## Repositório com Filtros Dinâmicos

```python
# db/repositories/product_repo.py
from typing import Optional
from beanie.operators import In, GTE, LTE, RegEx

class ProductRepository(BaseRepository[Product]):
    async def search(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[Product]:
        filters = []
        if query:
            filters.append(RegEx(Product.name, query, "i"))
        if category:
            filters.append(Product.category == category)
        if min_price is not None:
            filters.append(GTE(Product.price, min_price))
        if max_price is not None:
            filters.append(LTE(Product.price, max_price))

        find_query = Product.find(*filters) if filters else Product.find_all()
        return await find_query.skip(skip).limit(limit).to_list()
```

## Configuração de Conexão para Produção

```python
# db/mongodb.py
from motor.motor_asyncio import AsyncIOMotorClient

def get_motor_client() -> AsyncIOMotorClient:
    return AsyncIOMotorClient(
        settings.MONGODB_URL,
        maxPoolSize=50,          # Pool de conexões
        minPoolSize=10,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=10000,
        socketTimeoutMS=10000,
        retryWrites=True,        # Retry automático em writes transientes
        w="majority",            # Write concern: confirmar na maioria dos nós
        readPreference="primaryPreferred",  # Leitura do primário, fallback secundário
    )
```