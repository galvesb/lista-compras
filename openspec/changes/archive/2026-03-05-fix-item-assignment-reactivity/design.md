# Design: fix-item-assignment-reactivity

## Visão geral do fluxo atual (com bug)

```
OWNER clica "Delegar item_X a si mesmo"
        │
        ▼
PATCH /lists/{id}/items/{itemId}/assign
        │
        ├─── HTTP 200 → item_X (assigned_to = owner)
        │         │
        │    assignMutation.onSuccess → updateItemInCache(item_X)
        │         │
        │    for f in ['all', 'mine']:
        │      cache[f].map(i => i.id === item_X.id ? item_X : i)
        │         │
        │    cache['all'] → item_X atualizado ✓
        │    cache['mine'] → item_X não estava lá → nada muda ✗
        │
        └─── WS broadcast → item_assigned (para TODOS os membros)
                  │
             useListWebSocket.onmessage
                  │
             for f in ['all', 'mine']:
               cache[f].map(i => i.id === item_X.id ? item_X : i)
                  │
             cache['all'] → item_X atualizado ✓
             cache['mine'] → mesmo bug ✗
```

## Visão geral do fluxo corrigido

```
OWNER clica "Delegar item_X a si mesmo"
        │
        ▼
PATCH /lists/{id}/items/{itemId}/assign   (sem alteração)
        │
        ├─── HTTP 200 → item_X (assigned_to = {user_id: owner_id, ...})
        │         │
        │    assignMutation.onSuccess → updateItemInCacheFilterAware(item_X, currentUserId)
        │         │
        │    cache['all'].map(update)          ✓  (update in-place)
        │    cache['mine']:
        │      se item_X.assigned_to.user_id === currentUserId
        │        → ADD item_X se não existir    ✓
        │      senão
        │        → REMOVE item_X se existir     ✓
        │
        └─── WS broadcast → item_assigned (para TODOS os membros)
                  │
             useListWebSocket.onmessage (com userId passado como param)
                  │
             cache['all'].map(update)           ✓  (update in-place)
             cache['mine']:
               se msg.data.assigned_to?.user_id === userId
                 → ADD se não existir           ✓
               senão
                 → REMOVE se existir            ✓
```

---

## Fix 1 — `useListWebSocket.ts`: adicionar `userId` e lógica filter-aware

### Assinatura atual
```typescript
export function useListWebSocket(listId: string, token: string | null)
```

### Assinatura corrigida
```typescript
export function useListWebSocket(listId: string, token: string | null, userId: string | null)
```

### Lógica `item_assigned` corrigida

```typescript
case 'item_assigned': {
  const updated = msg.data

  // cache 'all': update in-place (item já existe aqui)
  queryClient.setQueryData<ListItem[]>(
    ['list', listId, 'items', 'all'],
    (old) => old?.map((i) => (i.id === updated.id ? updated : i))
  )

  // cache 'mine': filter-aware — add se agora é meu, remove se deixou de ser
  queryClient.setQueryData<ListItem[]>(
    ['list', listId, 'items', 'mine'],
    (old = []) => {
      const isNowMine = updated.assigned_to?.user_id === userId
      const alreadyInMine = old.some((i) => i.id === updated.id)

      if (isNowMine && !alreadyInMine) {
        return [...old, updated]          // adiciona ao fim
      }
      if (isNowMine && alreadyInMine) {
        return old.map((i) => (i.id === updated.id ? updated : i))  // atualiza
      }
      if (!isNowMine) {
        return old.filter((i) => i.id !== updated.id)  // remove
      }
      return old
    }
  )
  break
}
```

### Por que `old = []` ao invés de `old?.`?

Se o cache `'mine'` ainda não foi carregado (`undefined`), precisamos que o callback retorne um array válido quando o item é delegado para o usuário atual. Com `old = []`, o resultado será `[updated]`, populando o cache imediatamente sem precisar de uma requisição ao servidor.

---

## Fix 2 — `ListDetailPage.tsx`: passar `user.id` para o hook

```typescript
// Antes
useListWebSocket(listId!, token)

// Depois
useListWebSocket(listId!, token, user?.id ?? null)
```

`user` já existe na página via `useAuth()`. Nenhuma mudança estrutural necessária.

---

## Fix 3 — `ListItemRow.tsx`: lógica filter-aware na mutation onSuccess

### Problema

`ListItemRow` não tem acesso a `currentUserId`. Solução: usar `useAuth()` dentro do próprio componente (o hook já está disponível em todo o app via `AuthContext`).

### Código corrigido

```typescript
// Importar o hook (topo do arquivo)
import { useAuth } from '../context/AuthContext'

// Dentro do componente
const { user } = useAuth()

// updateItemInCache corrigida
const updateItemInCache = (updated: ListItem) => {
  // cache 'all': update in-place
  queryClient.setQueryData<ListItem[]>(
    ['list', listId, 'items', 'all'],
    (old) => old?.map((i) => (i.id === updated.id ? updated : i))
  )

  // cache 'mine': filter-aware
  queryClient.setQueryData<ListItem[]>(
    ['list', listId, 'items', 'mine'],
    (old = []) => {
      const isNowMine = updated.assigned_to?.user_id === user?.id
      const alreadyInMine = old.some((i) => i.id === updated.id)

      if (isNowMine && !alreadyInMine) return [...old, updated]
      if (isNowMine && alreadyInMine) return old.map((i) => (i.id === updated.id ? updated : i))
      return old.filter((i) => i.id !== updated.id)
    }
  )
}
```

### Deduplicação actor + WS

Após o fix, tanto a mutation `onSuccess` quanto o evento WS `item_assigned` atualizarão o cache para o actor (dono da lista). Isso não causará problemas porque:
- A mutation atualiza primeiro (resposta HTTP é mais rápida que o evento WS chegar ao próprio client)
- O evento WS chega depois e executa a mesma lógica, resultando no mesmo estado
- A condição `alreadyInMine` previne duplicatas no cache `'mine'`

---

## Fix 4 — `ConnectionManager.py`: limite de conexões por usuário

### Problema
Sem limite, um usuário poderia abrir dezenas de abas e criar dezenas de conexões WebSocket ativas, consumindo memória e descritores de arquivo no servidor.

### Solução

```python
MAX_CONNECTIONS_PER_USER = 5

async def connect(self, list_id: str, user_id: str, websocket: WebSocket) -> bool:
    """
    Aceita a conexão e registra no room.
    Retorna False e fecha se o limite por usuário for atingido.
    """
    user_connections = sum(
        1 for room in self._rooms.values() if user_id in room
    )
    if user_connections >= MAX_CONNECTIONS_PER_USER:
        await websocket.close(code=4029, reason="Too many connections")
        return False

    await websocket.accept()
    self._rooms[list_id][user_id] = websocket
    return True
```

### Atualização no router `ws.py`

```python
connected = await manager.connect(list_id, user_id, websocket)
if not connected:
    return  # fechado pelo manager
```

### Contagem de conexões por usuário vs por lista

O limite `MAX_CONNECTIONS_PER_USER = 5` conta conexões do usuário em **todas as listas**, não apenas na lista atual. Isso é mais defensivo: um usuário não pode abrir 5 abas de cada lista simultaneamente.

---

## Diagrama de estados do cache 'mine' após o fix

```
Estado inicial (cache 'mine' = [item_A])

Evento: item_X delegado para currentUser
   isNowMine = true
   alreadyInMine = false
   → ADD: cache 'mine' = [item_A, item_X]   ✓

Evento: item_X delegado para outro usuário (ou removido)
   isNowMine = false
   → REMOVE: cache 'mine' = [item_A]         ✓

Evento: item_A atualizado (ainda atribuído a currentUser)
   isNowMine = true
   alreadyInMine = true
   → UPDATE: cache 'mine' = [item_A_updated] ✓

Evento: item_X delegado para currentUser (cache 'mine' = undefined)
   old = []  (default)
   isNowMine = true
   alreadyInMine = false
   → ADD: cache 'mine' = [item_X]            ✓  (populado sem refetch)
```

---

## Contrato do evento `item_assigned` (sem alteração no backend)

```json
{
  "event": "item_assigned",
  "data": {
    "id": "abc123",
    "list_id": "list456",
    "name": "Leite integral",
    "quantity": "2L",
    "status": "pending",
    "assigned_to": {
      "user_id": "user789",
      "name": "Maria",
      "avatar_url": null
    },
    "price": null,
    "last_price": null,
    "checked_by": null,
    "checked_at": null,
    "version": 3,
    "created_at": "2026-03-05T10:00:00Z"
  }
}
```

O campo `assigned_to` é `null` quando o item é desatribuído. A lógica `updated.assigned_to?.user_id === userId` retorna `false` (undefined !== userId), cobrindo o caso de remoção de atribuição corretamente.

---

## Resumo dos arquivos e linhas impactadas

| Arquivo | Tipo de mudança | Linhas aprox. |
|---|---|---|
| `frontend/src/hooks/useListWebSocket.ts` | Adicionar parâmetro `userId`, reescrever case `item_assigned` | +15 linhas |
| `frontend/src/pages/ListDetailPage.tsx` | Passar `user?.id` para o hook | +1 linha |
| `frontend/src/components/ListItemRow.tsx` | Importar `useAuth`, reescrever `updateItemInCache` | +10 linhas |
| `backend/app/infra/websocket/connection_manager.py` | Adicionar limite de conexões por usuário | +8 linhas |
| `backend/app/infra/http/routers/ws.py` | Verificar retorno de `manager.connect` | +2 linhas |
