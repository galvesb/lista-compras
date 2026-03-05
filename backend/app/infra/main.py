from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.infra.config import settings
from app.infra.db.indexes import create_indexes
from app.infra.db.mongodb import close_connection, get_database
from app.infra.http.middleware.security_headers import SecurityHeadersMiddleware
from app.infra.http.routers import auth, items, lists, members, users, ws

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db = get_database()
    await create_indexes(db)
    yield
    # Shutdown
    await close_connection()


app = FastAPI(
    title="Lista de Compras API",
    version="1.0.0",
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=f"{settings.api_prefix}/redoc",
    openapi_url=f"{settings.api_prefix}/openapi.json",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────
PREFIX = settings.api_prefix
app.include_router(auth.router, prefix=PREFIX)
app.include_router(lists.router, prefix=PREFIX)
app.include_router(items.router, prefix=f"{PREFIX}/lists")
app.include_router(members.router, prefix=f"{PREFIX}/lists")
app.include_router(users.router, prefix=PREFIX)
app.include_router(ws.router)  # WebSocket at /ws/lists/{id}


@app.get("/health")
async def health() -> dict:
    from app.infra.db.mongodb import get_client
    try:
        client = get_client()
        await client.admin.command("ping")
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"
    status = "ok" if db_status == "ok" else "degraded"
    return {"status": status, "mongodb": db_status}
