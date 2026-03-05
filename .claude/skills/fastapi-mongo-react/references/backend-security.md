# Backend Security — Detalhes de Implementação

## Refresh Token Rotation

A cada uso do refresh token, emita um novo par (access + refresh) e invalide o anterior.
Isso limita o dano se um refresh token for roubado.

```python
# api/v1/endpoints/auth.py
@router.post("/refresh")
async def refresh_token(request: Request):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token não encontrado")

    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, [settings.ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Token inválido")
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token expirado ou inválido")

    # Verificar se token foi revogado (blacklist no MongoDB)
    if await is_token_revoked(refresh_token):
        raise HTTPException(status_code=401, detail="Token revogado")

    # Revogar o refresh token atual (rotation)
    await revoke_token(refresh_token)

    user = await User.get(user_id)
    new_access = create_access_token(user_id)
    new_refresh = create_refresh_token(user_id)

    response = JSONResponse({"access_token": new_access, "token_type": "bearer"})
    response.set_cookie("refresh_token", new_refresh, httponly=True, secure=True, samesite="strict")
    return response


@router.post("/logout")
async def logout(request: Request, current_user: User = Depends(get_current_user)):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        await revoke_token(refresh_token)
    response = JSONResponse({"message": "Logout realizado"})
    response.delete_cookie("refresh_token")
    return response
```

## Blacklist de Tokens no MongoDB

```python
# models/revoked_token.py
from beanie import Document
from datetime import datetime

class RevokedToken(Document):
    token_hash: str          # Hash do token (não armazenar o token em si)
    revoked_at: datetime
    expires_at: datetime     # Para TTL index

    class Settings:
        name = "revoked_tokens"
        indexes = [
            "token_hash",
            # TTL index — MongoDB remove automaticamente tokens expirados
            [("expires_at", 1), {"expireAfterSeconds": 0}]
        ]

import hashlib

async def revoke_token(token: str):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    payload = jwt.decode(token, settings.SECRET_KEY, [settings.ALGORITHM])
    await RevokedToken(
        token_hash=token_hash,
        revoked_at=datetime.now(UTC),
        expires_at=datetime.fromtimestamp(payload["exp"], UTC)
    ).insert()

async def is_token_revoked(token: str) -> bool:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return await RevokedToken.find_one(RevokedToken.token_hash == token_hash) is not None
```

## RBAC — Controle de Acesso por Role

```python
# models/user.py
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"

class User(Document):
    ...
    role: UserRole = UserRole.VIEWER

# api/deps.py
def require_role(*roles: UserRole):
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Permissão insuficiente")
        return current_user
    return checker

# Uso:
@router.delete("/users/{id}")
async def delete_user(
    id: str,
    admin: User = Depends(require_role(UserRole.ADMIN))
):
    ...
```

## Headers de Segurança com `secure`

```python
# pip install secure
from secure import SecureHeaders

secure_headers = SecureHeaders(
    server=False,              # Não revelar servidor
    hsts=True,                 # HTTP Strict Transport Security
    xfo="DENY",                # X-Frame-Options: DENY (anti-clickjacking)
    xxp=True,                  # X-XSS-Protection
    content=True,              # X-Content-Type-Options: nosniff
    csp=True,                  # Content-Security-Policy
)
```

## Proteção contra NoSQL Injection no MongoDB

MongoDB não sofre SQL injection, mas é vulnerável a injeção de operadores (`$where`, `$regex`):

```python
# ERRADO — nunca passar input do usuário direto em queries
await User.find({"email": {"$regex": user_input}}).to_list()

# CORRETO — usar Pydantic para validar e sanitizar
class SearchQuery(BaseModel):
    email: EmailStr  # Pydantic valida o formato

# Ou escapar regex se necessário:
import re
safe_pattern = re.escape(user_input)
```

## Logging Seguro

```python
# core/logging.py
import logging
import re

class SensitiveDataFilter(logging.Filter):
    PATTERNS = [
        r'"password"\s*:\s*"[^"]*"',
        r'"token"\s*:\s*"[^"]*"',
        r'Bearer\s+[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+',
    ]

    def filter(self, record):
        msg = str(record.getMessage())
        for pattern in self.PATTERNS:
            msg = re.sub(pattern, "[REDACTED]", msg)
        record.msg = msg
        return True
```