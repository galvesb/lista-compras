# ADR-001 — MongoDB como banco de dados principal

**Status:** Aceito
**Data:** 2026-03-04

## Contexto

O modelo de dados central do sistema é a **Shopping List**, composta por itens, membros e delegações. Os padrões de acesso predominantes são:

- Leitura completa da lista (itens + membros) numa única operação
- Atualizações frequentes e granulares em itens individuais (check/uncheck, preço)
- Nenhum requisito de transações multi-entidade entre listas de usuários diferentes
- Necessidade de schema flexível (quantidade de itens por lista é variável, campos opcionais como `price`, `last_price`)

Um banco relacional exigiria JOINs em toda leitura (users ⟶ list_members ⟶ shopping_lists ⟶ list_items), aumentando a complexidade de queries sem ganho real de integridade referencial neste domínio.

## Decisão

Adotar **MongoDB 7** como único banco de dados, com o seguinte design de collections:

- `users` — documentos de usuário (email único indexado)
- `shopping_lists` — metadados da lista (store_name, status, total_cost)
- `list_members` — relação lista ↔ usuário com role (índice único composto)
- `list_items` — itens com campo `version` para optimistic locking

Os itens são documentos separados (não embedded) para suportar atualizações atômicas individuais via `findOneAndUpdate` com filtro `{_id, version}` sem reescrever o documento inteiro da lista.

## Consequências

**Positivas:**
- Leitura de lista + itens em 2 queries simples, sem JOIN
- `findOneAndUpdate` com `{$inc: {version: 1}}` resolve race conditions naturalmente
- Schema flexível permite adicionar campos sem migrations
- Motor (driver async) integra nativamente com FastAPI/asyncio

**Negativas:**
- Sem foreign key constraints — integridade referencial é responsabilidade da aplicação
- Aggregations complexas (ex: relatórios de gastos históricos) são mais verbosas que SQL
- Backup requer `mongodump` em vez de simples dump SQL

**Mitigações:**
- Indexes únicos no MongoDB garantem email único e membership única por lista
- Use cases na camada de domínio centralizam a lógica de validação referencial
