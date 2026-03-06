# Proposal: delete-list-fix-add-button

## O que

1. **Exclusão de listas** — dono pode excluir listas ativas e arquivadas. Implementado como Soft Delete (`deleted_at`). Exclusão se propaga em tempo real via WebSocket para todos os colaboradores com a lista aberta.
2. **Correção do botão "+" no mobile** — `addBtnStyle` em `ListDetailPage.tsx` não tem Flexbox explícito, causando desalinhamento do ícone "+" em navegadores mobile.

## Por que

### Exclusão de listas
- Hoje não existe nenhuma forma de o usuário remover uma lista da sua conta. Listas de teste, listas criadas por engano e listas antigas acumulam indefinidamente.
- Regra de negócio: apenas o dono (criador) tem permissão para excluir. Colaboradores convidados não podem fazer isso.
- Soft Delete é a estratégia escolhida: o documento MongoDB recebe `deleted_at = datetime.now()` em vez de ser apagado fisicamente. Isso preserva histórico e permite auditoria futura.

### Bug do botão "+"
- O `addBtnStyle` usa `width: 36px`, `height: 36px` e `fontSize: 20px` sem `display: flex`. Sem Flexbox, o `+` é centralizado pelo `line-height` nativo do browser — que varia entre iOS Safari, Chrome Android e desktop, causando desalinhamento visual no mobile.

## Escopo

### Backend (Python / FastAPI / MongoDB)
- `domain/entities/shopping_list.py` — campo `deleted_at`
- `ports/repositories/list_repository.py` — método abstrato `soft_delete`
- `adapters/repositories/mongo_list_repo.py` — implementação do `soft_delete`, filtro `deleted_at: None` em `find_by_id` e `find_by_user`
- `use_cases/lists/delete_list.py` — novo Use Case
- `infra/http/routers/lists.py` — endpoint `DELETE /{list_id}`

### Frontend (React / TypeScript)
- `types/index.ts` — evento `list_deleted` no union type `WsEvent`
- `hooks/useListWebSocket.ts` — novo case `list_deleted` com navigate + cache clear
- `pages/ListsPage.tsx` — botão lixeira nos cards (visível apenas para `role === 'owner'`)
- `pages/ListDetailPage.tsx` — botão "Excluir lista" no header (visível apenas para `isOwner`), fix de `addBtnStyle`

### Sem alterações
- `list_items` e `list_members` não são deletados — Soft Delete deixa o documento da lista como registro. Quando `find_by_id` retorna `None` para uma lista deletada, todos os endpoints downstream (items, members) retornarão 403/404 automaticamente via `require_list_member`.
- Nenhuma nova dependência de biblioteca.

## Segurança

| Camada | Proteção | Detalhe |
|---|---|---|
| API (infra) | `require_list_owner` | Valida membership + role=owner no banco antes de chegar ao Use Case |
| Use Case (domínio) | Verifica `owner_id` | Defense-in-depth — barreira dupla |
| Frontend | Renderização condicional | Botão de exclusão ausente do DOM para não-owners (UI guard, não segurança real) |
| WebSocket | JWT + membership | Conexão WS já valida JWT e membership antes de aceitar |
