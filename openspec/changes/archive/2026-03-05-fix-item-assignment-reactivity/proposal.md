# Proposal: fix-item-assignment-reactivity

## O que

Corrigir a falta de reatividade da aba "Meus Itens" após delegacao de itens, e garantir que todos os colaboradores com a lista aberta recebam atualizações em tempo real sem recarregar a página.

## Por que

O app já possui WebSocket implementado e funcionando (`useListWebSocket`). O backend já faz broadcast correto do evento `item_assigned` para todos os membros conectados. O problema **não é de arquitetura**: é um bug de lógica no frontend ao atualizar o cache do React Query após uma delegação.

### Sintomas observados

1. **Delegante não vê o item em "Meus Itens"**: ao delegar um item para si mesmo na aba "Visão Geral" e clicar em "Meus Itens", o item não aparece — é necessário F5.
2. **Colaboradores não veem a delegação em tempo real**: outros usuários com a lista aberta precisam recarregar para ver quem ficou responsável por cada item.

### Causa raiz

A função `updateItemInCache` (usada tanto na mutation `onSuccess` de `ListItemRow.tsx` quanto no handler `item_assigned` de `useListWebSocket.ts`) executa:

```typescript
old?.map((i) => (i.id === updated.id ? updated : i))
```

Esse `.map()` funciona para o cache `'all'` porque o item já existe lá. Mas falha para o cache `'mine'` em dois cenários:

**Cenário A — cache 'mine' nunca foi carregado:**
```
cache['mine'] = undefined
old?.map(...) → undefined   ← setQueryData ignora
```

**Cenário B — cache 'mine' carregado, mas sem o item recém-delegado:**
```
cache['mine'] = [item_A, item_B]     ← itens antigos atribuídos a mim
item_X recém-delegado = só existe em cache['all']

old.map(i => i.id === item_X.id ? updated : i)
→ item_X não está em 'mine', map não encontra → retorna [item_A, item_B]
→ item_X nunca é adicionado ao cache 'mine'
```

O cache `'mine'` é um **subconjunto filtrado** — ele precisa de lógica de **add/remove contextual**, não apenas de update in-place.

## Escopo

Apenas frontend. Backend sem alterações funcionais.

### Arquivos modificados
- `frontend/src/hooks/useListWebSocket.ts` — adicionar `userId` como parâmetro e corrigir lógica `item_assigned`
- `frontend/src/pages/ListDetailPage.tsx` — passar `user.id` ao hook `useListWebSocket`
- `frontend/src/components/ListItemRow.tsx` — corrigir `updateItemInCache` para lógica filter-aware
- `frontend/src/context/AuthContext.tsx` — verificar se `user.id` está exposto (somente leitura, sem alteração)

### O que não muda
- Backend: nenhuma alteração (WebSocket, broadcast e endpoints já estão corretos)
- Arquitetura real-time: WebSocket já é a solução certa (sem necessidade de SSE ou polling)
- Dependências: nenhuma nova biblioteca

## Segurança

Durante a análise foram identificados pontos de atenção relacionados à segurança:

### Pontos existentes e status

| Item | Risco | Status |
|---|---|---|
| JWT validado antes de aceitar conexão WS | — | Seguro ✓ |
| Membership verificada antes de entrar na sala | — | Seguro ✓ |
| Apenas owner pode delegar (`require_list_owner`) | — | Seguro ✓ |
| Token JWT passado como query param na URL do WS | Médio — aparece em logs do servidor e histórico do browser | Limitação conhecida, aceitável para MVP |
| Estado de conexões em memória (sem Redis) | Baixo — perde conexões em restart; não escala horizontalmente | Aceitável para MVP de instância única |
| Sem limite de conexões WS por usuário | Baixo — abrir muitas abas cria muitas conexões | Sem impacto prático no MVP |

### Ação de segurança incluída nesta change

Adicionar proteção de limite de conexões simultâneas por usuário no `ConnectionManager` para evitar que um usuário mal-intencionado (ou com muitas abas) sobrecarregue o servidor com conexões WebSocket.

```python
# Limite de 5 conexões simultâneas por usuário por lista
MAX_CONNECTIONS_PER_USER = 5
```

Isso não resolve o problema do token em URL (que exigiria mudança no protocolo de handshake), mas é uma melhoria defensiva simples e sem breaking changes.
