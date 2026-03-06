# Design: delete-list-fix-add-button

---

## Parte 1 — Soft Delete: Modelagem e Backend

### 1.1 Schema do Documento MongoDB (`shopping_lists`)

Campo adicionado ao documento existente:

```json
{
  "_id": "ObjectId(...)",
  "title": "Carrefour - 2026-03-05",
  "store_name": "Carrefour",
  "address": "Av. Paulista, 1000",
  "owner_id": "ObjectId(...)",
  "status": "active",
  "total_cost": null,
  "source_list_id": null,
  "created_at": "2026-03-05T10:00:00Z",
  "archived_at": null,
  "deleted_at": null
}
```

Após soft delete:

```json
{
  "deleted_at": "2026-03-05T14:32:00Z"
}
```

### 1.2 Domain Entity — `ShoppingList` (Pydantic)

```python
# backend/app/domain/entities/shopping_list.py
from datetime import datetime
from pydantic import BaseModel
from app.domain.value_objects.list_status import ListStatus


class ShoppingList(BaseModel):
    id: str
    title: str
    store_name: str
    address: str
    owner_id: str
    status: ListStatus = ListStatus.ACTIVE
    total_cost: float | None = None
    source_list_id: str | None = None
    created_at: datetime
    archived_at: datetime | None = None
    deleted_at: datetime | None = None   # ← campo adicionado
```

### 1.3 Port — `ListRepository` (interface abstrata)

```python
# backend/app/ports/repositories/list_repository.py
from abc import ABC, abstractmethod

class ListRepository(ABC):
    # ... métodos existentes ...

    @abstractmethod
    async def soft_delete(self, list_id: str) -> bool:
        """
        Marca a lista como excluída (deleted_at = now()).
        Retorna True se encontrou e atualizou; False se não encontrou.
        """
```

### 1.4 Adapter — `MongoListRepository`

```python
# backend/app/adapters/repositories/mongo_list_repo.py

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
        deleted_at=doc.get("deleted_at"),   # ← adicionado
    )


class MongoListRepository(ListRepository):

    async def find_by_id(self, list_id: str) -> ShoppingList | None:
        if not ObjectId.is_valid(list_id):
            return None
        # deleted_at: None filtra listas excluídas
        doc = await self._col.find_one({
            "_id": ObjectId(list_id),
            "deleted_at": None,
        })
        return _doc_to_list(doc) if doc else None

    async def find_by_user(
        self, user_id: str, status: ListStatus | None = None
    ) -> list[ShoppingList]:
        query: dict = {
            "owner_id": ObjectId(user_id),
            "deleted_at": None,           # ← filtro adicionado
        }
        if status:
            query["status"] = status
        cursor = self._col.find(query).sort("created_at", -1)
        return [_doc_to_list(doc) async for doc in cursor]

    async def soft_delete(self, list_id: str) -> bool:
        """Define deleted_at somente se a lista ainda não foi excluída."""
        result = await self._col.update_one(
            {"_id": ObjectId(list_id), "deleted_at": None},
            {"$set": {"deleted_at": datetime.now(UTC)}},
        )
        return result.modified_count > 0
```

### 1.5 Use Case — `DeleteListUC`

```python
# backend/app/use_cases/lists/delete_list.py
from app.domain.exceptions.forbidden import ForbiddenError
from app.domain.exceptions.not_found import NotFoundError
from app.ports.repositories.list_repository import ListRepository


class DeleteListUC:
    def __init__(self, list_repo: ListRepository) -> None:
        self._list_repo = list_repo

    async def execute(self, list_id: str, current_user_id: str) -> None:
        """
        Defense-in-depth: valida ownership mesmo que require_list_owner
        no router já tenha verificado via member_repo.
        """
        lst = await self._list_repo.find_by_id(list_id)
        if not lst:
            raise NotFoundError("ShoppingList", list_id)

        if lst.owner_id != current_user_id:
            raise ForbiddenError("Only the list owner can delete it")

        deleted = await self._list_repo.soft_delete(list_id)
        if not deleted:
            raise NotFoundError("ShoppingList", list_id)
```

### 1.6 Router — Endpoint `DELETE /lists/{list_id}`

**Contrato OpenAPI:**

```yaml
DELETE /api/lists/{list_id}:
  summary: Excluir uma lista (soft delete)
  security:
    - BearerAuth: []
  parameters:
    - name: list_id
      in: path
      required: true
      schema: { type: string }
  responses:
    204:
      description: Lista excluída com sucesso
    403:
      description: Acesso negado — usuário não é o dono
      content:
        application/json:
          example: { "detail": "Access denied: only the list owner can perform this action" }
    404:
      description: Lista não encontrada
```

**Implementação FastAPI:**

```python
# backend/app/infra/http/routers/lists.py

@router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_list(
    list_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    membership: ListMember = Depends(require_list_owner),  # 403 se não for owner
) -> None:
    db = get_database()
    uc = DeleteListUC(MongoListRepository(db))
    try:
        await uc.execute(list_id, current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    # Notifica todos os colaboradores conectados via WebSocket
    await manager.broadcast(list_id, "list_deleted", {"list_id": list_id})
```

---

## Parte 2 — WebSocket: Evento `list_deleted`

### 2.1 Evento WS — Schema JSON

```json
{
  "event": "list_deleted",
  "data": {
    "list_id": "68c1a9f3b2e4d5f6a7b8c9d0"
  }
}
```

### 2.2 TypeScript — Atualizar `WsEvent`

```typescript
// frontend/src/types/index.ts

export type WsEvent =
  | { event: 'item_updated'; data: ListItem }
  | { event: 'item_added'; data: ListItem }
  | { event: 'item_deleted'; data: { item_id: string } }
  | { event: 'item_assigned'; data: ListItem }
  | { event: 'member_joined'; data: Member }
  | { event: 'member_removed'; data: { user_id: string } }
  | { event: 'list_archived'; data: { total_cost: number } }
  | { event: 'list_deleted'; data: { list_id: string } }   // ← adicionado
```

### 2.3 `useListWebSocket.ts` — Case `list_deleted`

```typescript
// frontend/src/hooks/useListWebSocket.ts
import { useNavigate } from 'react-router-dom'  // ← importar

export function useListWebSocket(
  listId: string,
  token: string | null,
  userId: string | null,
) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()    // ← adicionar
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    // ...
    switch (msg.event) {
      // ... cases existentes ...

      case 'list_deleted':
        // 1. Remove dados desta lista do cache (não apenas invalida)
        queryClient.removeQueries({ queryKey: ['list', listId] })
        queryClient.removeQueries({ queryKey: ['list', listId, 'items'] })
        // 2. Invalida a listagem geral para remover o card
        queryClient.invalidateQueries({ queryKey: ['lists'] })
        // 3. Redireciona para a home com replace (sem histórico desta lista)
        navigate('/lists', { replace: true })
        break
    }
  }, [listId, token, userId, queryClient, navigate])  // ← navigate nas deps
}
```

**Por que `removeQueries` e não `invalidateQueries`?**
`invalidateQueries` marca como stale e refetch seria tentado — mas a lista não existe mais, resultando em 404. `removeQueries` limpa o cache completamente, sem refetch.

---

## Parte 3 — Frontend: Botões de Exclusão + Fix do Botão "+"

### 3.1 `ListsPage.tsx` — Botão lixeira no card

```tsx
// O role já vem em ListSummaryResponse (campo existente)
{lists.map((list) => (
  <div key={list.id} onClick={() => navigate(`/lists/${list.id}`)} style={cardStyle}>
    <div style={{ flex: 1 }}>
      <p style={{ margin: 0, fontWeight: 600, fontSize: '15px' }}>{list.store_name}</p>
      {/* ... data e total_cost ... */}
    </div>
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      {tab === 'archived' && (
        <button onClick={(e) => { e.stopPropagation(); reuseMutation.mutate(list.id) }} style={reuseBtn}>
          Reutilizar
        </button>
      )}
      {/* Botão lixeira — visível APENAS para o dono */}
      {list.role === 'owner' && (
        <button
          onClick={(e) => {
            e.stopPropagation()
            if (confirm(`Excluir "${list.store_name}"? Esta ação não pode ser desfeita.`)) {
              deleteMutation.mutate(list.id)
            }
          }}
          style={deleteCardBtn}
          title="Excluir lista"
          disabled={deleteMutation.isPending}
        >
          🗑
        </button>
      )}
      <span style={{ color: '#d1d5db' }}>›</span>
    </div>
  </div>
))}
```

**Mutation de delete:**

```typescript
const deleteMutation = useMutation({
  mutationFn: (listId: string) => api.delete(`/lists/${listId}`),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['lists'] })
  },
})
```

**Estilo do botão lixeira no card:**

```typescript
const deleteCardBtn: React.CSSProperties = {
  background: 'transparent',
  border: 'none',
  color: '#fca5a5',
  cursor: 'pointer',
  fontSize: '16px',
  padding: '4px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
}
```

### 3.2 `ListDetailPage.tsx` — Botão "Excluir lista" no footer

```tsx
{/* Botão Excluir (owner only) — posicionado abaixo do botão Finalizar */}
{isOwner && (
  <div style={{ padding: '8px 16px 16px', textAlign: 'center' }}>
    <button
      onClick={() => {
        if (confirm(`Excluir "${listData.store_name}"? Esta ação é permanente.`)) {
          api.delete(`/lists/${listId}`).then(() => {
            queryClient.invalidateQueries({ queryKey: ['lists'] })
            navigate('/lists')
          })
        }
      }}
      style={deleteBtnStyle}
    >
      Excluir lista
    </button>
  </div>
)}
```

**Estilo:**

```typescript
const deleteBtnStyle: React.CSSProperties = {
  background: 'transparent',
  color: '#dc2626',
  border: '1.5px solid #fecaca',
  borderRadius: '10px',
  padding: '8px 20px',
  fontWeight: 600,
  fontSize: '13px',
  cursor: 'pointer',
}
```

### 3.3 Fix `addBtnStyle` — Botão "+" centralizado no mobile

**Causa:** Sem `display: flex`, o `+` é posicionado via `line-height` nativo — inconsistente entre iOS Safari, Chrome Android e desktop.

**Correção:**

```typescript
// frontend/src/pages/ListDetailPage.tsx — addBtnStyle
const addBtnStyle: React.CSSProperties = {
  width: '36px',
  height: '36px',
  borderRadius: '8px',
  background: '#6366f1',
  color: '#fff',
  border: 'none',
  fontSize: '20px',
  fontWeight: 700,
  cursor: 'pointer',
  flexShrink: 0,
  display: 'flex',           // ← centraliza no eixo principal (horizontal)
  alignItems: 'center',      // ← centraliza no eixo cruzado (vertical)
  justifyContent: 'center',  // ← centraliza no eixo principal
}
```

`display: flex` + `alignItems: center` + `justifyContent: center` centraliza o `+` **geometricamente** no container, ignorando font metrics, line-height e padding nativo do browser.

---

## Resumo dos arquivos e mudanças

| Arquivo | Tipo | Detalhe |
|---|---|---|
| `domain/entities/shopping_list.py` | +1 campo | `deleted_at: datetime \| None = None` |
| `ports/repositories/list_repository.py` | +1 método | `soft_delete(list_id: str) -> bool` |
| `adapters/repositories/mongo_list_repo.py` | +1 método, 2 queries atualizadas | `soft_delete`, filtro em `find_by_id` e `find_by_user` |
| `use_cases/lists/delete_list.py` | Novo arquivo | `DeleteListUC` |
| `infra/http/routers/lists.py` | +1 endpoint | `DELETE /{list_id}` |
| `frontend/src/types/index.ts` | +1 union member | `list_deleted` em `WsEvent` |
| `frontend/src/hooks/useListWebSocket.ts` | +1 import, +1 case | `useNavigate`, case `list_deleted` |
| `frontend/src/pages/ListsPage.tsx` | +1 mutation, +1 botão | `deleteMutation`, lixeira condicional |
| `frontend/src/pages/ListDetailPage.tsx` | +1 botão, fix estilo | Botão "Excluir lista", `addBtnStyle` com flexbox |
