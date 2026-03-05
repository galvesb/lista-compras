# Design: Lista de Compras Colaborativas

## Arquitetura Geral

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DOCKER COMPOSE                              │
│                                                                     │
│  ┌──────────────┐   HTTP :80    ┌──────────────────────────────┐   │
│  │   BROWSER    │──────────────▶│  frontend (React + Nginx)    │   │
│  │  (mobile /   │               │  multi-stage build           │   │
│  │   desktop)   │               │  non-root, alpine            │   │
│  └──────┬───────┘               └──────────────┬───────────────┘   │
│         │                                      │ /api/* proxy_pass  │
│         │ WS ws://host/ws/lists/{id}?token=    │ :8000              │
│         │                                      ▼                    │
│         └──────────────────────────▶┌──────────────────────────┐   │
│                                     │  api (FastAPI + Uvicorn)  │   │
│                                     │  non-root, python:slim    │   │
│                                     │  Clean Architecture       │   │
│                                     └──────────────┬────────────┘   │
│                                                    │                │
│                                          rede interna               │
│                                          (não exposta)              │
│                                                    ▼                │
│                                     ┌──────────────────────────┐   │
│                                     │  mongodb (mongo:7-jammy)  │   │
│                                     │  volume: mongo_data       │   │
│                                     │  só acessível via api     │   │
│                                     └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 1. Modelagem de Dados (MongoDB)

### Decisão: Items como coleção separada (referenciada)

**Justificativa:** O padrão de acesso dominante é atualização granular por item (check, preço, status). Com embedding, cada update em um item requereria um `arrayFilters` no documento pai — o que, sob concorrência (dois usuários dando check simultaneamente), causaria conflitos no mesmo documento. Com documentos separados, cada item recebe um update atômico independente com optimistic locking.

### Collection: `users`

```json
{
  "_id": "ObjectId",
  "email": "string (unique, indexed)",
  "name": "string",
  "avatar_url": "string | null",
  "hashed_password": "string (bcrypt, cost≥12)",
  "is_active": "boolean",
  "created_at": "datetime"
}
```

Índices: `{ email: 1 }` unique

### Collection: `shopping_lists`

```json
{
  "_id": "ObjectId",
  "title": "string",
  "store_name": "string",
  "address": "string",
  "owner_id": "ObjectId → users",
  "status": "active | archived",
  "total_cost": "float | null",
  "created_at": "datetime",
  "archived_at": "datetime | null",
  "source_list_id": "ObjectId | null"
}
```

Índices: `{ owner_id: 1, status: 1 }`, `{ created_at: -1 }`

### Collection: `list_members`

```json
{
  "_id": "ObjectId",
  "list_id": "ObjectId → shopping_lists (indexed)",
  "user_id": "ObjectId → users",
  "role": "owner | member",
  "joined_at": "datetime"
}
```

Índices: `{ list_id: 1, user_id: 1 }` unique compound

### Collection: `list_items`

```json
{
  "_id": "ObjectId",
  "list_id": "ObjectId → shopping_lists (indexed)",
  "name": "string",
  "quantity": "string",
  "status": "pending | checked | unavailable",
  "assigned_to_user_id": "ObjectId | null → users",
  "price": "float | null",
  "last_price": "float | null",
  "checked_by_user_id": "ObjectId | null → users",
  "checked_at": "datetime | null",
  "created_by_user_id": "ObjectId → users",
  "version": "integer (inicia em 1, +1 a cada update)",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

Índices: `{ list_id: 1 }`, `{ list_id: 1, assigned_to_user_id: 1 }`

### Collection: `list_invites`

```json
{
  "_id": "ObjectId",
  "list_id": "ObjectId → shopping_lists",
  "invited_email": "string",
  "invited_by_user_id": "ObjectId → users",
  "status": "pending | accepted | rejected",
  "created_at": "datetime",
  "expires_at": "datetime"
}
```

---

## 2. Clean Architecture — Estrutura de Diretórios

```
backend/
├── app/
│   ├── domain/                        # Camada de Domínio (zero dependências externas)
│   │   ├── entities/
│   │   │   ├── user.py                # Dataclass/Pydantic puro
│   │   │   ├── shopping_list.py
│   │   │   ├── list_item.py
│   │   │   └── list_member.py
│   │   ├── value_objects/
│   │   │   ├── item_status.py         # Enum: pending | checked | unavailable
│   │   │   └── member_role.py         # Enum: owner | member
│   │   └── exceptions/
│   │       ├── not_found.py
│   │       ├── forbidden.py
│   │       └── conflict.py            # Optimistic lock conflict (409)
│   │
│   ├── use_cases/                     # Regras de negócio (orquestram domínio + ports)
│   │   ├── auth/
│   │   │   ├── register_user.py
│   │   │   └── login_user.py
│   │   ├── lists/
│   │   │   ├── create_list.py
│   │   │   ├── archive_list.py
│   │   │   ├── reuse_list.py
│   │   │   └── get_lists.py
│   │   ├── items/
│   │   │   ├── add_item.py
│   │   │   ├── update_item_status.py  # check / uncheck / unavailable + preço
│   │   │   ├── assign_item.py
│   │   │   └── delete_item.py
│   │   └── members/
│   │       ├── invite_member.py
│   │       └── remove_member.py
│   │
│   ├── ports/                         # Interfaces (abstrações dos repositórios)
│   │   ├── repositories/
│   │   │   ├── user_repository.py     # ABC
│   │   │   ├── list_repository.py
│   │   │   ├── item_repository.py
│   │   │   └── member_repository.py
│   │   └── services/
│   │       ├── password_hasher.py     # ABC
│   │       └── token_service.py       # ABC
│   │
│   ├── adapters/                      # Implementações concretas
│   │   ├── repositories/
│   │   │   ├── mongo_user_repo.py     # Motor/Beanie
│   │   │   ├── mongo_list_repo.py
│   │   │   ├── mongo_item_repo.py
│   │   │   └── mongo_member_repo.py
│   │   └── services/
│   │       ├── bcrypt_hasher.py
│   │       └── jwt_token_service.py
│   │
│   └── infra/                         # Framework & entrypoints
│       ├── db/
│       │   ├── mongodb.py             # Motor client, connection pool
│       │   └── indexes.py             # Criação de índices na startup
│       ├── websocket/
│       │   └── connection_manager.py  # Gerencia rooms por list_id
│       ├── http/
│       │   ├── routers/
│       │   │   ├── auth.py
│       │   │   ├── lists.py
│       │   │   ├── items.py
│       │   │   ├── members.py
│       │   │   └── users.py
│       │   ├── dependencies/
│       │   │   ├── auth.py            # get_current_user (JWT via DI)
│       │   │   └── permissions.py     # require_list_owner, require_list_member
│       │   ├── schemas/               # Pydantic request/response
│       │   │   ├── auth.py
│       │   │   ├── list.py
│       │   │   └── item.py
│       │   └── middleware/
│       │       ├── security_headers.py
│       │       └── rate_limiter.py
│       └── config.py                  # Settings via pydantic-settings + .env
│
├── tests/
│   ├── unit/                          # Testa use_cases com mocks
│   └── integration/                   # Testa adapters com MongoDB real
├── Dockerfile
├── pyproject.toml
└── .env.example
```

---

## 3. Contratos da API (RESTful)

**Base URL:** `/api/v1`
**Auth:** `Authorization: Bearer <jwt>` em todas as rotas protegidas

### Auth

```
POST /auth/register
Request:  { "email": "str", "password": "str", "name": "str" }
Response: { "id": "str", "email": "str", "name": "str" }
Erros:    409 email já cadastrado

POST /auth/login
Request:  { "email": "str", "password": "str" }
Response: { "access_token": "str", "token_type": "bearer", "expires_in": 900 }
Erros:    401 credenciais inválidas

GET /auth/me
Response: { "id": "str", "email": "str", "name": "str", "avatar_url": "str|null" }
```

### Listas

```
GET /lists
Query:  ?status=active|archived
Response: [{ "id", "title", "store_name", "status", "total_cost",
             "created_at", "role": "owner|member" }]

POST /lists
Request:  { "store_name": "str", "address": "str" }
Response: { "id": "str", "title": "Pão de Açúcar 04/03/2026",
            "store_name": "str", "address": "str",
            "status": "active", "created_at": "datetime" }

GET /lists/{list_id}
Response: {
  "id", "title", "store_name", "address", "status",
  "total_cost", "created_at",
  "members": [{ "user_id", "name", "avatar_url", "role" }],
  "items": [{ ...ver item abaixo... }]
}
Query: ?filter=mine  (retorna apenas items assigned_to = current_user)

PATCH /lists/{list_id}/archive
Response: { "id", "status": "archived", "total_cost": 187.40, "archived_at" }
Permissão: somente owner

POST /lists/{list_id}/reuse
Response: { "id", "title": "Pão de Açúcar 04/03/2026", ... }
Efeito: cria nova lista copiando itens (com last_price do original)
Permissão: somente owner
```

### Itens

```
GET /lists/{list_id}/items
Query:  ?filter=mine
Response: [
  {
    "id": "str",
    "name": "Leite integral",
    "quantity": "2L",
    "status": "pending | checked | unavailable",
    "assigned_to": { "user_id", "name", "avatar_url" } | null,
    "price": 5.49 | null,
    "last_price": 4.99 | null,
    "checked_by": { "user_id", "name" } | null,
    "checked_at": "datetime | null",
    "version": 3
  }
]

POST /lists/{list_id}/items
Request:  { "name": "str", "quantity": "str" }
Response: { "id", "name", "quantity", "status": "pending", "version": 1, ... }
Permissão: owner ou member

PATCH /lists/{list_id}/items/{item_id}
Request:  {
  "status": "checked | unchecked | unavailable",  # opcional
  "price": 8.90,                                   # opcional (só com status=checked)
  "version": 3                                     # OBRIGATÓRIO (optimistic lock)
}
Response: { ...item atualizado com version: 4... }
Erros:    409 { "detail": "conflict", "current_version": 4 }
          403 se não é membro
Permissão: owner ou member

PATCH /lists/{list_id}/items/{item_id}/assign
Request:  { "user_id": "str | null" }   # null = remover atribuição
Response: { ...item atualizado... }
Permissão: somente owner

DELETE /lists/{list_id}/items/{item_id}
Response: 204 No Content
Permissão: owner ou member
```

### Membros

```
GET /lists/{list_id}/members
Response: [{ "user_id", "name", "email", "avatar_url", "role", "joined_at" }]

POST /lists/{list_id}/members
Request:  { "email": "str" }
Response: { "user_id", "name", "email", "avatar_url", "role": "member" }
Erros:    404 usuário não encontrado
          409 já é membro
Permissão: somente owner

DELETE /lists/{list_id}/members/{user_id}
Response: 204
Efeito:   itens atribuídos ao membro são reassigned para o owner
Permissão: owner (remove qualquer membro) ou o próprio membro (sai da lista)
```

### Usuários

```
GET /users/search?email={email}
Response: [{ "user_id", "name", "email", "avatar_url" }]
Nota:     retorna máximo 5 resultados, somente usuários ativos
```

### WebSocket

```
WS /ws/lists/{list_id}?token={jwt}

Eventos recebidos pelo cliente:
{ "event": "item_updated",   "data": { item completo } }
{ "event": "item_added",     "data": { item completo } }
{ "event": "item_deleted",   "data": { "item_id": "str" } }
{ "event": "item_assigned",  "data": { "item_id": "str", "assigned_to": {...} | null } }
{ "event": "member_joined",  "data": { "user_id", "name", "avatar_url" } }
{ "event": "member_removed", "data": { "user_id": "str" } }
{ "event": "list_archived",  "data": { "total_cost": 187.40 } }

Ciclo de vida:
- Servidor valida JWT no handshake (fecha 4001 se inválido)
- Servidor verifica que usuário é membro da lista (fecha 4003 se não for)
- Cliente recebe todos os eventos da lista enquanto conectado
```

---

## 4. Fluxo de Autorização (FastAPI DI)

```
Request HTTP
    │
    ▼
┌─────────────────────┐
│  SecurityHeaders     │  ← Middleware: X-Content-Type-Options, X-Frame-Options,
│  Middleware          │    Content-Security-Policy, HSTS
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  RateLimiter         │  ← Middleware: slowapi, por IP + por user
│  Middleware          │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Router Handler      │
│  Depends(get_current │  ← DI: valida JWT, retorna User entity
│  _user)              │    401 se expirado/inválido
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  Depends(require_list_member) ou    │  ← DI: verifica list_members
│  Depends(require_list_owner)        │    403 se não tem permissão
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────┐
│  Use Case            │  ← Regra de negócio pura, sem conhecer HTTP
└─────────────────────┘

Exemplo de endpoint com DI:
@router.patch("/{list_id}/items/{item_id}")
async def update_item(
    item_id: str,
    payload: UpdateItemSchema,
    current_user: User = Depends(get_current_user),
    membership: ListMember = Depends(require_list_member),  # verifica + retorna role
    use_case: UpdateItemStatusUC = Depends(get_update_item_uc),
):
    return await use_case.execute(item_id, payload, current_user)
```

---

## 5. Infraestrutura — docker-compose.yml

```yaml
version: "3.9"

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile          # multi-stage: node build → nginx:alpine
    ports:
      - "80:80"
    networks:
      - public
    environment:
      - VITE_API_URL=/api/v1
    depends_on:
      - api

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile          # multi-stage: python:3.12-slim → runtime
    ports:
      - "8000:8000"                   # exposto apenas para dev; em prod, só via frontend proxy
    networks:
      - public
      - internal
    env_file:
      - .env
    depends_on:
      mongodb:
        condition: service_healthy
    restart: unless-stopped

  mongodb:
    image: mongo:7-jammy
    networks:
      - internal                      # NUNCA exposto publicamente
    volumes:
      - mongo_data:/data/db
    environment:
      MONGO_INITDB_ROOT_USERNAME: ${MONGO_USER}
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD}
      MONGO_INITDB_DATABASE: ${MONGO_DB}
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5

networks:
  public: {}
  internal:
    internal: true                    # sem saída para internet

volumes:
  mongo_data: {}
```

### Diretrizes de Segurança nos Dockerfiles

**Backend (multi-stage):**
```dockerfile
# Stage 1: build
FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml .
RUN pip install --no-cache-dir build && pip install .

# Stage 2: runtime
FROM python:3.12-slim AS runtime
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --chown=appuser:appgroup app/ ./app/
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.infra.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Diretrizes aplicadas:**
- `non-root user` em todos os containers (appuser)
- `python:3.12-slim` / `nginx:alpine` como imagens base (< 30MB de superfície de ataque)
- `multi-stage build` — builder não vai para produção
- `--no-cache-dir` no pip — sem cache de pacotes na imagem final
- Segredos via variáveis de ambiente, nunca hardcoded ou em ARG
- `.env` no `.dockerignore` e `.gitignore`
- `COPY --chown` para ownership correto sem rodar como root

---

## 6. Segurança da Aplicação (OWASP Top 10)

| Risco OWASP | Mitigação Implementada |
|-------------|------------------------|
| A01 Broken Access Control | DI `require_list_member` / `require_list_owner` em cada endpoint; IDs validados como ObjectId válido |
| A02 Cryptographic Failures | bcrypt cost≥12 para senhas; JWT HS256 com secret de 256 bits; HTTPS obrigatório em produção |
| A03 Injection | Motor ODM com tipos tipados; nunca interpolar strings em queries; ObjectId sempre validado |
| A04 Insecure Design | Optimistic locking previne race condition no check de itens |
| A05 Security Misconfiguration | Security headers middleware; MongoDB sem porta exposta; .env fora do repositório |
| A07 Auth Failures | JWT com expiração de 15min; refresh token com rotação; rate limiting em /auth/* |
| A08 Software Integrity | `pip install` com hashes (pip-compile); imagens Docker com digest fixo em produção |

---

## 7. Fluxo Real-Time (WebSocket + REST)

```
Usuário A dá check em um item:
─────────────────────────────

1. PATCH /api/v1/lists/{id}/items/{item_id}
   Body: { "status": "checked", "price": 8.90, "version": 3 }

2. API executa UpdateItemStatusUC:
   a. findOneAndUpdate({ _id, version: 3 }, { $set: {...}, $inc: { version: 1 } })
   b. Se nenhum doc retornado → version divergiu → raise ConflictException → 409

3. Se sucesso:
   a. Retorna item atualizado (version: 4) para Usuário A via HTTP 200
   b. ConnectionManager.broadcast(list_id, { event: "item_updated", data: item })

4. Usuário B recebe via WebSocket:
   { "event": "item_updated", "data": { "id": "...", "status": "checked",
     "price": 8.90, "version": 4, "checked_by": { "name": "Ana" } } }

5. Frontend de B atualiza UI sem reload
```

---

## 8. Modelo de Dados para Reutilização de Lista

```
POST /lists/{archived_list_id}/reuse

Processo interno:
1. Busca lista arquivada (verifica ownership)
2. Para cada item da lista original:
   - Copia: name, quantity
   - Define: last_price = item.price (se existia)
   - Zera: status=pending, price=null, assigned_to=null,
           checked_by=null, version=1
3. Cria nova ShoppingList com:
   - store_name e address da original (pré-preenchidos)
   - source_list_id = id da original
   - title = "Store NOVA_DATA"

Frontend exibe last_price discretamente:
  ○ Leite integral  2L    ~R$ 4,99   ← cinza, pequeno, prefixo "~"
```
