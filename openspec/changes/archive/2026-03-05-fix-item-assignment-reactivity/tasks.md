# Tasks: fix-item-assignment-reactivity

- [x] Adicionar parâmetro `userId: string | null` à função `useListWebSocket` em `frontend/src/hooks/useListWebSocket.ts` e reescrever o case `item_assigned` com lógica filter-aware (add se `assigned_to.user_id === userId`, remove se não)
- [x] Atualizar a chamada `useListWebSocket(listId!, token)` em `frontend/src/pages/ListDetailPage.tsx` para `useListWebSocket(listId!, token, user?.id ?? null)`
- [x] Importar `useAuth` em `frontend/src/components/ListItemRow.tsx` e reescrever `updateItemInCache` com lógica filter-aware para o cache `'mine'` (add/update/remove baseado em `assigned_to.user_id === user?.id`)
- [x] Adicionar limite de conexoes WebSocket por usuario (`MAX_CONNECTIONS_PER_USER = 5`) em `backend/app/infra/websocket/connection_manager.py` e atualizar `connect()` para retornar `bool` e fechar com codigo 4029 quando o limite for atingido
- [x] Atualizar `backend/app/infra/http/routers/ws.py` para verificar o retorno de `manager.connect()` e encerrar o handler se a conexao foi recusada
