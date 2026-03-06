# Tasks: delete-list-fix-add-button

## Backend

- [x] Adicionar campo `deleted_at: datetime | None = None` à classe `ShoppingList` em `backend/app/domain/entities/shopping_list.py`
- [x] Adicionar método abstrato `soft_delete(self, list_id: str) -> bool` à interface `ListRepository` em `backend/app/ports/repositories/list_repository.py`
- [x] Atualizar `_doc_to_list` em `backend/app/adapters/repositories/mongo_list_repo.py` para mapear `deleted_at`; atualizar `find_by_id` e `find_by_user` para filtrar `deleted_at: None`; implementar método `soft_delete`
- [x] Criar `backend/app/use_cases/lists/delete_list.py` com `DeleteListUC` que valida `owner_id`, chama `soft_delete` e levanta `NotFoundError` ou `ForbiddenError`
- [x] Adicionar endpoint `DELETE /{list_id}` em `backend/app/infra/http/routers/lists.py` com `require_list_owner`, instancia `DeleteListUC`, faz broadcast `list_deleted` após sucesso

## Frontend — Tipos e WebSocket

- [x] Adicionar `| { event: 'list_deleted'; data: { list_id: string } }` ao union type `WsEvent` em `frontend/src/types/index.ts`
- [x] Importar `useNavigate` em `frontend/src/hooks/useListWebSocket.ts`, adicionar `navigate` nas dependências do `useEffect`, e implementar case `list_deleted` que chama `removeQueries` para os caches da lista, `invalidateQueries` para `['lists']` e `navigate('/lists', { replace: true })`

## Frontend — UI da Exclusão

- [x] Adicionar `deleteMutation` (chama `api.delete('/lists/{id}')` e invalida `['lists']`) e botão lixeira condicional (`list.role === 'owner'`) com `e.stopPropagation()` e `confirm()` nos cards de `frontend/src/pages/ListsPage.tsx`
- [x] Adicionar botão "Excluir lista" em `frontend/src/pages/ListDetailPage.tsx`, visível apenas quando `isOwner === true`, com `confirm()` e navegação de volta para `/lists` no `onSuccess`

## Frontend — Fix do Botão "+"

- [x] Adicionar `display: 'flex'`, `alignItems: 'center'` e `justifyContent: 'center'` ao `addBtnStyle` em `frontend/src/pages/ListDetailPage.tsx`
