# Tasks: Lista de Compras Colaborativas

## Fase 1 — Fundação (Infra + Auth)

### ✅ T01 · Scaffolding do Projeto
- Criar estrutura de monorepo: `backend/`, `frontend/`, `docker/`
- Configurar `docker-compose.yml` com serviços `api`, `frontend`, `mongodb`
- Configurar redes Docker: `public` e `internal` (MongoDB isolado)
- Configurar volume `mongo_data` para persistência
- Criar `.env.example` com todas as variáveis necessárias
- Criar `.gitignore` e `.dockerignore`

### ✅ T02 · Backend — Estrutura Clean Architecture
- Criar árvore de diretórios completa do backend (domain, use_cases, ports, adapters, infra)
- Configurar `pyproject.toml` com dependências: fastapi, uvicorn, motor, pydantic-settings, python-jose, bcrypt, slowapi
- Configurar `app/infra/config.py` com Settings (pydantic-settings, lê .env)
- Configurar `app/infra/db/mongodb.py` — Motor client com connection pool
- Configurar `app/infra/db/indexes.py` — criação de índices na startup

### ✅ T03 · Backend Dockerfile (multi-stage, non-root)
- Stage 1 (builder): `python:3.12-slim`, instala dependências
- Stage 2 (runtime): copia só site-packages, cria `appuser`, `USER appuser`
- Validar que container não roda como root

### ✅ T04 · Frontend Dockerfile (multi-stage)
- Stage 1 (builder): `node:20-alpine`, `npm ci && npm run build`
- Stage 2 (runtime): `nginx:alpine`, copia `dist/`, configura proxy `/api` → `api:8000`
- Configurar `nginx.conf` com proxy_pass e headers de segurança

### ✅ T05 · Auth — Entidades e Use Cases
- Criar entity `User` (domain/entities/user.py)
- Criar port `UserRepository` (ABC)
- Criar port `PasswordHasher` (ABC) + adapter `BcryptHasher` (cost=12)
- Criar port `TokenService` (ABC) + adapter `JWTTokenService` (HS256, exp=15min)
- Implementar use case `RegisterUserUC`
- Implementar use case `LoginUserUC`
- Implementar `MongoUserRepository`

### ✅ T06 · Auth — Endpoints HTTP
- Router `POST /api/v1/auth/register`
- Router `POST /api/v1/auth/login`
- Router `GET /api/v1/auth/me`
- DI `get_current_user` (valida JWT, retorna User)
- Rate limiting em `/auth/*` via slowapi (5 req/min por IP)

### ✅ T07 · Security Middleware
- `SecurityHeadersMiddleware`: X-Content-Type-Options, X-Frame-Options, CSP, HSTS
- Configurar CORS: origins permitidas via `.env`
- Validação de ObjectId: helper para converter e validar IDs

---

## Fase 2 — Core: Listas e Itens

### ✅ T08 · Domínio — Shopping List
- Criar entity `ShoppingList` com value object `ListStatus` (active|archived)
- Criar entity `ListMember` com value object `MemberRole` (owner|member)
- Criar port `ListRepository` (ABC)
- Criar port `MemberRepository` (ABC)
- Implementar `MongoListRepository`
- Implementar `MongoMemberRepository`

### ✅ T09 · Use Cases — Listas
- `CreateListUC`: gera título automático "[store] DD/MM/YYYY", cria owner como membro
- `GetListsUC`: retorna listas ativas/arquivadas do usuário (como owner ou member)
- `GetListDetailUC`: retorna lista + membros + itens (com filtro `?filter=mine`)
- `ArchiveListUC`: calcula total_cost (soma preços de itens checked), arquiva lista
- `ReuseListUC`: copia itens com last_price, cria nova lista com store pré-preenchido

### ✅ T10 · Endpoints HTTP — Listas
- `GET /api/v1/lists` com DI `get_current_user`
- `POST /api/v1/lists`
- `GET /api/v1/lists/{list_id}` com DI `require_list_member`
- `PATCH /api/v1/lists/{list_id}/archive` com DI `require_list_owner`
- `POST /api/v1/lists/{list_id}/reuse` com DI `require_list_owner`

### ✅ T11 · Domínio — List Items
- Criar entity `ListItem` com value object `ItemStatus` (pending|checked|unavailable)
- Criar domain exception `ConflictException` (optimistic lock)
- Criar port `ItemRepository` com método `update_with_version(item_id, version, update_data)`
- Implementar `MongoItemRepository` com `findOneAndUpdate({_id, version}, {$set:..., $inc:{version:1}})`

### ✅ T12 · Use Cases — Itens
- `AddItemUC`: adiciona item à lista (owner ou member)
- `UpdateItemStatusUC`: check/uncheck/unavailable + preço opcional; trata 409
- `AssignItemUC`: atribui item a membro (owner only); valida que user é membro da lista
- `DeleteItemUC`: remove item (owner ou member)

### ✅ T13 · Endpoints HTTP — Itens
- `GET /api/v1/lists/{list_id}/items?filter=mine`
- `POST /api/v1/lists/{list_id}/items` com DI `require_list_member`
- `PATCH /api/v1/lists/{list_id}/items/{item_id}` com DI `require_list_member`
- `PATCH /api/v1/lists/{list_id}/items/{item_id}/assign` com DI `require_list_owner`
- `DELETE /api/v1/lists/{list_id}/items/{item_id}` com DI `require_list_member`

---

## Fase 3 — Colaboração

### ✅ T14 · Use Cases — Membros
- `InviteMemberUC`: busca user por email, adiciona como member; valida não duplicado
- `RemoveMemberUC`: remove membro; reassign itens do removido para o owner
- `SearchUsersUC`: busca por email parcial, retorna máx 5 usuários ativos

### ✅ T15 · Endpoints HTTP — Membros e Usuários
- `GET /api/v1/lists/{list_id}/members` com DI `require_list_member`
- `POST /api/v1/lists/{list_id}/members` com DI `require_list_owner`
- `DELETE /api/v1/lists/{list_id}/members/{user_id}` (owner remove qualquer um; membro remove a si mesmo)
- `GET /api/v1/users/search?email=` com DI `get_current_user`

---

## Fase 4 — Real-Time

### ✅ T16 · WebSocket — ConnectionManager
- Criar `app/infra/websocket/connection_manager.py`
- `connect(list_id, user_id, websocket)` — adiciona ao room
- `disconnect(list_id, user_id)` — remove do room
- `broadcast(list_id, event, data)` — envia para todos no room exceto quem gerou (opcional)

### ✅ T17 · WebSocket — Endpoint e Auth
- Criar `WS /ws/lists/{list_id}?token={jwt}`
- Validar JWT no handshake (fechar 4001 se inválido)
- Verificar membership da lista (fechar 4003 se não membro)
- Manter conexão aberta, remover ao desconectar

### ✅ T18 · Integração REST → WebSocket
- Após cada mutação bem-sucedida (check, add item, delete, assign, archive), chamar `connection_manager.broadcast`
- Definir payload padrão de evento: `{ "event": "...", "data": {...} }`
- Eventos: `item_updated`, `item_added`, `item_deleted`, `item_assigned`, `member_joined`, `member_removed`, `list_archived`

---

## Fase 5 — Frontend

### ✅ T19 · Setup React + Roteamento
- Criar projeto React com Vite + TypeScript
- Configurar React Router (rotas: `/login`, `/register`, `/lists`, `/lists/:id`)
- Configurar Axios com interceptor para JWT (Bearer header + 401 redirect)
- Configurar TanStack Query (ou SWR) para cache e refetch
- Layout responsivo base com Tailwind CSS (ou CSS Modules)

### ✅ T20 · Auth — Telas
- Tela de Login (email + senha, validação client-side)
- Tela de Register (email, nome, senha, confirmação)
- Hook `useAuth` com contexto global (user, token, login, logout)
- Proteção de rotas privadas (`PrivateRoute`)

### ✅ T21 · Lista de Listas — Tela Home
- Card de lista: nome do mercado, data, status, total (se arquivada)
- Tabs: Ativas / Histórico (arquivadas)
- Botão "Nova Lista" → modal com form (nome do mercado + endereço)
- Botão "Reutilizar" nas listas arquivadas

### ✅ T22 · Detalhe da Lista
- Header: nome do mercado, data, endereço, avatares dos membros
- Tabs: "Visão Geral" / "Meus Itens"
- Item card: checkbox, nome, quantidade, avatar do atribuído
- Ao marcar como checked: input de preço (opcional, com confirm)
- Chip de status: ✓ comprado / ✗ indisponível
- Indicador de `last_price` (cinza, discreto)

### ✅ T23 · Delegação e Gerenciamento (Owner)
- Menu de item (owner only): "Atribuir a..." → modal com lista de membros + avatares
- Botão "Convidar Membro" → busca por email + confirmação
- Botão "Arquivar Lista" com total calculado na confirmação

### ✅ T24 · WebSocket — Integração Frontend
- Hook `useListWebSocket(listId)` — abre/fecha conexão WS
- Ao receber `item_updated`: atualiza item na query cache (TanStack Query)
- Ao receber `item_added`: adiciona item na lista
- Ao receber `item_deleted`: remove item da lista
- Ao receber `member_joined/removed`: atualiza membros
- Indicador visual "X pessoas online nesta lista" (opcional)

---

## Fase 6 — Testes e Hardening

### T25 · Testes de Use Cases (Unit)
- Testes com repositórios mockados para cada use case
- Cobrir: fluxo feliz, permissão negada (403), optimistic lock conflict (409), not found (404)

### T26 · Testes de Integração
- Testes de endpoints com MongoDB real (pytest + motor test client)
- Cobrir: criar lista, adicionar item, check, convidar membro, arquivar

### T27 · Análise de Segurança
- Revisar todos os endpoints contra OWASP Top 10
- Validar que MongoDB nunca recebe operadores `$` de input externo
- Confirmar que ObjectIds são validados antes de queries
- Testar rate limiting em rotas de auth
- Confirmar headers de segurança na resposta
